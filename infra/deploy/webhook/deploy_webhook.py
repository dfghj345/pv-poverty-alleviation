#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import subprocess
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None  # type: ignore[assignment]


HOST = os.getenv("WEBHOOK_HOST", "127.0.0.1")
PORT = int(os.getenv("WEBHOOK_PORT", "9001"))
PATH = os.getenv("WEBHOOK_PATH", "/webhook")

PROJECT_DIR = Path(os.getenv("PROJECT_DIR", "/srv/pv-poverty-alleviation"))
FRONTEND_DIR = Path(os.getenv("FRONTEND_DIR", str(PROJECT_DIR / "frontend")))
FRONTEND_DIST_DIR = Path(os.getenv("FRONTEND_DIST_DIR", "/var/www/poverty.top"))
COMPOSE_DIR = Path(os.getenv("COMPOSE_DIR", str(PROJECT_DIR)))
TARGET_BRANCH = os.getenv("WEBHOOK_BRANCH", "refs/heads/main")

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "").strip()
WEBHOOK_TOKEN = os.getenv("WEBHOOK_TOKEN", "").strip()
LOCK_FILE = Path(os.getenv("WEBHOOK_LOCK_FILE", str(PROJECT_DIR / ".deploy-webhook.lock")))
LOG_LEVEL = os.getenv("WEBHOOK_LOG_LEVEL", "INFO").upper()
_DEPLOY_LOCK = threading.Lock()


logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("deploy-webhook")


def run_checked(command: list[str], *, cwd: Path) -> str:
    logger.info("running: %s (cwd=%s)", " ".join(command), cwd)
    result = subprocess.run(
        command,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"command failed: {' '.join(command)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    output = result.stdout.strip()
    if output:
        logger.info(output)
    if result.stderr.strip():
        logger.warning(result.stderr.strip())
    return output


def verify_signature(signature_header: str, body: bytes) -> bool:
    if not WEBHOOK_SECRET:
        return False
    if not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def verify_token(headers: dict[str, str], query: str) -> bool:
    if not WEBHOOK_TOKEN:
        return False

    header_candidates = [
        headers.get("X-Webhook-Token", ""),
        headers.get("X-Gitee-Token", ""),
        headers.get("Authorization", "").removeprefix("Bearer ").strip(),
    ]
    if any(hmac.compare_digest(candidate, WEBHOOK_TOKEN) for candidate in header_candidates if candidate):
        return True

    parsed = {}
    for item in query.split("&"):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        parsed[key] = value
    token = parsed.get("token", "")
    return bool(token) and hmac.compare_digest(token, WEBHOOK_TOKEN)


def is_authorized(headers: dict[str, str], body: bytes, query: str) -> bool:
    signature = headers.get("X-Hub-Signature-256", "")
    if verify_signature(signature, body):
        return True
    return verify_token(headers, query)


def branch_matches(payload: dict[str, Any]) -> bool:
    ref = str(payload.get("ref") or "").strip()
    if not ref:
        return True
    return ref == TARGET_BRANCH


def deploy() -> dict[str, Any]:
    started_at = time.time()
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not _DEPLOY_LOCK.acquire(blocking=False):
        raise RuntimeError("deployment already in progress")

    try:
        with LOCK_FILE.open("w", encoding="utf-8") as lock_fp:
            if fcntl is not None:
                try:
                    fcntl.flock(lock_fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError as exc:
                    raise RuntimeError("deployment already in progress") from exc

            run_checked(["git", "pull", "--ff-only"], cwd=PROJECT_DIR)
            run_checked(["docker", "compose", "up", "-d", "--build", "postgres", "redis", "backend"], cwd=COMPOSE_DIR)
            run_checked(["npm", "ci"], cwd=FRONTEND_DIR)
            run_checked(["npm", "run", "build"], cwd=FRONTEND_DIR)

            FRONTEND_DIST_DIR.mkdir(parents=True, exist_ok=True)
            run_checked(
                [
                    "rsync",
                    "-av",
                    "--delete",
                    f"{FRONTEND_DIR / 'dist'}/",
                    str(FRONTEND_DIST_DIR),
                ],
                cwd=PROJECT_DIR,
            )
    finally:
        _DEPLOY_LOCK.release()

    return {
        "ok": True,
        "duration_seconds": round(time.time() - started_at, 2),
        "project_dir": str(PROJECT_DIR),
        "frontend_dist_dir": str(FRONTEND_DIST_DIR),
    }


class WebhookHandler(BaseHTTPRequestHandler):
    server_version = "DeployWebhook/1.0"

    def log_message(self, format: str, *args: object) -> None:
        logger.info("%s - %s", self.address_string(), format % args)

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != PATH:
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "message": "not found"})
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length)
        headers = {key: value for key, value in self.headers.items()}

        if not is_authorized(headers, body, parsed.query):
            self._send_json(HTTPStatus.UNAUTHORIZED, {"ok": False, "message": "unauthorized"})
            return

        event = headers.get("X-GitHub-Event") or headers.get("X-Gitee-Event") or "unknown"
        if event in {"ping"}:
            self._send_json(HTTPStatus.OK, {"ok": True, "message": "pong"})
            return

        try:
            payload = json.loads(body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "message": "invalid json"})
            return

        if not branch_matches(payload):
            self._send_json(
                HTTPStatus.ACCEPTED,
                {
                    "ok": True,
                    "message": "ignored",
                    "reason": "branch mismatch",
                    "target_branch": TARGET_BRANCH,
                    "ref": payload.get("ref"),
                },
            )
            return

        try:
            result = deploy()
        except Exception as exc:  # pragma: no cover
            logger.exception("deployment failed")
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"ok": False, "message": "deployment failed", "error": str(exc)},
            )
            return

        self._send_json(
            HTTPStatus.OK,
            {
                "ok": True,
                "message": "deployment finished",
                "event": event,
                **result,
            },
        )


def main() -> None:
    if not WEBHOOK_SECRET and not WEBHOOK_TOKEN:
        raise SystemExit("WEBHOOK_SECRET or WEBHOOK_TOKEN must be set")

    if not PROJECT_DIR.exists():
        raise SystemExit(f"PROJECT_DIR does not exist: {PROJECT_DIR}")

    server = ThreadingHTTPServer((HOST, PORT), WebhookHandler)
    logger.info("webhook server listening on http://%s:%s%s", HOST, PORT, PATH)
    server.serve_forever()


if __name__ == "__main__":
    main()
