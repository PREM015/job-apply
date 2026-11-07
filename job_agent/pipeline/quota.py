"""Quota selection: all inputs are passed in; no I/O."""
from __future__ import annotations


def select_quota(candidates: list[dict], prefs: dict, applied_keys: set[str] | None = None,
                 suppressed: set[str] | None = None) -> list[dict]:
    applied_keys = applied_keys or set()
    suppressed = suppressed or set()
    quotas = prefs["quotas"]
    total_cap = int(quotas["total_per_day"])
    per_tier = {str(k): int(v) for k, v in quotas["per_tier"].items()}
    per_company = int(quotas["per_company"])
    tier_counts: dict[str, int] = {}
    company_counts: dict[str, int] = {}
    selected: list[dict] = []
    ranked = sorted(
        candidates,
        key=lambda job: (
            -int(job.get("score_total", 0)),
            str(job.get("tier", "9")),
            -int(job.get("recency_rank", 0)),
            str(job.get("company_name", "")).lower(),
        ),
    )
    for job in ranked:
        if len(selected) >= total_cap:
            break
        if job.get("already_applied") or job.get("suppressed"):
            continue
        if job.get("canonical_url") in applied_keys or job.get("fingerprint") in applied_keys:
            continue
        if job.get("company_name") in suppressed:
            continue
        tier = str(job.get("tier", "")).lower().replace("tier", "").strip()
        if tier and tier_counts.get(tier, 0) >= per_tier.get(tier, total_cap):
            continue
        company = str(job.get("company_name", "")).lower()
        if company_counts.get(company, 0) >= per_company:
            continue
        selected.append(job)
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
        company_counts[company] = company_counts.get(company, 0) + 1
    return selected
