from __future__ import annotations

from job_agent.pipeline.score import score_job


def test_score_is_bounded_and_explainable(prefs):
    job = {"title": "Software Engineer", "description_text": "Python and React. Bachelor degree. Fresher.",
           "location_raw": "Bengaluru, India", "country": "IN", "work_mode": "onsite",
           "experience_level": "fresher", "skills_required": ["python", "react"],
           "posted_at": "2026-11-06T10:00:00+00:00"}
    result = score_job(job, prefs, tier="Tier 1")
    assert 0 <= result.total <= 100
    assert set(result.breakdown) == {"role_title", "required_skills", "experience", "location",
                                     "education", "company_tier", "recency"}
    assert result.total == sum(result.breakdown.values())
    assert result.reasons


def test_score_deterministic(prefs):
    job = {"title": "Software Engineer", "description_text": "Python. Fresher.",
           "location_raw": "Pune", "country": "IN", "experience_level": "fresher",
           "skills_required": ["python"], "posted_at": "2026-11-06T00:00:00+00:00"}
    assert score_job(job, prefs, "Tier 2") == score_job(job, prefs, "Tier 2")


def test_unknown_job_scores_low(prefs):
    result = score_job({}, prefs, None)
    assert result.total == 0
