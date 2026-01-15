from __future__ import annotations

from typing import Any

from data.connectors.job_posts import greenhouse, lever, mock_source

CONNECTORS = {
    "mock": mock_source.fetch_job_posts,
    "greenhouse": greenhouse.fetch_job_posts,
    "lever": lever.fetch_job_posts,
}


def fetch_posts(company_domain: str, source: str) -> list[dict[str, Any]]:
    connector = CONNECTORS.get(source)
    if not connector:
        raise ValueError(f"Unknown source: {source}")
    return connector(company_domain)
