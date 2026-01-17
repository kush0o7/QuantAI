# Intent-Level Market Model MVP

## Overview

This project is a working MVP for detecting early organizational intent by analyzing hiring signals and related text sources (job posts, SEC filings). It is designed as a pipeline that ingests signals, computes semantic drift and feature shifts, infers intent hypotheses, and persists everything in a queryable database with a simple API and demo UI. The goal is to surface directional changes (for example, IPO preparation or cost pressure) before outcomes are publicly visible.

The codebase is organized around a small set of agents that each own a piece of the pipeline. The default setup uses mock fixtures so the system can run without external integrations, but the architecture is built to accept real connectors.

## What it does

- Ingests job posting and filing data for a company (mock fixtures included).
- Normalizes and deduplicates raw signals into a consistent schema.
- Computes semantic drift using embedding similarity, keyword shift, and tech stack tag changes.
- Generates intent hypotheses using a rule-based scorer (LLM scorer hook is present but stubbed).
- Stores signals, embeddings, hypotheses, and outcomes in Postgres with pgvector.
- Exposes a FastAPI API for intents, timelines, dashboards, backtests, and a lightweight graph model.
- Offers a basic demo frontend and a CLI for running pipelines.

## Why it matters

Hiring signals are an early indicator of company behavior. When job descriptions shift in terms of compliance language, platform focus, or cost optimization, it can foreshadow IPO prep, product expansion, or restructuring. This MVP makes those shifts measurable and queryable so recruiters, investors, and analysts can see leading indicators instead of only lagging outcomes.

## Architecture and data flow

1. Data ingestion
   - Connectors fetch raw signals. `mock` is implemented with local fixtures. `greenhouse` and `lever` connectors are stubbed but ready to be wired.
   - SEC filings mock data is available under `data/fixtures/sec` and ingested via `sec_mock`.

2. Normalization
   - Raw items are normalized into `SignalEvent` records with consistent fields: timestamp, signal type, raw text, structured metadata.
   - Role buckets and tech tags are derived from text to support downstream scoring.

3. Semantic drift
   - Each new signal is embedded using a hashing vectorizer (no external model dependency).
   - Drift is computed against a company baseline: cosine similarity, keyword delta, and tech stack changes.

4. Intent inference
   - The rule scorer maps signal content to intent types (IPO prep, cost pressure, platform pivot, product expansion, etc.).
   - Intent hypotheses are deduped by signal and stored with confidence and explanation text.

5. Persistence and APIs
   - Signals, intents, outcomes, and backtest results live in Postgres.
   - FastAPI routes expose the pipeline, intent timelines, dashboards, and backtests.

6. Translation (decision support)
   - Intent hypotheses can be summarized into investor-facing or jobseeker-facing explanations.

## Core components

- Signal Harvester: fetches, normalizes, dedupes, computes drift, stores signals.
- Intent Inference: fuses rule-based scoring (optional LLM hook) into intent hypotheses.
- Decision Translator: turns intents into investor and jobseeker summaries.
- Causal Memory: stubbed placeholder for learning intent-outcome relationships.
- Backtest Service: measures how often intents preceded outcomes and by how many days.
- Graph API: stubbed graph nodes/edges for intent relationship exploration.

## Data model (high level)

- Tenant: workspace container.
- Company: entity being tracked.
- SignalEvent: a single signal with text, metadata, embedding, and drift diff.
- IntentHypothesis: inferred intent with confidence and evidence.
- OutcomeEvent: recorded business outcomes (IPO, funding, layoffs, etc.).
- IntentBacktestResult: match statistics between intents and outcomes.
- IntentGraphNode/Edge: lightweight graph representation (stub).

## Tech stack

- FastAPI for APIs and static demo UI
- SQLAlchemy ORM
- Postgres + pgvector (hashing embeddings stored as vectors)
- scikit-learn HashingVectorizer for embeddings
- Docker Compose for local setup

## Run with Docker Compose

