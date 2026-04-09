from __future__ import annotations

from typing import List

from data_pipeline.base.processor import BaseProcessor
from data_pipeline.core.context import RunContext
from data_pipeline.core.logging import get_ctx_logger
from data_pipeline.registry.processors import register_processor
from data_pipeline.storage.energy_policy_db import EnergyPolicyRow


@register_processor("energy_gov")
class PolicyProcessor(BaseProcessor[EnergyPolicyRow, EnergyPolicyRow]):
    """
    energy_gov 已调整为抓取政策列表页（HTML -> 结构化记录）。
    当前 processor 作为轻量校验/清洗入口：去空、截断超长字段。
    """

    name = "policy_processor"

    def process(self, items: List[EnergyPolicyRow], ctx: RunContext) -> List[EnergyPolicyRow]:
        log = get_ctx_logger(__name__, ctx=ctx)
        out: List[EnergyPolicyRow] = []
        for idx, it in enumerate(items):
            try:
                title = (it.title or "").strip()
                url = (it.url or "").strip()
                if not title or not url:
                    continue
                out.append(
                    EnergyPolicyRow(
                        title=title[:500],
                        url=url[:800],
                        publish_date=(it.publish_date or None),
                        summary=(it.summary[:2000] if it.summary else None),
                        source=(it.source or "nea")[:50],
                        source_url=(it.source_url[:800] if it.source_url else None),
                    )
                )
            except Exception as e:
                # 单条失败不影响整体
                log.warning("process item failed", extra={"item_index": idx, "url": getattr(it, "url", None), "error": str(e)})
        return out

