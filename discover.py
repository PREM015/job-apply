#!/usr/bin/env python3
"""Discovery module – real HTTP fetching + BeautifulSoup parsing.

- Uses the ``requests`` library with timeout, retry, user‑agent.
- Honours ``robots.txt`` when possible (simple check).
- Parses HTML with ``beautifulsoup4``.
- Returns a list of job dicts (or empty list on failure).
- Logs failures instead of silently treating them as successful discovery.
"""

import re
import time
import logging
from typing import List, Dict, Any

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Configuration (tweak as needed)
# ---------------------------------------------------------------------------
USER_AGENT = (
    "JobAgent/1.0 (+https://github.com/your-repo/job-agent); "
    "compatible with Python-Requests"
)
MAX_RETRIES = 3
BASE_TIMEOUT = 15  # seconds
RESPECT_ROBOTS_TXT = True  # set False to ignore (not recommended)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("discovery")
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _simple_robots_allow(url: str) -> bool:
    """Very small robots.txt check – only for the same host.

    Returns ``True`` if we can reasonably assume we are allowed,
    ``False`` if the robots.txt explicitly disallows.
    """
    from urllib.robotparser import RobotFileParser
    parsed = requests.utils.urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.fetch()
        return rp.can_fetch(USER_AGENT, url)
    except Exception as e:
        logger.warning("robots.txt fetch failed for %s: %s", url, e)
        return True  # be permissive on error


# ---------------------------------------------------------------------------
# HTTP fetching
# ---------------------------------------------------------------------------
def fetch_html(url: str, max_retries: int = MAX_RETRIES, timeout: int = BASE_TIMEOUT) -> str:
    """Fetch *url* and return the raw HTML text.

    - Retries up to *max_retries* on network errors / non‑200 status.
    - Uses a descriptive User‑Agent.
    - Respects ``robots.txt`` when ``RESPECT_ROBOTS_TXT`` is ``True``.
    - Logs every failure and finally returns ``""`` (empty string) so the
      caller can decide what to do.
    """
    if RESPECT_ROBOTS_TXT and not _simple_robots_allow(url):
        logger.info("robots.txt disallows fetching %s", url)
        return ""

    headers = {"User-Agent": USER_AGENT}
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, timeout=timeout, headers=headers)
            if resp.status_code == 200:
                return resp.text
            else:
                logger.warning(
                    "HTTP %s fetching %s (attempt %d/%d)", resp.status_code, url, attempt, max_retries
                )
        except requests.RequestException as exc:
            logger.warning(
                "Request error fetching %s (attempt %d/%d): %s", url, attempt, max_retries, exc
            )
        time.sleep(2 * attempt)  # back‑off
    return ""


# ---------------------------------------------------------------------------
# HTML parsing – job extraction
# ---------------------------------------------------------------------------
def _normalize_text(s: str) -> str:
    """Lower‑case, strip, collapse whitespace."""
    return " ".join(s.lower().split())


def _is_relative_url(url: str) -> bool:
    return url.startswith("/") and not url.startswith("//")


def _absolute_url(base: str, maybe_relative: str) -> str:
    """Turn a possibly‑relative URL into an absolute one."""
    from urllib.parse import urljoin
    return urljoin(base, maybe_relative)


