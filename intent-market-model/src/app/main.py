import logging
from pathlib import Path
import threading
import time

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.routes_companies import router as companies_router
from app.api.v1.routes_intents import router as intents_router
from app.api.v1.routes_outcomes import router as outcomes_router
from app.api.v1.routes_backtest import router as backtest_router
from app.api.v1.routes_timeline import router as timeline_router
from app.api.v1.routes_graph import router as graph_router
from app.api.v1.routes_pipeline import router as pipeline_router
from app.api.v1.routes_tenants import router as tenants_router
from core.config import get_settings
from core.logger import setup_logging
from data.storage.db import init_db, SessionLocal
from data.storage.repositories import company_repo, tenant_repo
from agents.orchestrator import Orchestrator


setup_logging()
app = FastAPI(title="Intent-Level Market Model MVP")
logger = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).parent / "frontend"


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    settings = get_settings()
    if settings.enable_scheduler:
        thread = threading.Thread(
            target=_scheduler_loop,
            args=(settings.scheduler_interval_hours, settings.scheduler_source),
            daemon=True,
        )
        thread.start()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


app.include_router(tenants_router, tags=["tenants"])
app.include_router(companies_router, prefix="/tenants/{tenant_id}/companies", tags=["companies"])
app.include_router(intents_router, prefix="/tenants/{tenant_id}/companies", tags=["intents"])
app.include_router(outcomes_router, tags=["outcomes"])
app.include_router(backtest_router, tags=["backtest"])
app.include_router(timeline_router, tags=["timeline"])
app.include_router(pipeline_router, tags=["pipeline"])
app.include_router(graph_router, tags=["graph"])
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def frontend():
    return FileResponse(STATIC_DIR / "index.html")


def _scheduler_loop(interval_hours: int, source: str) -> None:
    sleep_seconds = max(1, int(interval_hours * 3600))
    while True:
        try:
            with SessionLocal() as session:
                tenants = tenant_repo.list_tenants(session)
                orchestrator = Orchestrator(session)
                for tenant in tenants:
                    companies = company_repo.list_companies(session, tenant.id)
                    orchestrator.run(companies, source=source)
                logger.info("Scheduled pipeline run completed")
        except Exception as exc:
            logger.exception("Scheduled pipeline run failed: %s", exc)
        time.sleep(sleep_seconds)
