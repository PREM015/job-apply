"""Adapter registry and config validation."""
from __future__ import annotations

from .ashby import AshbyAdapter
from .greenhouse import GreenhouseAdapter
from .jsonld import JsonLdAdapter
from .keka_zoho import KekaAdapter, ZohoAdapter
from .lever import LeverAdapter
from .sitemap import SitemapAdapter
from .smartrecruiters import SmartRecruitersAdapter
from .workable import WorkableAdapter

ADAPTERS = {
    "jsonld": JsonLdAdapter,
    "sitemap": SitemapAdapter,
    "greenhouse": GreenhouseAdapter,
    "lever": LeverAdapter,
    "ashby": AshbyAdapter,
    "smartrecruiters": SmartRecruitersAdapter,
    "workable": WorkableAdapter,
    "keka": KekaAdapter,
    "zoho": ZohoAdapter,
}


def get_adapter(source_type: str):
    try:
        return ADAPTERS[source_type]()
    except KeyError as exc:
        raise ValueError(f"unknown source type: {source_type}") from exc


def validate_source_config(sources: dict) -> None:
    for name, spec in sources.items():
        if name not in ADAPTERS:
            raise ValueError(f"unknown source in config: {name}")
        if not isinstance(spec, dict) or not isinstance(spec.get("enabled"), bool):
            raise ValueError(f"source {name} must have a boolean enabled flag")
