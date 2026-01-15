from __future__ import annotations

import typer

from agents.intent_inference.agent import IntentInferenceAgent
from agents.signal_harvester.agent import SignalHarvesterAgent
from agents.orchestrator import Orchestrator
from data.storage.db import SessionLocal
from data.storage.repositories import company_repo, signals_repo

app = typer.Typer(help="Intent-Level Market Model CLI")


@app.command()
def ingest(tenant_id: int, company_id: int, source: str = "mock") -> None:
    with SessionLocal() as session:
        company = company_repo.get_company(session, tenant_id, company_id)
        if not company:
            raise typer.Exit(code=1)
        harvester = SignalHarvesterAgent(session)
        inserted = harvester.harvest(company, source)
        typer.echo(f"Inserted {inserted} signals")


@app.command()
def infer(tenant_id: int, company_id: int) -> None:
    with SessionLocal() as session:
        signals = signals_repo.list_recent_signals(session, tenant_id, company_id, limit=50)
        agent = IntentInferenceAgent(session)
        intents = agent.infer(signals)
        typer.echo(f"Inserted {len(intents)} intents")


@app.command()
def pipeline(tenant_id: int, source: str = "mock") -> None:
    with SessionLocal() as session:
        companies = company_repo.list_companies(session, tenant_id)
        orchestrator = Orchestrator(session)
        results = orchestrator.run(companies, source=source)
        typer.echo(results)
