from __future__ import annotations

import pytest

from job_agent.pipeline.classify import (classify_job, country_eligibility, experience_level,
                                         extract_skills, is_excluded_title, software_classification,
                                         work_mode)
from job_agent.pipeline.validate import validate_job, validate_jobs


@pytest.mark.parametrize("title,expected", [
    ("Software Engineer", True),
    ("Backend Developer", True),
    ("Data Engineer", True),
    ("Frontend Engineer", True),
    ("Accountant", False),
    ("Civil Engineer", False),
    ("Sales Engineer", False),
    ("Marketing Manager", False),
])
def test_software_classification(title, expected):
    is_software, evidence = software_classification(title, "")
    assert is_software is expected
    assert (evidence != []) is expected


def test_excluded_titles():
    assert is_excluded_title("Senior Software Engineer") is True
    assert is_excluded_title("Software Engineer") is False


@pytest.mark.parametrize("text,expected", [
    ("Fresher", "fresher"),
    ("0-1 years", "0-1"),
    ("1-2 years experience", "1-2"),
    ("2-3 years", "2-3"),
    ("5+ years", "3plus"),
    ("Internship", "internship"),
    ("", "unknown"),
])
def test_experience_level(text, expected):
    assert experience_level("Engineer", text) == expected


def test_work_mode():
    assert work_mode("Remote") == "remote"
    assert work_mode("Hybrid - Bengaluru") == "hybrid"
    assert work_mode("onsite") == "onsite"
    assert work_mode("Bengaluru") == "unknown"


def test_country_eligibility():
    assert country_eligibility("Bengaluru, India", "", {"IN"}) == ("IN", True)
    assert country_eligibility("New York, USA", "", {"IN"}) == ("US", False)
    assert country_eligibility("Somewhere", "", {"IN"}) == ("unknown", True)


def test_extract_skills_word_boundaries_and_aliases():
    text = "We use Python, C++, C#, .NET, Node.js, React and JavaScript."
    result = extract_skills(text, ["python", "c++", "c#", ".net", "node.js", "react", "java"],
                            ["javascript", "docker"])
    assert "python" in result["required"]
    assert "c++" in result["required"]
    assert "c#" in result["required"]
    assert ".net" in result["required"]
    assert "node.js" in result["required"]
    assert "react" in result["required"]
    assert "java" not in result["required"]
    assert "javascript" in result["preferred"]


def test_classify_job_enriches():
    job = {"title": "Software Engineer", "description_text": "Python and React. Fresher. Bengaluru, India.",
           "location_raw": "Bengaluru, India", "employment_type": "full_time"}
    prefs = {
        "skills": {"required": ["python", "react"], "preferred": ["docker"], "aliases": {}},
        "locations": {"countries": ["IN"]},
    }
    classify_job(job, prefs)
    assert job["is_software"] == 1
    assert job["experience_level"] == "fresher"
    assert job["country"] == "IN"
    assert job["country_eligible"] is True
    assert job["skills_required"] == ["python", "react"]


def test_validate_job_reasons():
    from tests.support import make_job

    ok, reason = validate_job(make_job())
    assert ok and reason is None
    assert validate_job(make_job(title="")) == (False, "missing_title")
    assert validate_job(make_job(company_name="")) == (False, "missing_company")
    assert validate_job(make_job(canonical_url="not-a-url")) == (False, "malformed_url")
    assert validate_job(make_job(posted_at="bad")) == (False, "malformed_date")


def test_validate_jobs_rejects_duplicate_source_id():
    from tests.support import make_job

    accepted, rejected = validate_jobs([make_job(), make_job(canonical_url="https://x.example.com/2")])
    assert len(accepted) == 1
    assert rejected[0]["reason"] == "duplicate_source_id"
