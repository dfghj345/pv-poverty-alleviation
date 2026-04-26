from __future__ import annotations

if __package__ is None:
    # 支持直接运行：python data_pipeline/scheduler/runner.py
    from importlib.util import module_from_spec, spec_from_file_location
    from pathlib import Path

    _bootstrap_path = Path(__file__).resolve().parents[1] / "_bootstrap.py"
    _spec = spec_from_file_location("data_pipeline._bootstrap", _bootstrap_path)
    if _spec is None or _spec.loader is None:
        raise RuntimeError(f"Failed to load bootstrap from {_bootstrap_path}")
    _mod = module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    _mod.ensure_project_root_on_syspath(__file__)

import json
from time import perf_counter
from typing import Any, Optional
import traceback

from data_pipeline.base.processor import BaseProcessor
from data_pipeline.base.storage import BaseStorage, StoreResult
from data_pipeline.base.spider import BaseSpider
from data_pipeline.core.config import get_site, pipeline_settings
from data_pipeline.core.context import RunContext
from data_pipeline.core.logging import get_ctx_logger
from data_pipeline.core.request import HttpClient, PlaywrightHtmlClient, RequestOptions
from data_pipeline.core.results import ErrorDetail, PipelineDetails, PipelineReport, PipelineSummary, StageErrors
from data_pipeline.registry.storages import get_storage


