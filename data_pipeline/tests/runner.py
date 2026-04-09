from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from time import perf_counter
from typing import Any, List, Optional

from data_pipeline.core.config import pipeline_settings
from data_pipeline.core.context import RunContext
from data_pipeline.core.logging import configure_logging, get_logger
from data_pipeline.core.results import ErrorDetail, PipelineDetails, PipelineReport, PipelineSummary, StageErrors
from data_pipeline.registry.processors import get_processor
from data_pipeline.registry.spiders import get_spider, list_spiders
from data_pipeline.scheduler.runner import PipelineRunner
from data_pipeline.registry.storages import get_storage

# 确保导入 spiders 触发注册
from data_pipeline.spiders import energy_gov as _energy_gov  # noqa: F401
from data_pipeline.spiders import weather_data as _weather_data  # noqa: F401
from data_pipeline.spiders import open_meteo_radiation as _open_meteo_radiation  # noqa: F401
from data_pipeline.spiders import poverty_regions as _poverty_regions  # noqa: F401
from data_pipeline.spiders import city_location_reference as _city_location_reference  # noqa: F401
from data_pipeline.spiders import policy_tariff_reference as _policy_tariff_reference  # noqa: F401
from data_pipeline.spiders import county_region_reference as _county_region_reference  # noqa: F401
from data_pipeline.processors import policy_cleaner as _policy_cleaner  # noqa: F401
from data_pipeline.processors import weather_processor as _weather_processor  # noqa: F401
from data_pipeline.processors import open_meteo_radiation_processor as _open_meteo_radiation_processor  # noqa: F401
from data_pipeline.processors import poverty_cleaner as _poverty_cleaner  # noqa: F401
from data_pipeline.processors import cost_cleaner as _cost_cleaner  # noqa: F401
from data_pipeline.processors import generation_cleaner as _generation_cleaner  # noqa: F401
from data_pipeline.processors import city_location_cleaner as _city_location_cleaner  # noqa: F401
from data_pipeline.processors import policy_tariff_cleaner as _policy_tariff_cleaner  # noqa: F401
from data_pipeline.processors import county_region_cleaner as _county_region_cleaner  # noqa: F401
from data_pipeline.storage import db as _db_storage  # noqa: F401
from data_pipeline.storage import weather_radiation_db as _weather_radiation_db  # noqa: F401
from data_pipeline.storage import poverty_db as _poverty_db  # noqa: F401
from data_pipeline.storage import cost_db as _cost_db  # noqa: F401
from data_pipeline.storage import city_location_db as _city_location_db  # noqa: F401
from data_pipeline.spiders import pv_costs as _pv_costs  # noqa: F401
from data_pipeline.storage import generation_db as _generation_db  # noqa: F401
from data_pipeline.spiders import pv_generation as _pv_generation  # noqa: F401


logger = get_logger(__name__)


@dataclass(slots=True)
class TestSummary:
    report: PipelineReport


def _make_processor(spider_name: str):
    return get_processor(spider_name)


def _make_storage(spider_name: str):
    # 由 storage registry 分发
    SpiderCls = get_spider(spider_name)
    spider = SpiderCls()  # type: ignore[call-arg]
    data_type = getattr(spider, "data_type", None) or spider_name
    return get_storage(spider=spider_name, site=getattr(spider, "site", spider_name), data_type=str(data_type))


async def _run_one(spider_name: str, stage: str) -> TestSummary:
    SpiderCls = get_spider(spider_name)
    spider = SpiderCls()  # type: ignore[call-arg]
    runner = PipelineRunner()
    ctx = RunContext(spider=spider_name, site=getattr(spider, "site", spider_name), stage="test")
    processor = _make_processor(spider_name)
    storage = _make_storage(spider_name)
    rep = await runner.run(spider, processor=processor, storage=storage, stage=stage, ctx=ctx)
    return TestSummary(report=rep)


def _load_case_text(spider_name: str) -> str:
    raise RuntimeError("deprecated: use _load_case_data()")


def _load_case_data(spider_name: str) -> Any:
    import json
    import os

    here = os.path.dirname(__file__)
    html_path = os.path.join(here, "cases", f"{spider_name}_sample.html")
    json_path = os.path.join(here, "cases", f"{spider_name}_sample.json")

    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    raise FileNotFoundError(f"no offline case found for spider={spider_name} (expected {html_path} or {json_path})")


