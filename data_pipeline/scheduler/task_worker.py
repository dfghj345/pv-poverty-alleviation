from __future__ import annotations

from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource

from data_pipeline.core.config import get_site
from data_pipeline.core.config import pipeline_settings
from data_pipeline.core.logging import configure_logging, get_logger
from data_pipeline.spiders.energy_gov import EnergyGovSpider
from data_pipeline.processors.policy_cleaner import PolicyProcessor
from data_pipeline.scheduler.runner import PipelineRunner
from data_pipeline.storage.db import PolicyStorage

logger = get_logger(__name__)

try:
    import taskiq_aiopg  # type: ignore
except Exception:  # pragma: no cover
    taskiq_aiopg = None  # type: ignore[assignment]

if pipeline_settings.TASKIQ_BROKER_DSN is None:
    raise RuntimeError("TASKIQ_BROKER_DSN is not configured; scheduler requires a PostgreSQL broker DSN")
if taskiq_aiopg is None:
    raise RuntimeError("taskiq-aiopg is not installed; scheduler is isolated from the main pipeline flow")

broker = taskiq_aiopg.AioPGBroker(pipeline_settings.TASKIQ_BROKER_DSN)
scheduler = TaskiqScheduler(broker, sources=[LabelScheduleSource(broker)])


_CRON = get_site("energy_gov").cron or "0 2 * * *"
@broker.task(schedule=[{"cron": _CRON}])
async def daily_policy_sync() -> None:
    configure_logging(pipeline_settings.LOG_LEVEL)

    spider = EnergyGovSpider()
    processor = PolicyProcessor()
    storage = PolicyStorage()

    runner = PipelineRunner()
    result = await runner.run(spider, processor=processor, storage=storage, stage="crawl")
    if result.summary.status == "ok":
        logger.info(
            "daily policy sync completed",
            extra={"run_id": result.summary.run_id, "count": result.summary.items_count, "duration_ms": result.summary.duration_ms},
        )
    else:
        logger.error(
            "daily policy sync failed",
            extra={
                "run_id": result.summary.run_id,
                "duration_ms": result.summary.duration_ms,
                "fetch_errors": [e.to_dict() for e in result.details.errors.fetch_errors],
                "parse_errors": [e.to_dict() for e in result.details.errors.parse_errors],
                "process_errors": [e.to_dict() for e in result.details.errors.process_errors],
                "store_errors": [e.to_dict() for e in result.details.errors.store_errors],
            },
        )