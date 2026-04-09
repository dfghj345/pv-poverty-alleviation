from __future__ import annotations

if __package__ is None:
    from importlib.util import module_from_spec, spec_from_file_location
    from pathlib import Path

    _bootstrap_path = Path(__file__).resolve().parents[1] / '_bootstrap.py'
    _spec = spec_from_file_location('data_pipeline._bootstrap', _bootstrap_path)
    if _spec is None or _spec.loader is None:
        raise RuntimeError(f'Failed to load bootstrap from {_bootstrap_path}')
    _mod = module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    _mod.ensure_project_root_on_syspath(__file__)

import argparse
import asyncio
import csv
import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Sequence

# Import modules to trigger registry registration.
from data_pipeline.processors import city_location_cleaner as _city_location_cleaner  # noqa: F401
from data_pipeline.processors import cost_cleaner as _cost_cleaner  # noqa: F401
from data_pipeline.processors import county_region_cleaner as _county_region_cleaner  # noqa: F401
from data_pipeline.processors import open_meteo_radiation_processor as _open_meteo_radiation_processor  # noqa: F401
from data_pipeline.processors import policy_tariff_cleaner as _policy_tariff_cleaner  # noqa: F401
from data_pipeline.storage import city_location_db as _city_location_db  # noqa: F401
from data_pipeline.storage import cost_db as _cost_db  # noqa: F401
from data_pipeline.storage import db as _policy_db  # noqa: F401
from data_pipeline.storage import poverty_db as _poverty_db  # noqa: F401
from data_pipeline.storage import weather_radiation_db as _weather_radiation_db  # noqa: F401
from data_pipeline.core.context import RunContext
from data_pipeline.core.logging import configure_logging
from data_pipeline.db.records import WeatherRadiationRecord
from data_pipeline.db.session import get_engine
from data_pipeline.registry.processors import get_processor
from data_pipeline.registry.storages import get_storage
from data_pipeline.spiders.city_location_reference import CityLocationRawItem
from data_pipeline.spiders.county_region_reference import CountyRegionRawItem
from data_pipeline.spiders.policy_tariff_reference import PolicyTariffRawItem
from data_pipeline.spiders.pv_costs import CostRawItem

ROOT_DIR = Path(__file__).resolve().parents[2]
SEED_ROOT = ROOT_DIR / 'data_pipeline' / 'seeds'


@dataclass(frozen=True, slots=True)
class DatasetSpec:
    name: str
    spider: str
    site: str
    data_type: str
    default_paths: tuple[Path, ...]
    raw_loader: Callable[[list[dict[str, Any]], Path], list[Any]]


def _default_paths(dataset: str) -> tuple[Path, ...]:
    return (
        SEED_ROOT / dataset / f'{dataset}_seed.json',
        SEED_ROOT / dataset / f'{dataset}_seed.csv',
    )


def _normalize_rows(payload: Any, *, source_path: Path) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        items = payload.get('items')
        if not isinstance(items, list):
            raise ValueError(f'{source_path} JSON must contain an items list')
        payload = items

    if not isinstance(payload, list):
        raise ValueError(f'{source_path} must resolve to a list of row objects')

    rows: list[dict[str, Any]] = []
    for idx, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f'{source_path} row #{idx} is not an object')
        rows.append({str(k).strip(): v for k, v in item.items()})
    return rows


