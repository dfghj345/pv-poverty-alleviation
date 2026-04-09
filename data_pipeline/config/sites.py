from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, MutableMapping, Optional


@dataclass(frozen=True, slots=True)
class SiteConfig:
    name: str
    url: str
    headers: Mapping[str, str] = field(default_factory=dict)
    user_agent: Optional[str] = None
    timeout_s: float = 20.0
    retries: int = 2
    retry_base_delay_s: float = 0.5
    concurrency: int = 1
    cron: Optional[str] = None


SITES: MutableMapping[str, SiteConfig] = {
    "energy_gov": SiteConfig(
        name="energy_gov",
        url="https://www.nea.gov.cn/zcfb/",
        user_agent="Mozilla/5.0",
        timeout_s=30.0,
        retries=2,
        retry_base_delay_s=1.0,
        cron="0 2 * * *",
    ),
    "weather_data": SiteConfig(
        name="weather_data",
        url="https://archive-api.open-meteo.com/v1/archive",
        timeout_s=20.0,
        retries=2,
        retry_base_delay_s=0.5,
    ),
    "poverty_regions": SiteConfig(
        name="poverty_regions",
        url="https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json",
        timeout_s=20.0,
        retries=2,
        retry_base_delay_s=0.5,
    ),
    "pv_costs": SiteConfig(
        name="pv_costs",
        url="https://www.nea.gov.cn/",
        user_agent="Mozilla/5.0",
        timeout_s=20.0,
        retries=2,
        retry_base_delay_s=0.5,
    ),
    "pv_generation": SiteConfig(
        name="pv_generation",
        url="https://data.stats.gov.cn/",
        user_agent="Mozilla/5.0",
        timeout_s=20.0,
        retries=2,
        retry_base_delay_s=0.5,
    ),
    "city_location_reference": SiteConfig(
        name="city_location_reference",
        # Can be replaced with a maintained internal JSON source.
        url="https://example.com/pv/city_location_reference.json",
        timeout_s=15.0,
        retries=1,
        retry_base_delay_s=0.3,
    ),
    "policy_tariff_reference": SiteConfig(
        name="policy_tariff_reference",
        # Can be replaced with a maintained tariff dataset source.
        url="https://example.com/pv/policy_tariff_reference.json",
        timeout_s=15.0,
        retries=1,
        retry_base_delay_s=0.3,
    ),
    "county_region_reference": SiteConfig(
        name="county_region_reference",
        # Can be replaced with a maintained county dataset source.
        url="https://example.com/pv/county_region_reference.json",
        timeout_s=15.0,
        retries=1,
        retry_base_delay_s=0.3,
    ),
}
