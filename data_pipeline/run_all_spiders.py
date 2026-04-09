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
    return {
        "spider": spider_name,
        "site": rep.summary.site,
        "stage": rep.summary.stage,
        "status": rep.summary.status,
        "items_count": rep.summary.items_count,
        "duration_ms": rep.summary.duration_ms,
        "skipped_reason": rep.summary.skipped_reason,
        "run_id": rep.summary.run_id,
        "error_detail": err0,
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
            print(
                f"[{r['status'].upper()}] spider={r['spider']} site={r['site']} "
                f"stage={r['stage']} items={r['items_count']} duration_ms={r['duration_ms']} run_id={r['run_id']}"
                + (f" skipped_reason={r['skipped_reason']}" if r.get("skipped_reason") else "")
            )
            if r.get("status") == "fail" and r.get("error_detail"):
                ed = r["error_detail"]
                print(f"  error: stage={ed.get('stage')} type={ed.get('type')} message={ed.get('message')}")
        except Exception as e:
            out.append(
                {
                    "spider": sp,
                    "status": "fail",
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                    "elapsed_ms_wall": int((perf_counter() - t0) * 1000),
                }
            )
            print(f"[FAIL] spider={sp} error={e}\n{traceback.format_exc()}")

    results = out
    ok = sum(1 for r in results if r.get("status") == "ok")
    skipped = sum(1 for r in results if r.get("status") == "skipped")
    fail = len(results) - ok - skipped
    print(f"\n=== run summary === total={len(results)} ok={ok} skipped={skipped} fail={fail}")
    return 0 if fail == 0 else 1


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

