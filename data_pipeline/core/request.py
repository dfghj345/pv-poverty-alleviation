from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Optional

import httpx
from playwright.async_api import async_playwright

from data_pipeline.core.config import pipeline_settings
from data_pipeline.core.context import RunContext
from data_pipeline.core.logging import get_ctx_logger
from data_pipeline.core.retry import async_retry


@dataclass(slots=True, frozen=True)
class RequestOptions:
    timeout_s: float = 20.0
    retries: int = 2
    retry_base_delay_s: float = 0.5
    headers: Mapping[str, str] | None = None
    user_agent: Optional[str] = None
    trust_env: Optional[bool] = None
    body_preview_len: int = 240


class HttpClient:
    async def get_json(self, url: str, *, params: Mapping[str, Any] | None = None, ctx: RunContext, opt: RequestOptions) -> Any:
        log = get_ctx_logger(__name__, ctx=ctx)
        timeout = httpx.Timeout(opt.timeout_s)
        headers = dict(opt.headers or {})
        if opt.user_agent:
            headers.setdefault("User-Agent", opt.user_agent)

        trust_env = opt.trust_env if opt.trust_env is not None else bool(getattr(pipeline_settings, "HTTP_TRUST_ENV", False))
        async with httpx.AsyncClient(timeout=timeout, headers=headers, trust_env=trust_env) as client:
            async def _call() -> Any:
                r = await client.get(url, params=params)
                ct = (r.headers.get("content-type") or "").lower()
                body = r.content or b""
                preview = body[: opt.body_preview_len].decode("utf-8", errors="replace")

                try:
                    r.raise_for_status()
                except Exception as e:
                    log.error(
                        "http status error",
                        extra={
                            "url": str(r.request.url) if r.request else url,
                            "status_code": r.status_code,
                            "content_type": ct,
                            "body_preview": preview,
                            "params": safe_json_dumps(params),
                            "trust_env": trust_env,
                        },
                    )
                    raise

                # content-type 可能缺失/不标准，因此再加一个 body 形态兜底
                looks_like_json = ("json" in ct) or preview.lstrip().startswith(("{", "["))
                if not looks_like_json:
                    msg = "response is not JSON"
                    log.error(
                        msg,
                        extra={
                            "url": str(r.request.url) if r.request else url,
                            "status_code": r.status_code,
                            "content_type": ct,
                            "body_preview": preview,
                            "params": safe_json_dumps(params),
                            "trust_env": trust_env,
                        },
                    )
                    raise RuntimeError(
                        f"{msg} | status={r.status_code} content-type={ct or '<missing>'} "
                        f"url={str(r.request.url) if r.request else url} params={safe_json_dumps(params)} "
                        f"body_preview={preview!r}"
                    )

                try:
                    return r.json()
                except Exception as e:
                    log.error(
                        "json decode failed",
                        extra={
                            "url": str(r.request.url) if r.request else url,
                            "status_code": r.status_code,
                            "content_type": ct,
                            "body_preview": preview,
                            "params": safe_json_dumps(params),
                            "error": f"{type(e).__name__}: {e}",
                            "trust_env": trust_env,
                        },
                    )
                    raise

            return await async_retry(
                _call,
                retries=opt.retries,
                base_delay_s=opt.retry_base_delay_s,
                on_retry=lambda n, e, d: log.warning("http retry", extra={"attempt": n, "delay_s": d, "error": str(e)}),
            )

    async def get_text(self, url: str, *, params: Mapping[str, Any] | None = None, ctx: RunContext, opt: RequestOptions) -> str:
        data = await self.get_bytes(url, params=params, ctx=ctx, opt=opt)
        return data.decode("utf-8", errors="replace")

    async def get_bytes(self, url: str, *, params: Mapping[str, Any] | None = None, ctx: RunContext, opt: RequestOptions) -> bytes:
        log = get_ctx_logger(__name__, ctx=ctx)
        timeout = httpx.Timeout(opt.timeout_s)
        headers = dict(opt.headers or {})
        if opt.user_agent:
            headers.setdefault("User-Agent", opt.user_agent)

        trust_env = opt.trust_env if opt.trust_env is not None else bool(getattr(pipeline_settings, "HTTP_TRUST_ENV", False))
        async with httpx.AsyncClient(timeout=timeout, headers=headers, trust_env=trust_env) as client:
            async def _call() -> bytes:
                r = await client.get(url, params=params)
                r.raise_for_status()
                return r.content

            return await async_retry(
                _call,
                retries=opt.retries,
                base_delay_s=opt.retry_base_delay_s,
                on_retry=lambda n, e, d: log.warning("http retry", extra={"attempt": n, "delay_s": d, "error": str(e)}),
            )


class PlaywrightHtmlClient:
    async def get_html(self, url: str, *, ctx: RunContext, opt: RequestOptions, wait_selector: Optional[str] = None) -> str:
        log = get_ctx_logger(__name__, ctx=ctx)

        async def _call() -> str:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                try:
                    context = await browser.new_context(user_agent=opt.user_agent or None)
                    page = await context.new_page()
                    log.info("playwright goto", extra={"url": url})
                    await page.goto(url, wait_until="networkidle", timeout=int(opt.timeout_s * 1000))
                    if wait_selector:
                        await page.wait_for_selector(wait_selector, timeout=int(opt.timeout_s * 1000))
                    html = await page.content()
                    if opt.body_preview_len:
                        log.info(
                            "playwright html fetched",
                            extra={"url": url, "body_preview": (html[: opt.body_preview_len] if isinstance(html, str) else "")},
                        )
                    return html
                finally:
                    await browser.close()

        return await async_retry(
            _call,
            retries=opt.retries,
            base_delay_s=opt.retry_base_delay_s,
            on_retry=lambda n, e, d: log.warning("playwright retry", extra={"attempt": n, "delay_s": d, "error": str(e)}),
        )


def safe_json_dumps(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, default=str)
    except Exception:
        return "<unserializable>"