class PipelineRunner:
    def __init__(
        self,
        *,
        http: Optional[HttpClient] = None,
        browser: Optional[PlaywrightHtmlClient] = None,
    ) -> None:
        self.http = http or HttpClient()
        self.browser = browser or PlaywrightHtmlClient()

    async def run(
        self,
        spider: BaseSpider[Any, Any],
        *,
        processor: Optional[BaseProcessor[Any, Any]] = None,
        storage: Optional[BaseStorage[Any]] = None,
        stage: str = "crawl",
        ctx: Optional[RunContext] = None,
    ) -> PipelineReport:
        site_cfg = get_site(spider.site)
        base_ctx = ctx or RunContext(spider=spider.name, site=spider.site, stage="crawl", url=site_cfg.url)
        log = get_ctx_logger(__name__, ctx=base_ctx)

        # spider 级别降级/禁用：不硬崩全量运行
        if getattr(spider, "enabled", True) is False:
            reason = getattr(spider, "disabled_reason", "") or "spider disabled"
            log.warning("spider skipped (disabled)", extra={"reason": reason})
            return PipelineReport(
                summary=PipelineSummary(
                    run_id=base_ctx.run_id,
                    spider=spider.name,
                    site=spider.site,
                    url=site_cfg.url,
                    stage=stage,
                    items_count=0,
                    duration_ms=0,
                    status="skipped",
                    skipped_reason=reason,
                ),
                details=PipelineDetails(stage_durations_ms={}, errors=StageErrors(), meta={}),
            )

        opt = RequestOptions(
            timeout_s=site_cfg.timeout_s,
            retries=site_cfg.retries,
            retry_base_delay_s=site_cfg.retry_base_delay_s,
            headers=site_cfg.headers,
            user_agent=site_cfg.user_agent,
        )

        # 给 spider 一个简单的依赖注入方式（不强制，但可用）
        setattr(spider, "_http", self.http)
        setattr(spider, "_browser", self.browser)
        setattr(spider, "_request_opt", opt)
        setattr(spider, "_site_url", site_cfg.url)

        t0 = perf_counter()
        stage_durations: dict[str, int] = {}
        errors = StageErrors()
        meta: dict[str, Any] = {}

        def _err(stage_name: str, exc: BaseException, *, url: Optional[str], item_index: Optional[int] = None, with_tb: bool = True) -> ErrorDetail:
            return ErrorDetail(
                stage=stage_name,
                type=type(exc).__name__,
                message=str(exc),
                url=url,
                item_index=item_index,
                traceback_optional=traceback.format_exc() if with_tb else None,
            )

        def _report(status: str, done_stage: str, items_count: int, duration_ms: int, *, skipped_reason: Optional[str] = None) -> PipelineReport:
            return PipelineReport(
                summary=PipelineSummary(
                    run_id=base_ctx.run_id,
                    spider=spider.name,
                    site=spider.site,
                    url=site_cfg.url,
                    stage=done_stage,
                    items_count=items_count,
                    duration_ms=duration_ms,
                    status=status,  # ok | fail | skipped
                    skipped_reason=skipped_reason,
                ),
                details=PipelineDetails(
                    stage_durations_ms=stage_durations,
                    errors=errors,
                    meta=dict(meta),
                ),
            )

        try:
            # 语义：stage 表示“跑到哪一阶段就停”，前置阶段仍会执行
            # 约定：
            # - fetch/parse/process/store：精确停在对应阶段
            # - crawl：停在 process（不触发 store），用于“只采集+解析+清洗”的最小闭环
            fctx = base_ctx.with_stage("fetch", url=site_cfg.url)
            f0 = perf_counter()
            try:
                raw = await spider.fetch(fctx)
            except Exception as e:
                tb = traceback.format_exc()
                errors.fetch_errors.append(_err("crawl", e, url=site_cfg.url))
                stage_durations["fetch"] = int((perf_counter() - f0) * 1000)
                meta["request_log"] = _request_log(
                    spider=spider.name,
                    url=site_cfg.url,
                    fetch_meta=fctx.meta,
                    html_length=int(fctx.meta.get("http_content_length") or 0),
                    parsed_item_count=0,
                    duration_ms=stage_durations["fetch"],
                )
                dur = int((perf_counter() - t0) * 1000)
                # 打出完整失败上下文，便于定位“为什么 fetch 失败”（包含最后一次失败原因与 traceback）
                log.error(
                    "fetch failed",
                    extra={
                        "run_id": base_ctx.run_id,
                        "spider": spider.name,
                        "site": spider.site,
                        "url": site_cfg.url,
                        "exception_type": type(e).__name__,
                        "exception_message": str(e),
                        "traceback": tb,
                    },
                    exc_info=True,
                )
                return _report("fail", stage, 0, dur)
            stage_durations["fetch"] = int((perf_counter() - f0) * 1000)
            if stage == "fetch":
                meta["request_log"] = _request_log(
                    spider=spider.name,
                    url=site_cfg.url,
                    fetch_meta=fctx.meta,
                    html_length=_raw_length(raw),
                    parsed_item_count=0,
                    duration_ms=int((perf_counter() - f0) * 1000),
                )
                return _report("ok", "fetch", 1, int((perf_counter() - t0) * 1000))

            pctx = base_ctx.with_stage("parse", url=site_cfg.url, **fctx.meta)
            p0 = perf_counter()
            try:
                items = spider.parse(raw, pctx)
                spider.validate_items(items, pctx)
            except Exception as e:
                errors.parse_errors.append(_err("parse", e, url=site_cfg.url))
                stage_durations["parse"] = int((perf_counter() - p0) * 1000)
                meta["request_log"] = _request_log(
                    spider=spider.name,
                    url=site_cfg.url,
                    fetch_meta=fctx.meta,
                    html_length=_raw_length(raw),
                    parsed_item_count=0,
                    duration_ms=stage_durations["fetch"] + stage_durations["parse"],
                )
                dur = int((perf_counter() - t0) * 1000)
                log.error(f"parse failed: {type(e).__name__}: {e}", exc_info=True)
                return _report("fail", stage, 0, dur)
            stage_durations["parse"] = int((perf_counter() - p0) * 1000)
            meta["request_log"] = _request_log(
                spider=spider.name,
                url=site_cfg.url,
                fetch_meta=fctx.meta,
                html_length=_raw_length(raw),
                parsed_item_count=len(items),
                duration_ms=stage_durations["fetch"] + stage_durations["parse"],
            )
            log.info("spider request completed", extra=meta["request_log"])
            if stage == "parse":
                return _report("ok", "parse", len(items), int((perf_counter() - t0) * 1000))

            if processor is not None:
                prctx = base_ctx.with_stage("process", url=site_cfg.url, **fctx.meta)
                pr0 = perf_counter()
                try:
                    items = processor.process(items, prctx)  # type: ignore[assignment,arg-type]
                except Exception as e:
                    errors.process_errors.append(_err("parse", e, url=site_cfg.url))
                    stage_durations["process"] = int((perf_counter() - pr0) * 1000)
                    dur = int((perf_counter() - t0) * 1000)
                    log.error(f"process failed: {type(e).__name__}: {e}", exc_info=True)
                    return _report("fail", stage, 0, dur)
                stage_durations["process"] = int((perf_counter() - pr0) * 1000)
                meta["request_log"]["parsed_item_count"] = len(items)
            if stage == "process":
                return _report("ok", "process", len(items), int((perf_counter() - t0) * 1000))

            if stage == "crawl":
                # crawl 不做入库
                return _report("ok", "crawl", len(items), int((perf_counter() - t0) * 1000))

            # storage 分发：优先使用入参 storage；否则走 registry
            if storage is None:
                data_type = getattr(spider, "data_type", None) or spider.name
                storage = get_storage(spider=spider.name, site=spider.site, data_type=str(data_type))

            if storage is not None:
                if getattr(pipeline_settings, "PIPELINE_DATABASE_URL", None) is None:
                    reason = "PIPELINE_DATABASE_URL is not configured; skipped store"
                    log.warning(reason)
                    dur = int((perf_counter() - t0) * 1000)
                    stage_durations["store"] = 0
                    return _report("skipped", "store", 0, dur, skipped_reason=reason)
                sctx = base_ctx.with_stage("store", url=site_cfg.url)
                s0 = perf_counter()
                try:
                    r: StoreResult = await storage.store(items, sctx)  # type: ignore[arg-type]
                except Exception as e:
                    # --stage store 时缺少 DB 配置：标记为 skipped，不中断测试
                    if stage == "store" and isinstance(e, RuntimeError) and "PIPELINE_DATABASE_URL" in str(e):
                        stage_durations["store"] = int((perf_counter() - s0) * 1000)
                        dur = int((perf_counter() - t0) * 1000)
                        return _report("skipped", "store", 0, dur, skipped_reason=str(e))

                    errors.store_errors.append(_err("store", e, url=site_cfg.url))
                    stage_durations["store"] = int((perf_counter() - s0) * 1000)
                    dur = int((perf_counter() - t0) * 1000)
                    log.error(f"store failed: {type(e).__name__}: {e}", exc_info=True)
                    return _report("fail", stage, 0, dur)
                stage_durations["store"] = int((perf_counter() - s0) * 1000)
                if r.store_errors:
                    errors.store_errors.extend(r.store_errors)
                if stage == "store":
                    ok = r.failed == 0
                    rep = _report("ok" if ok else "fail", "store", r.stored, int((perf_counter() - t0) * 1000))
                    if (not ok) and r.error:
                        # 汇总错误信息也放到 details.meta，便于消费
                        rep.details.meta["store_error_summary"] = r.error
                    return rep
            else:
                if stage == "store":
                    dur = int((perf_counter() - t0) * 1000)
                    return _report("skipped", "store", 0, dur, skipped_reason="no storage registered for this spider/site/data_type")

            # 若未显式要求 store，但走到了这里，说明 stage 传参不在约定范围
            return _report("ok", stage, len(items), int((perf_counter() - t0) * 1000))
        except Exception as e:
            # 理论上不会到这里（每阶段已拦截），但保底
            errors.fetch_errors.append(_err("crawl", e, url=site_cfg.url))
            log.error(f"pipeline failed: {type(e).__name__}: {e}", exc_info=True)
            return _report("fail", stage, 0, int((perf_counter() - t0) * 1000))


def _raw_length(raw: Any) -> int:
    if raw is None:
        return 0
    if isinstance(raw, bytes):
        return len(raw)
    if isinstance(raw, str):
        return len(raw)
    try:
        return len(json.dumps(raw, ensure_ascii=False, default=str))
    except Exception:
        return 0


def _request_log(
    *,
    spider: str,
    url: str,
    fetch_meta: dict[str, Any],
    html_length: int,
    parsed_item_count: int,
    duration_ms: int,
) -> dict[str, Any]:
    return {
        "spider": spider,
        "url": url,
        "status_code": fetch_meta.get("http_status_code"),
        "final_url": fetch_meta.get("http_final_url") or fetch_meta.get("http_request_url") or url,
        "html_length": html_length,
        "parsed_item_count": parsed_item_count,
        "duration_ms": duration_ms,
    }