async def _run_offline_case(spider_name: str, stage: str) -> TestSummary:
    SpiderCls = get_spider(spider_name)
    spider = SpiderCls()  # type: ignore[call-arg]
    ctx = RunContext(spider=spider_name, site=getattr(spider, "site", spider_name), stage="test", url="offline://case")
    t0 = perf_counter()
    stage_durations: dict[str, int] = {}
    errors = StageErrors()
    try:
        raw = _load_case_data(spider_name)
        p0 = perf_counter()
        try:
            items = spider.parse(raw, ctx.with_stage("parse", url="offline://case"))  # type: ignore[arg-type]
        except Exception as e:
            errors.parse_errors.append(
                ErrorDetail(
                    stage="parse",
                    type=type(e).__name__,
                    message=str(e),
                    url="offline://case",
                    item_index=None,
                    traceback_optional=None,
                )
            )
            stage_durations["parse"] = int((perf_counter() - p0) * 1000)
            rep = PipelineReport(
                summary=PipelineSummary(
                    run_id=ctx.run_id,
                    spider=spider_name,
                    site=getattr(spider, "site", spider_name),
                    url="offline://case",
                    stage=stage,
                    items_count=0,
                    duration_ms=int((perf_counter() - t0) * 1000),
                    status="fail",
                    skipped_reason=None,
                ),
                details=PipelineDetails(stage_durations_ms=stage_durations, errors=errors, meta={}),
            )
            return TestSummary(report=rep)
        stage_durations["parse"] = int((perf_counter() - p0) * 1000)
        if stage == "parse":
            rep = PipelineReport(
                summary=PipelineSummary(
                    run_id=ctx.run_id,
                    spider=spider_name,
                    site=getattr(spider, "site", spider_name),
                    url="offline://case",
                    stage="parse",
                    items_count=len(items),
                    duration_ms=int((perf_counter() - t0) * 1000),
                    status="ok",
                    skipped_reason=None,
                ),
                details=PipelineDetails(stage_durations_ms=stage_durations, errors=errors, meta={}),
            )
            return TestSummary(report=rep)

        processor = _make_processor(spider_name)
        if processor is None:
            errors.process_errors.append(
                ErrorDetail(
                    stage="process",
                    type="ProcessorNotRegistered",
                    message="no processor registered for this spider",
                    url="offline://case",
                    item_index=None,
                    traceback_optional=None,
                )
            )
            rep = PipelineReport(
                summary=PipelineSummary(
                    run_id=ctx.run_id,
                    spider=spider_name,
                    site=getattr(spider, "site", spider_name),
                    url="offline://case",
                    stage=stage,
                    items_count=0,
                    duration_ms=int((perf_counter() - t0) * 1000),
                    status="fail",
                    skipped_reason=None,
                ),
                details=PipelineDetails(stage_durations_ms=stage_durations, errors=errors, meta={}),
            )
            return TestSummary(report=rep)
        pr0 = perf_counter()
        try:
            items2 = processor.process(items, ctx.with_stage("process", url="offline://case"))  # type: ignore[arg-type]
        except Exception as e:
            errors.process_errors.append(
                ErrorDetail(
                    stage="process",
                    type=type(e).__name__,
                    message=str(e),
                    url="offline://case",
                    item_index=None,
                    traceback_optional=None,
                )
            )
            stage_durations["process"] = int((perf_counter() - pr0) * 1000)
            rep = PipelineReport(
                summary=PipelineSummary(
                    run_id=ctx.run_id,
                    spider=spider_name,
                    site=getattr(spider, "site", spider_name),
                    url="offline://case",
                    stage=stage,
                    items_count=0,
                    duration_ms=int((perf_counter() - t0) * 1000),
                    status="fail",
                    skipped_reason=None,
                ),
                details=PipelineDetails(stage_durations_ms=stage_durations, errors=errors, meta={}),
            )
            return TestSummary(report=rep)
        stage_durations["process"] = int((perf_counter() - pr0) * 1000)
        if stage == "process":
            rep = PipelineReport(
                summary=PipelineSummary(
                    run_id=ctx.run_id,
                    spider=spider_name,
                    site=getattr(spider, "site", spider_name),
                    url="offline://case",
                    stage="process",
                    items_count=len(items2),
                    duration_ms=int((perf_counter() - t0) * 1000),
                    status="ok",
                    skipped_reason=None,
                ),
                details=PipelineDetails(stage_durations_ms=stage_durations, errors=errors, meta={}),
            )
            return TestSummary(report=rep)

        # 离线 store：parse→process→store（不走网络）
        if stage == "store":
            storage = _make_storage(spider_name)
            if storage is None:
                rep = PipelineReport(
                    summary=PipelineSummary(
                        run_id=ctx.run_id,
                        spider=spider_name,
                        site=getattr(spider, "site", spider_name),
                        url="offline://case",
                        stage="store",
                        items_count=0,
                        duration_ms=int((perf_counter() - t0) * 1000),
                        status="skipped",
                        skipped_reason="no storage registered for this spider/site/data_type",
                    ),
                    details=PipelineDetails(stage_durations_ms=stage_durations, errors=errors, meta={}),
                )
                return TestSummary(report=rep)

            s0 = perf_counter()
            try:
                r = await storage.store(items2, ctx.with_stage("store", url="offline://case"))  # type: ignore[arg-type]
                stage_durations["store"] = int((perf_counter() - s0) * 1000)
                rep = PipelineReport(
                    summary=PipelineSummary(
                        run_id=ctx.run_id,
                        spider=spider_name,
                        site=getattr(spider, "site", spider_name),
                        url="offline://case",
                        stage="store",
                        items_count=r.stored,
                        duration_ms=int((perf_counter() - t0) * 1000),
                        status="ok" if r.failed == 0 else "fail",
                        skipped_reason=None,
                    ),
                    details=PipelineDetails(stage_durations_ms=stage_durations, errors=errors, meta={"store_error_summary": r.error} if r.error else {}),
                )
                if getattr(r, "store_errors", None):
                    errors.store_errors.extend(r.store_errors)
                return TestSummary(report=rep)
            except Exception as e:
                stage_durations["store"] = int((perf_counter() - s0) * 1000)
                msg = str(e)
                if isinstance(e, RuntimeError) and "PIPELINE_DATABASE_URL" in msg:
                    rep = PipelineReport(
                        summary=PipelineSummary(
                            run_id=ctx.run_id,
                            spider=spider_name,
                            site=getattr(spider, "site", spider_name),
                            url="offline://case",
                            stage="store",
                            items_count=0,
                            duration_ms=int((perf_counter() - t0) * 1000),
                            status="skipped",
                            skipped_reason=msg,
                        ),
                        details=PipelineDetails(stage_durations_ms=stage_durations, errors=errors, meta={}),
                    )
                    return TestSummary(report=rep)
                errors.store_errors.append(
                    ErrorDetail(stage="store", type=type(e).__name__, message=msg, url="offline://case", item_index=None, traceback_optional=None)
                )
                rep = PipelineReport(
                    summary=PipelineSummary(
                        run_id=ctx.run_id,
                        spider=spider_name,
                        site=getattr(spider, "site", spider_name),
                        url="offline://case",
                        stage="store",
                        items_count=0,
                        duration_ms=int((perf_counter() - t0) * 1000),
                        status="fail",
                        skipped_reason=None,
                    ),
                    details=PipelineDetails(stage_durations_ms=stage_durations, errors=errors, meta={}),
                )
                return TestSummary(report=rep)

        # 离线 crawl：parse→process（不走 fetch/store）
        rep = PipelineReport(
            summary=PipelineSummary(
                run_id=ctx.run_id,
                spider=spider_name,
                site=getattr(spider, "site", spider_name),
                url="offline://case",
                stage="crawl",
                items_count=len(items2),
                duration_ms=int((perf_counter() - t0) * 1000),
                status="ok",
                skipped_reason=None,
            ),
            details=PipelineDetails(stage_durations_ms=stage_durations, errors=errors, meta={}),
        )
        return TestSummary(report=rep)
    except Exception as e:
        errors.fetch_errors.append(
            ErrorDetail(
                stage="crawl",
                type=type(e).__name__,
                message=str(e),
                url="offline://case",
                item_index=None,
                traceback_optional=None,
            )
        )
        rep = PipelineReport(
            summary=PipelineSummary(
                run_id=ctx.run_id,
                spider=spider_name,
                site=getattr(spider, "site", spider_name),
                url="offline://case",
                stage=stage,
                items_count=0,
                duration_ms=int((perf_counter() - t0) * 1000),
                status="fail",
                skipped_reason=None,
            ),
            details=PipelineDetails(stage_durations_ms=stage_durations, errors=errors, meta={}),
        )
        return TestSummary(report=rep)


