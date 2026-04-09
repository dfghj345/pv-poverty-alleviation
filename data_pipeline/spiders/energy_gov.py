from __future__ import annotations

if __package__ is None:
    # 支持直接运行：python data_pipeline/spiders/energy_gov.py
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


@register_spider("energy_gov")
class EnergyGovSpider(BaseSpider[str, EnergyPolicyRow]):
    name = "energy_gov"
    site = "energy_gov"
    data_type = "energy_policy"

    def __init__(self) -> None:
        # 依赖注入：由 runner 在运行时设置（见 scheduler/runner.py）
        self._http: HttpClient | None = None
        self._request_opt: RequestOptions | None = None
        self._site_url: str | None = None

    async def fetch(self, ctx: RunContext) -> str:
        if self._http is None or self._request_opt is None or self._site_url is None:
            raise RuntimeError("spider dependencies not injected (runner should set _http/_request_opt/_site_url)")
        log = get_ctx_logger(__name__, ctx=ctx)
        html = await self._http.get_text(self._site_url, params=None, ctx=ctx, opt=self._request_opt)
        log.info("fetched html", extra={"bytes": len(html.encode('utf-8', errors='ignore'))})
        return html

    def parse(self, raw: str, ctx: RunContext) -> List[EnergyPolicyRow]:
        log = get_ctx_logger(__name__, ctx=ctx)
        soup = BeautifulSoup(raw, "lxml")

        # /zcfb/ 页面核心是“标题 + (YYYY-MM-DD)”列表项，链接常见两类：
        # - www.nea.gov.cn/2017-xx/xx/c_xxx.htm
        # - zfxxgk.nea.gov.cn/auto../yyyyMM/t....htm
        # 不能只过滤 /zcfb/，否则会导致 items=0
        lis = soup.select("div.text_list li") or soup.find_all("li")
        out: List[EnergyPolicyRow] = []
        seen: set[str] = set()

        for li in lis:
            a = li.find("a", href=True) if hasattr(li, "find") else None
            if a is None:
                continue
            title = (a.get_text() or "").strip()
            href = (a.get("href") or "").strip()
            if not title or not href:
                continue
            if len(title) < 6:
                continue

            url = urljoin(self._site_url or ctx.url or "", href)
            if ("nea.gov.cn" not in url) and ("zfxxgk.nea.gov.cn" not in url):
                continue
            if url in seen:
                continue

            li_text = " ".join(li.stripped_strings) if hasattr(li, "stripped_strings") else title
            publish_date = _extract_date(li_text)
            summary = _make_summary(li_text, title=title, publish_date=publish_date)

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

        log.info("parsed policy list", extra={"count": len(out), "url": self._site_url})
        return out


_DATE_RE = re.compile(r"(20\d{2}[-/.]\d{1,2}[-/.]\d{1,2})|(20\d{2}年\d{1,2}月\d{1,2}日)")


def _extract_date(text: str) -> Optional[str]:
    if not text:
        return None
    m = _DATE_RE.search(text)
    if not m:
        return None
    v = m.group(0)
    if "年" in v:
        v = v.replace("年", "-").replace("月", "-").replace("日", "")
    return v


def _make_summary(text: str, *, title: str, publish_date: Optional[str]) -> Optional[str]:
    if not text:
        return None
    s = text
    if title:
        s = s.replace(title, "").strip()
    if publish_date:
        s = s.replace(publish_date, "").strip()
    s = s.strip("()（） \t")
    return s[:300] if s else None