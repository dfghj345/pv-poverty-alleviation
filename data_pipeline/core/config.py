from __future__ import annotations

from data_pipeline.config.settings import pipeline_settings
from data_pipeline.config.sites import SITES, SiteConfig


def get_site(name: str) -> SiteConfig:
    try:
        return SITES[name]
    except KeyError as e:
        raise KeyError(f"unknown site config: {name}") from e


__all__ = ["pipeline_settings", "get_site", "SiteConfig"]

