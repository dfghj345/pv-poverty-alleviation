from __future__ import annotations
if __package__ is None:
    # 支持直接运行：python data_pipeline/run_all_spiders.py
    from importlib.util import module_from_spec, spec_from_file_location
    from pathlib import Path

    _bootstrap_path = Path(__file__).resolve().parents[0] / "_bootstrap.py"
    _spec = spec_from_file_location("data_pipeline._bootstrap", _bootstrap_path)
    if _spec is None or _spec.loader is None:
        raise RuntimeError(f"Failed to load bootstrap from {_bootstrap_path}")
    _mod = module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    _mod.ensure_project_root_on_syspath(__file__)

import argparse
import asyncio
import json
import sys
from time import perf_counter
from typing import Any, Optional
import importlib
import pkgutil
import traceback

from data_pipeline.core.config import pipeline_settings
from data_pipeline.core.context import RunContext
from data_pipeline.core.logging import configure_logging
from data_pipeline.registry.processors import get_processor
from data_pipeline.registry.spiders import get_spider, list_spiders
from data_pipeline.registry.storages import get_storage
from data_pipeline.scheduler.runner import PipelineRunner


def make_loop():
    if sys.platform.startswith("win"):
        loop = asyncio.SelectorEventLoop()
        asyncio.set_event_loop(loop)
        return loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop


def _import_all_submodules(package_name: str) -> None:
    """
    通过 import 触发注册（spiders/processors/storages 均使用装饰器注册）。
    """
    pkg = importlib.import_module(package_name)
    pkg_path = getattr(pkg, "__path__", None)
    if pkg_path is None:
        return
    for m in pkgutil.iter_modules(pkg_path):
        if m.ispkg:
            continue
        importlib.import_module(f"{package_name}.{m.name}")


def _make_storage(spider_name: str):
    SpiderCls = get_spider(spider_name)
    spider = SpiderCls()  # type: ignore[call-arg]
    data_type = getattr(spider, "data_type", None) or spider_name
    site = getattr(spider, "site", spider_name)
    return get_storage(spider=spider_name, site=site, data_type=str(data_type))


async def _run_one(spider_name: str, stage: str) -> dict[str, Any]:
    SpiderCls = get_spider(spider_name)
    spider = SpiderCls()  # type: ignore[call-arg]
    runner = PipelineRunner()
    ctx = RunContext(spider=spider_name, site=getattr(spider, "site", spider_name), stage="run_all")
    processor = get_processor(spider_name)
    storage = _make_storage(spider_name)

    t0 = perf_counter()
    rep = await runner.run(spider, processor=processor, storage=storage, stage=stage, ctx=ctx)
    err0 = rep.details.errors.all()[0].to_dict() if rep.details.errors.any() else None
    result = {
        "run_id": rep.summary.run_id,
        "spider": spider_name,
        "site": rep.summary.site,
        "url": rep.summary.url,
        "stage": _public_stage(rep.summary.stage),
        "items_count": rep.summary.items_count,
        "duration_ms": rep.summary.duration_ms,
        "error": err0,
    }
    return {
        **result,
        "status": rep.summary.status,
        "skipped_reason": rep.summary.skipped_reason,
        "result": result,
        "request_log": rep.details.meta.get("request_log"),
        "elapsed_ms_wall": int((perf_counter() - t0) * 1000),
    }


async def amain(argv: Optional[list[str]] = None) -> int:
    # Windows 控制台默认编码可能是 gbk，打印包含特殊连字符等字符会触发 UnicodeEncodeError
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except Exception:
            pass
    parser = argparse.ArgumentParser(prog="python data_pipeline/run_all_spiders.py")
    parser.add_argument("--spider", type=str, help="仅运行指定 spider（例如 energy_gov）")
    parser.add_argument("--stage", type=str, default="crawl", choices=["fetch", "parse", "process", "store", "crawl"], help="跑到哪一阶段就停")
    args = parser.parse_args(argv)

    configure_logging(pipeline_settings.LOG_LEVEL)

    # 触发自动注册
    _import_all_submodules("data_pipeline.spiders")
    _import_all_submodules("data_pipeline.processors")
    _import_all_submodules("data_pipeline.storage")

    spiders = [args.spider] if args.spider else list_spiders()
    if not spiders:
        print("未发现已注册的 spider（data_pipeline/registry/spiders.py 的注册表为空）")
        return 2

    print(f"将运行 spiders={spiders} stage={args.stage}")

    out: list[dict[str, Any]] = []
    for sp in spiders:
        if sp is None:
            continue
        t0 = perf_counter()
        try:
            r = await _run_one(sp, args.stage)
            out.append(r)
            if r.get("request_log"):
                print("REQUEST " + json.dumps(r["request_log"], ensure_ascii=False, default=str))
            if r.get("skipped_reason"):
                print(f"WARNING spider={r['spider']} stage={r['stage']} {r['skipped_reason']}")
            print("RESULT " + json.dumps(r["result"], ensure_ascii=False, default=str))
        except Exception as e:
            err = {
                "stage": _public_stage(args.stage),
                "type": type(e).__name__,
                "message": str(e),
                "url": None,
                "item_index": None,
                "traceback_optional": traceback.format_exc(),
            }
            failed_result = {
                "run_id": None,
                "spider": sp,
                "site": None,
                "url": None,
                "stage": _public_stage(args.stage),
                "items_count": 0,
                "duration_ms": int((perf_counter() - t0) * 1000),
                "error": err,
            }
            out.append({**failed_result, "status": "fail", "result": failed_result})
            print(f"[FAIL] spider={sp} error={e}\n{traceback.format_exc()}")
            print("RESULT " + json.dumps(failed_result, ensure_ascii=False, default=str))

    results = out
    ok = sum(1 for r in results if r.get("status") == "ok")
    skipped = sum(1 for r in results if r.get("status") == "skipped")
    fail = len(results) - ok - skipped
    print(f"\n=== run summary === total={len(results)} ok={ok} skipped={skipped} fail={fail}")
    return 0 if fail == 0 else 1


def _public_stage(stage: str) -> str:
    if stage == "store":
        return "store"
    if stage in {"parse", "process"}:
        return "parse"
    return "crawl"


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(amain(), loop_factory=make_loop))
    except TypeError:
        # 兼容旧版 Python：asyncio.run 不支持 loop_factory 参数
        _loop = make_loop()
        try:
            raise SystemExit(_loop.run_until_complete(amain()))
        finally:
            _loop.close()