```bash
cp .env.example .env
docker-compose up --build
```

The API will be available at `http://localhost:8000`.
The demo frontend is available at `http://localhost:8000/`.

Note: multi-tenant support adds new tables/columns. If you already have a Postgres volume from before this change, reset it with `docker compose down -v`.

## Quickstart workflow

Create a tenant and company:

```bash
curl -X POST http://localhost:8000/tenants \
  -H "Content-Type: application/json" \
  -d '{"name": "Demo Workspace"}'

curl -X POST http://localhost:8000/tenants/1/companies/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Acme AI", "domain": "acme-ai.com"}'
```

Ingest mock signals:

```bash
curl -X POST "http://localhost:8000/tenants/1/companies/ingest/1?source=mock"
```

Ingest mock SEC filings:

```bash
curl -X POST "http://localhost:8000/tenants/1/companies/ingest/1?source=sec_mock"
```

Skip inference during ingest:

```bash
curl -X POST "http://localhost:8000/tenants/1/companies/ingest/1?source=mock&infer=false"
```

Query latest intents:

```bash
curl http://localhost:8000/tenants/1/companies/1/intents/latest
```

Filter intents by type or confidence:

```bash
curl "http://localhost:8000/tenants/1/companies/1/intents/latest?intent_type=IPO_PREP,PLATFORM_PIVOT&min_confidence=0.7&limit=5"
```

Intent dashboard:

```bash
curl http://localhost:8000/tenants/1/companies/1/intents/dashboard
```

Intent timeline:

```bash
curl http://localhost:8000/tenants/1/companies/1/intents/timeline
```

## Outcomes and backtesting

```bash
curl -X POST http://localhost:8000/tenants/1/companies/1/outcomes \
  -H "Content-Type: application/json" \
  -d '{"outcome_type":"IPO","timestamp":"2025-01-15T00:00:00Z","source":"mock"}'

curl -X POST http://localhost:8000/tenants/1/companies/1/backtest/run?lookback_days=365
curl http://localhost:8000/tenants/1/companies/1/backtest/report
```

## Intent graph (stub)

```bash
curl -X POST http://localhost:8000/graph/nodes \
  -H "Content-Type: application/json" \
  -d '{"company_id":1,"node_type":"intent","label":"IPO_PREP"}'

curl -X POST http://localhost:8000/graph/edges \
  -H "Content-Type: application/json" \
  -d '{"src_node_id":1,"dst_node_id":2,"relation_type":"precedes","weight":0.7}'

curl http://localhost:8000/graph/nodes
curl http://localhost:8000/graph/edges
```

## Query recent signals

```bash
curl http://localhost:8000/tenants/1/companies/1/signals/recent
```

## CLI task runner

```bash
intent-cli ingest 1 1 --source mock
intent-cli infer 1 1
intent-cli pipeline 1 --source mock
```

## Run pipeline via API

```bash
curl -X POST "http://localhost:8000/tenants/1/pipeline/run?source=mock"
```

Run pipeline across multiple sources:

```bash
curl -X POST "http://localhost:8000/tenants/1/pipeline/run?source=mock,sec_mock"
```

Check scheduler status:

```bash
curl http://localhost:8000/pipeline/scheduler
```

## Semantic drift (short explanation)

Semantic drift compares new job post text to a company baseline using:
- embedding cosine similarity
- keyword shift deltas
- tech stack tag changes

Large deviations indicate intent changes before outcomes surface.

## Known limitations

- Only the mock fixture connector is fully implemented.
- LLM intent scoring and causal memory are present as stubs.
- Scheduler is a simple in-process loop (no retries or distributed coordination).

## Next steps

- Add real connectors for ATS and filings APIs.
- Train intent scorers on historical outcomes and improve confidence calibration.
- Implement alerting and caching for translated summaries.

## Scheduler (optional)

Set `ENABLE_SCHEDULER=true` in `.env` to run the pipeline on a fixed interval (default 24 hours).
