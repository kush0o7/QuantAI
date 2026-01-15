from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.config import get_settings

settings = get_settings()


def fetch_job_posts(company_domain: str) -> list[dict[str, Any]]:
    fixtures_path = Path(settings.fixtures_path)
    fixture_file = fixtures_path / f"{company_domain}.json"
    if not fixture_file.exists():
        return []
    return json.loads(fixture_file.read_text(encoding="utf-8"))
