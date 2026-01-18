from __future__ import annotations

import json
import logging
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


logger = logging.getLogger(__name__)


def fetch_job_posts(company_domain: str) -> list[dict[str, Any]]:
    board = _resolve_board_slug(company_domain)
    if not board:
        return []
    url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"
    payload = _fetch_json(url)
    if not payload:
        return []
    jobs = payload.get("jobs", [])
    results: list[dict[str, Any]] = []
    for job in jobs:
        department = _pick_department(job.get("departments", []))
        location = _pick_location(job.get("location"))
        results.append(
            {
                "id": job.get("id"),
                "title": job.get("title"),
                "location": location,
                "team": department,
                "posted_at": job.get("updated_at") or job.get("created_at"),
                "url": job.get("absolute_url"),
                "employment_type": _pick_metadata(job.get("metadata", []), "Employment Type"),
                "seniority": _pick_metadata(job.get("metadata", []), "Seniority"),
                "source": "greenhouse",
            }
        )
    return results


def _resolve_board_slug(company_domain: str) -> str | None:
    domain = _normalize_domain(company_domain)
    mapping = _load_board_map()
    if domain in mapping:
        return mapping[domain]
    if "." in domain:
        return domain.split(".")[0]
    return domain or None


def _normalize_domain(value: str) -> str:
    cleaned = value.strip().lower()
    cleaned = cleaned.removeprefix("https://").removeprefix("http://")
    cleaned = cleaned.split("/")[0]
    return cleaned


def _load_board_map() -> dict[str, str]:
    raw = os.environ.get("GREENHOUSE_BOARD_MAP", "{}")
    try:
        mapping_raw = json.loads(raw)
    except json.JSONDecodeError:
        mapping_raw = {}
    if isinstance(mapping_raw, dict):
        return {str(key).lower(): str(value).lower() for key, value in mapping_raw.items()}
    return {}


def _fetch_json(url: str) -> dict[str, Any] | None:
    request = Request(url, headers={"User-Agent": "intent-market-model/0.1"})
    try:
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        logger.warning("Greenhouse fetch failed: %s", exc)
        return None


def _pick_department(departments: list[dict[str, Any]]) -> str | None:
    if not departments:
        return None
    return departments[0].get("name")


def _pick_location(location: dict[str, Any] | None) -> str | None:
    if not location:
        return None
    return location.get("name") or None


def _pick_metadata(items: list[dict[str, Any]], key: str) -> str | None:
    for item in items:
        if item.get("name") == key:
            return item.get("value")
    return None