def _load_rows_from_file(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == '.json':
        payload = json.loads(path.read_text(encoding='utf-8-sig'))
        return _normalize_rows(payload, source_path=path)

    if suffix == '.csv':
        with path.open('r', encoding='utf-8-sig', newline='') as fh:
            reader = csv.DictReader(fh)
            return [
                {str(k).strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items() if k is not None}
                for row in reader
            ]

    raise ValueError(f'unsupported seed file format: {path.suffix}')


def _pick_source_url(row: dict[str, Any], source_path: Path) -> str:
    raw = row.get('source_url') or row.get('url')
    text = str(raw).strip() if raw is not None else ''
    return text or source_path.as_uri()


def _opt_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return Decimal(text)


def _opt_int(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return int(text)


def _parse_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        raise ValueError('day is required for weather_radiation seeds')
    return datetime.strptime(text, '%Y-%m-%d').date()


def _load_city_location_rows(rows: list[dict[str, Any]], source_path: Path) -> list[CityLocationRawItem]:
    return [
        CityLocationRawItem(
            province=str(row.get('province') or '').strip(),
            city=str(row.get('city') or '').strip(),
            latitude=_opt_decimal(row.get('latitude')) or Decimal('0'),
            longitude=_opt_decimal(row.get('longitude')) or Decimal('0'),
            source=str(row.get('source') or 'city_location_seed').strip() or 'city_location_seed',
            source_url=_pick_source_url(row, source_path),
        )
        for row in rows
    ]


def _load_weather_rows(rows: list[dict[str, Any]], source_path: Path) -> list[WeatherRadiationRecord]:
    out: list[WeatherRadiationRecord] = []
    for row in rows:
        radiation = _opt_decimal(row.get('shortwave_radiation_sum_kwh_m2'))
        if radiation is None:
            raise ValueError(f'weather row missing shortwave_radiation_sum_kwh_m2: {row}')
        out.append(
            WeatherRadiationRecord(
                latitude=float(_opt_decimal(row.get('latitude')) or Decimal('0')),
                longitude=float(_opt_decimal(row.get('longitude')) or Decimal('0')),
                day=_parse_date(row.get('day')),
                shortwave_radiation_sum_kwh_m2=radiation,
                temperature_mean_c=_opt_decimal(row.get('temperature_mean_c')),
                precipitation_sum_mm=_opt_decimal(row.get('precipitation_sum_mm')),
                wind_speed_mean_m_s=_opt_decimal(row.get('wind_speed_mean_m_s')),
                annual_radiation_sum_kwh_m2=_opt_decimal(row.get('annual_radiation_sum_kwh_m2')),
                equivalent_hours_h=_opt_decimal(row.get('equivalent_hours_h')),
                source=str(row.get('source') or 'weather_seed').strip() or 'weather_seed',
                source_url=_pick_source_url(row, source_path),
            )
        )
    return out


def _load_policy_tariff_rows(rows: list[dict[str, Any]], source_path: Path) -> list[PolicyTariffRawItem]:
    out: list[PolicyTariffRawItem] = []
    for row in rows:
        price = _opt_decimal(row.get('benchmark_price_yuan_per_kwh') or row.get('price'))
        if price is None:
            raise ValueError(f'policy row missing benchmark_price_yuan_per_kwh: {row}')
        out.append(
            PolicyTariffRawItem(
                province=str(row.get('province') or '').strip(),
                benchmark_price_yuan_per_kwh=price,
                subsidy_yuan_per_kwh=_opt_decimal(row.get('subsidy_yuan_per_kwh') or row.get('subsidy')),
                policy_date=str(row.get('policy_date') or '').strip() or None,
                policy_type=str(row.get('policy_type') or '').strip() or None,
                source=str(row.get('source') or 'policy_tariff_seed').strip() or 'policy_tariff_seed',
                source_url=_pick_source_url(row, source_path),
            )
        )
    return out


def _load_county_rows(rows: list[dict[str, Any]], source_path: Path) -> list[CountyRegionRawItem]:
    return [
        CountyRegionRawItem(
            province=str(row.get('province') or '').strip(),
            city=str(row.get('city') or '').strip() or None,
            county=str(row.get('county') or '').strip(),
            population=_opt_int(row.get('population')),
            income_per_capita_yuan=_opt_decimal(row.get('income_per_capita_yuan')),
            energy_condition=str(row.get('energy_condition') or '').strip() or None,
            tags=str(row.get('tags') or '').strip() or None,
            adcode=str(row.get('adcode') or '').strip() or None,
            source=str(row.get('source') or 'poverty_county_seed').strip() or 'poverty_county_seed',
            source_url=_pick_source_url(row, source_path),
        )
        for row in rows
    ]


def _load_cost_rows(rows: list[dict[str, Any]], source_path: Path) -> list[CostRawItem]:
    return [
        CostRawItem(
            name=str(row.get('name') or '').strip(),
            category=str(row.get('category') or '').strip(),
            province=str(row.get('province') or '').strip() or None,
            unit_cost_yuan_per_kw=_opt_decimal(row.get('unit_cost_yuan_per_kw')),
            component_price_yuan_per_w=_opt_decimal(row.get('component_price_yuan_per_w')),
            effective_date=str(row.get('effective_date') or '').strip() or None,
            source=str(row.get('source') or 'cost_seed').strip() or 'cost_seed',
            source_url=_pick_source_url(row, source_path),
        )
        for row in rows
    ]


DATASETS: dict[str, DatasetSpec] = {
    'city_location': DatasetSpec(
        name='city_location',
        spider='city_location_reference',
        site='city_location_reference',
        data_type='city_location',
        default_paths=_default_paths('city_location'),
        raw_loader=_load_city_location_rows,
    ),
    'weather_radiation': DatasetSpec(
        name='weather_radiation',
        spider='open_meteo_radiation',
        site='weather_data',
        data_type='weather_radiation',
        default_paths=_default_paths('weather_radiation'),
        raw_loader=_load_weather_rows,
    ),
    'policy_tariff': DatasetSpec(
        name='policy_tariff',
        spider='policy_tariff_reference',
        site='policy_tariff_reference',
        data_type='policy',
        default_paths=_default_paths('policy_tariff'),
        raw_loader=_load_policy_tariff_rows,
    ),
    'poverty_county': DatasetSpec(
        name='poverty_county',
        spider='county_region_reference',
        site='county_region_reference',
        data_type='poverty_county',
        default_paths=_default_paths('poverty_county'),
        raw_loader=_load_county_rows,
    ),
    'cost': DatasetSpec(
        name='cost',
        spider='pv_costs',
        site='pv_costs',
        data_type='cost',
        default_paths=_default_paths('cost'),
        raw_loader=_load_cost_rows,
    ),
}


def _resolve_seed_file(spec: DatasetSpec, explicit_file: str | None) -> Path:
    if explicit_file:
        path = Path(explicit_file).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f'seed file not found: {path}')
        return path

    for path in spec.default_paths:
        if path.exists():
            return path

    options = ', '.join(str(p) for p in spec.default_paths)
    raise FileNotFoundError(f'no seed file found for dataset={spec.name}; expected one of: {options}')


async def _run_dataset(spec: DatasetSpec, *, file_path: str | None, dry_run: bool) -> tuple[str, int, int, str]:
    seed_file = _resolve_seed_file(spec, file_path)
    rows = _load_rows_from_file(seed_file)
    raw_items = spec.raw_loader(rows, seed_file)

    processor = get_processor(spec.spider)
    if processor is None:
        raise RuntimeError(f'processor not registered for spider={spec.spider}')

    storage = get_storage(spider=spec.spider, site=spec.site, data_type=spec.data_type)
    if storage is None:
        raise RuntimeError(
            f'storage not registered for spider={spec.spider} site={spec.site} data_type={spec.data_type}'
        )

    ctx = RunContext(
        spider=spec.spider,
        site=spec.site,
        stage='seed',
        url=seed_file.as_uri(),
        meta={'dataset': spec.name, 'seed_file': str(seed_file)},
    )

    processed_items = processor.process(raw_items, ctx.with_stage('process', url=seed_file.as_uri()))
    if dry_run:
        return spec.name, len(rows), len(processed_items), 'dry-run'

    result = await storage.store(processed_items, ctx.with_stage('store', url=seed_file.as_uri()))
    return spec.name, len(rows), result.stored, result.error or 'ok'


async def _dispose_engine() -> None:
    engine = get_engine()
    await engine.dispose()


def _expand_datasets(dataset_arg: str) -> Sequence[DatasetSpec]:
    if dataset_arg == 'all':
        return tuple(DATASETS[name] for name in DATASETS)
    try:
        return (DATASETS[dataset_arg],)
    except KeyError as exc:
        raise KeyError(f'unknown dataset={dataset_arg}; available={", ".join(DATASETS)}') from exc


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='python data_pipeline/tools/load_seed_data.py')
    parser.add_argument('--dataset', required=True, choices=tuple(DATASETS.keys()) + ('all',), help='seed dataset name')
    parser.add_argument('--file', help='optional seed file path; defaults to data_pipeline/seeds/<dataset>/<dataset>_seed.(json|csv)')
    parser.add_argument('--dry-run', action='store_true', help='parse/process only; do not write to database')
    args = parser.parse_args(argv)

    configure_logging('INFO')

    async def _run() -> int:
        specs = _expand_datasets(args.dataset)
        exit_code = 0
        for spec in specs:
            file_path = args.file if args.dataset != 'all' else None
            try:
                name, raw_count, stored_count, status = await _run_dataset(spec, file_path=file_path, dry_run=args.dry_run)
                print(f'[seed] dataset={name} raw_rows={raw_count} processed_or_stored={stored_count} status={status}')
                if status not in ('ok', 'dry-run'):
                    exit_code = 1
            except FileNotFoundError as exc:
                print(f'[seed] dataset={spec.name} skipped: {exc}')
                if args.dataset != 'all':
                    exit_code = 1
            except Exception as exc:
                print(f'[seed] dataset={spec.name} failed: {type(exc).__name__}: {exc}')
                exit_code = 1
        if not args.dry_run:
            await _dispose_engine()
        return exit_code

    return asyncio.run(_run())


if __name__ == '__main__':
    raise SystemExit(main())