def _print_report(summaries: List[TestSummary]) -> None:
    ok = sum(1 for s in summaries if s.report.summary.status == "ok")
    skipped = sum(1 for s in summaries if s.report.summary.status == "skipped")
    fail = len(summaries) - ok - skipped
    total_ms = sum(s.report.summary.duration_ms for s in summaries)
    print("\n=== data_pipeline test summary ===")
    print(f"total={len(summaries)} ok={ok} skipped={skipped} fail={fail} duration_ms={total_ms}")
    for s in summaries:
        r = s.report
        status = "OK" if r.summary.status == "ok" else ("SKIP" if r.summary.status == "skipped" else "FAIL")
        line = (
            f"- {status} run_id={r.summary.run_id} spider={r.summary.spider} site={r.summary.site} "
            f"url={r.summary.url} stage={r.summary.stage} items={r.summary.items_count} duration_ms={r.summary.duration_ms}"
        )
        if r.summary.skipped_reason:
            line += f" skipped_reason={r.summary.skipped_reason}"
        print(line)

    print("\n=== data_pipeline test details ===")
    for s in summaries:
        r = s.report
        print(f"\n--- spider={r.summary.spider} run_id={r.summary.run_id} ---")
        print("summary:", {
            "run_id": r.summary.run_id,
            "spider": r.summary.spider,
            "site": r.summary.site,
            "url": r.summary.url,
            "stage": r.summary.stage,
            "items_count": r.summary.items_count,
            "duration_ms": r.summary.duration_ms,
            "status": r.summary.status,
            "skipped_reason": r.summary.skipped_reason,
        })
        print("details:", {
            "stage_durations_ms": r.details.stage_durations_ms,
            "errors": r.details.errors.to_dict(),
        })


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m data_pipeline.tests.runner")
    parser.add_argument("--spider", type=str, help="spider 名称（例如 energy_gov）")
    parser.add_argument("--all", action="store_true", help="测试所有已注册 spider")
    parser.add_argument("--stage", type=str, default="crawl", choices=["fetch", "parse", "process", "store", "crawl"], help="测试阶段")
    parser.add_argument("--case", action="store_true", help="使用离线样例（tests/cases/<spider>_sample.*）跑 parse/process，不发网络请求")
    args = parser.parse_args(argv)

    configure_logging(pipeline_settings.LOG_LEVEL)

    if not args.all and not args.spider:
        print(f"available spiders: {', '.join(list_spiders())}")
        print("example: python -m data_pipeline.tests.runner --spider energy_gov --stage parse")
        return 2

    spiders = list_spiders() if args.all else [args.spider]

    async def _run() -> List[TestSummary]:
        out: List[TestSummary] = []
        for sp in spiders:
            if sp is None:
                continue
            if args.case:
                if args.stage not in ("parse", "process", "store", "crawl"):
                    out.append(
                        TestSummary(
                            report=PipelineReport(
                                summary=PipelineSummary(
                                    run_id=RunContext().run_id,
                                    spider=sp,
                                    site=sp,
                                    url="offline://case",
                                    stage=args.stage,
                                    items_count=0,
                                    duration_ms=0,
                                    status="fail",
                                    skipped_reason="--case only supports stage=parse/process/store/crawl",
                                ),
                                details=PipelineDetails(stage_durations_ms={}, errors=StageErrors(), meta={}),
                            )
                        )
                    )
                    continue
                out.append(await _run_offline_case(sp, args.stage))
            else:
                t0 = perf_counter()
                try:
                    out.append(await _run_one(sp, args.stage))
                except Exception as e:
                    # 保底：构造一个失败 report，确保测试入口不因异常分支 dataclass 不匹配而二次失败
                    out.append(
                        TestSummary(
                            report=PipelineReport(
                                summary=PipelineSummary(
                                    run_id=RunContext().run_id,
                                    spider=sp,
                                    site=sp,
                                    url="unknown://exception",
                                    stage=args.stage,
                                    items_count=0,
                                    duration_ms=int((perf_counter() - t0) * 1000),
                                    status="fail",
                                    skipped_reason=str(e),
                                ),
                                details=PipelineDetails(stage_durations_ms={}, errors=StageErrors(), meta={}),
                            )
                        )
                    )
        return out

    summaries = asyncio.run(_run())
    _print_report(summaries)
    # skipped 不视为失败
    return 0 if all(s.report.summary.status in ("ok", "skipped") for s in summaries) else 1


if __name__ == "__main__":
    raise SystemExit(main())

