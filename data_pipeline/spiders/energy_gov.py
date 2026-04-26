from __future__ import annotations

if __package__ is None:
    from importlib.util import module_from_spec, spec_from_file_location
    from pathlib import Path

    _bootstrap_path = Path(__file__).resolve().parents[1] / "_bootstrap.py"
    _spec = spec_from_file_location("data_pipeline._bootstrap", _bootstrap_path)
    if _spec is None or _spec.loader is None:
        raise RuntimeError(f"Failed to load bootstrap from {_bootstrap_path}")
    _mod = module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    _mod.ensure_project_root_on_syspath(__file__)

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from data_pipeline.base.spider import BaseSpider
from data_pipeline.core.context import RunContext
from data_pipeline.core.logging import get_ctx_logger
from data_pipeline.core.request import HttpClient, RequestOptions
from data_pipeline.registry.spiders import register_spider
from data_pipeline.storage.energy_policy_db import EnergyPolicyRow


@dataclass(frozen=True)
class EnergyPolicyItem:
    title: str
    url: str
    publish_date: Optional[str] = None
    summary: Optional[str] = None


POLICY_KEYWORDS = ("光伏", "扶贫", "新能源", "可再生能源", "分布式", "电价", "补贴", "能源")
_DATE_RE = re.compile(r"(20\d{2}[-/.]\d{1,2}[-/.]\d{1,2})|(20\d{2}年\d{1,2}月\d{1,2}日)")


@register_spider("energy_gov")
class EnergyGovSpider(BaseSpider[str, EnergyPolicyRow]):
    name = "energy_gov"
    site = "energy_gov"
    data_type = "energy_policy"

    def __init__(self) -> None:
        self._http: HttpClient | None = None
        self._request_opt: RequestOptions | None = None
        self._site_url: str | None = None

    async def fetch(self, ctx: RunContext) -> str:
        if self._http is None or self._request_opt is None or self._site_url is None:
            raise RuntimeError("spider dependencies not injected (runner should set _http/_request_opt/_site_url)")
        log = get_ctx_logger(__name__, ctx=ctx)
        html = await self._http.get_text(self._site_url, params=None, ctx=ctx, opt=self._request_opt)
        log.info("fetched html", extra={"html_length": len(html)})
        return html

    def parse(self, raw: str, ctx: RunContext) -> List[EnergyPolicyRow]:
        log = get_ctx_logger(__name__, ctx=ctx)
        soup = BeautifulSoup(raw, "lxml")
        base_url = str(ctx.meta.get("http_final_url") or self._site_url or ctx.url or "")

        out: List[EnergyPolicyRow] = []
        seen: set[str] = set()
        for a in soup.find_all("a", href=True):
            title = " ".join(a.stripped_strings).strip()
            href = (a.get("href") or "").strip()
            if not title or not href:
                continue
            if not any(keyword in title for keyword in POLICY_KEYWORDS):
                continue

            url = urljoin(base_url, href)
            if not url.lower().startswith(("http://", "https://")):
                continue
            if url in seen:
                continue

            parent = a.find_parent(["li", "tr", "p", "div"])
            text = " ".join(parent.stripped_strings) if parent is not None else title
            publish_date = _extract_date(text)
            summary = _make_summary(text, title=title, publish_date=publish_date)

            out.append(
                EnergyPolicyRow(
                    title=title,
                    url=url,
                    publish_date=publish_date,
                    summary=summary,
                    source="nea",
                    source_url=self._site_url or ctx.url,
                )
            )
            seen.add(url)

        if not out and ctx.meta.get("http_status_code") == 200:
            debug_path = _save_debug_html(raw)
            log.warning(
                "energy_gov returned HTTP 200 but parsed zero items; saved debug html",
                extra={"debug_html": str(debug_path), "html_length": len(raw)},
            )

        log.info("parsed policy list", extra={"count": len(out), "url": self._site_url})
        return out


def _extract_date(text: str) -> Optional[str]:
    if not text:
        return None
    m = _DATE_RE.search(text)
    if not m:
        return None
    value = m.group(0)
    if "年" in value:
        value = value.replace("年", "-").replace("月", "-").replace("日", "")
    return value


def _make_summary(text: str, *, title: str, publish_date: Optional[str]) -> Optional[str]:
    if not text:
        return None
    summary = text
    if title:
        summary = summary.replace(title, "").strip()
    if publish_date:
        summary = summary.replace(publish_date, "").strip()
    summary = summary.strip("()（） \t")
    return summary[:300] if summary else None


def _save_debug_html(html: str) -> Path:
    path = Path(__file__).resolve().parents[2] / "debug_html" / "energy_gov.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return path