def extract_jobs_from_html(html: str, company: str) -> List[Dict[str, Any]]:
    """Parse *html* and return a list of job dicts.

    Each dict contains at least: ``title``, ``link``, ``location`` (when found),
    and a short ``snippet`` of the description.
    """
    soup = BeautifulSoup(html, "html.parser")
    jobs = []

    # -----------------------------------------------------------------------
    # Heuristic 1: <a> tags whose href contains the word "job" (anywhere) or
    # "career" or "position".  We also require the visible text to be at least
    # 5 characters long.
    # -----------------------------------------------------------------------
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)

        if not text or len(text) < 5:
            continue

        # Normalise href
        if _is_relative_url(href):
            full_url = _absolute_url("https://example.com", href)
        else:
            full_url = href

        # Discard obvious placeholders
        if "example.com" in full_url.lower():
            continue
        if "placeholder" in full_url.lower():
            continue

        # Keep links that mention "job", "career", or "position" (case‑insensitive)
        lower = full_url.lower()
        if not any(kw in lower for kw in ("job", "career", "position")):
            # If the title itself looks like a role (contains at least two alpha words >2 chars)
            title_words = [w for w in text.split() if w.isalpha() and len(w) > 2]
            if len(title_words) < 2:
                continue

        # The company name must appear somewhere on the page – cheap check
        if company.lower() not in soup.get_text().lower():
            continue

        # Build a minimal job record
        job = {
            "title": text,
            "link": full_url,
            "source": "careers_page",
            "company": company,
            "snippet": "",  # will be filled later if needed
        }

        # Try to extract a location if the text contains a city / region pattern
        loc_match = re.search(r"[A-Za-z\s]+,\s*[A-Za-z\s]+", text)
        if loc_match:
            job["location"] = loc_match.group(0).strip()

        jobs.append(job)

    # -----------------------------------------------------------------------
    # Heuristic 2: look for <h2>/<h3> headings that often hold job titles on
    # career pages.  Keep them if not already captured.
    # -----------------------------------------------------------------------
    for hs in soup.find_all(["h2", "h3"]):
        text = hs.get_text(strip=True)
        if not text or len(text) < 5:
            continue
        # Avoid duplicates
        already = any(j["title"] == text for j in jobs)
        if already:
            continue
        if company.lower() not in soup.get_text().lower():
            continue
        job = {
            "title": text,
            "link": "",  # no direct link from heading; will be filled later if needed
            "source": "careers_page",
            "company": company,
            "snippet": "",
        }
        # Try to find a nearby <a> for a link
        nearby = hs.find_next_sibling("a") or hs.find_parent("a")
        if nearby and nearby.get("href"):
            job["link"] = nearby["href"]
        jobs.append(job)

    # -----------------------------------------------------------------------
    # Heuristic 3: Google‑specific – look for links whose href matches the
    # pattern /about/careers/applications/jobs/results/....  This captures the
    # actual job‑posting URLs we observed earlier.
    # -----------------------------------------------------------------------
    if "google" in company.lower():
        for a in soup.find_all("a", href=True):
            href = a["href"]
            # Normalise
            if _is_relative_url(href):
                full_url = _absolute_url("https://example.com", href)
            else:
                full_url = href
            # Pattern match
            if re.search(r"/about/careers/applications/jobs/results/[^\s']+", full_url):
                text = a.get_text(strip=True)
                if not text or len(text) < 5:
                    text = re.sub(r"/jobs/results/[0-9]+-[a-z-]+", "", full_url).strip() or "Google Job"
                job = {
                    "title": text,
                    "link": full_url,
                    "source": "careers_page",
                    "company": company,
                    "snippet": "",
                }
                # Avoid duplicates
                if not any(j["title"] == job["title"] for j in jobs):
                    jobs.append(job)

    # -----------------------------------------------------------------------
    # Deduplicate by title (case‑insensitive) – keep first occurrence
    # -----------------------------------------------------------------------
    seen = set()
    unique_jobs = []
    for j in jobs:
        key = j["title"].lower()
        if key in seen:
            continue
        seen.add(key)
        unique_jobs.append(j)
    return unique_jobs


# ---------------------------------------------------------------------------
# Main discovery function – used by the job agent
# ---------------------------------------------------------------------------
def real_discover_jobs(comp: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Discover jobs for a single company entry.

    ``comp`` is expected to have a key ``"careers_page"`` whose value is the
    absolute URL of the company's careers board.  If the key is missing or the
    fetch fails we return an empty list – **no phantom jobs are created**.

    The function:
    1. validates the URL,
    2. fetches the page (with retries, timeout, user‑agent),
    3. respects robots.txt,
    3. parses the HTML with BeautifulSoup,
    4. extracts candidate job links,
    5. returns a list of dicts (title, link, source, company, optional location).
    """
    careers_url = comp.get("careers_page")
    if not careers_url:
        logger.info("No careers_page URL for company %s", comp.get("company_name"))
        return []

    # robots.txt already checked inside fetch_html, but we log here
    logger.info("Fetching careers page %s (company: %s)", careers_url, comp.get("company_name"))

    html = fetch_html(careers_url)
    if not html:
        logger.error("Empty HTML fetched for %s", careers_url)
        return []

    company_name = comp.get("company_name", "Unknown")
    jobs = extract_jobs_from_html(html, company_name)
    logger.info("Extracted %d job(s) from %s", len(jobs), careers_url)
    return jobs


# ---------------------------------------------------------------------------
# Export for the main agent
# ---------------------------------------------------------------------------
# The main.py imports ``real_discover_jobs`` from this module.
# ---------------------------------------------------------------------------