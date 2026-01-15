# Intent-Level Market Model MVP

This MVP detects early organizational intent by tracking semantic drift and hiring signal changes in job posts. It persists all signals, embeddings, and intent hypotheses in Postgres with pgvector, and exposes a FastAPI API to query intents and evidence.

## Run with Docker Compose

```bash
cp .env.example .env
docker-compose up --build
```

The API will be available at `http://localhost:8000`.

The demo frontend is available at `http://localhost:8000/`.

Note: multi-tenant support adds new tables/columns. If you already have a Postgres volume from before this change, reset it with `docker compose down -v`.

## Public repo checklist

- Do not commit `.env` (use `.env.example`).
- Keep mock fixtures only; add real outcomes via private data stores.

## Create a tenant and company

```bash
curl -X POST http://localhost:8000/tenants \
  -H "Content-Type: application/json" \
  -d '{"name": "Demo Workspace"}'

curl -X POST http://localhost:8000/tenants/1/companies/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Acme AI", "domain": "acme-ai.com"}'
```

## Ingest mock signals

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

## Query latest intents

```bash
curl http://localhost:8000/tenants/1/companies/1/intents/latest
```

Filter intents by type or confidence:

```bash
curl "http://localhost:8000/tenants/1/companies/1/intents/latest?intent_type=IPO_PREP,PLATFORM_PIVOT&min_confidence=0.7&limit=5"
```

## Intent dashboard

```bash
curl http://localhost:8000/tenants/1/companies/1/intents/dashboard
```

## Intent timeline

```bash
curl http://localhost:8000/tenants/1/companies/1/intents/timeline
```

## Outcomes + backtest

```bash
curl -X POST http://localhost:8000/tenants/1/companies/1/outcomes \
  -H "Content-Type: application/json" \
  -d '{"outcome_type":"IPO","timestamp":"2025-01-15T00:00:00Z","source":"mock"}'

curl -X POST http://localhost:8000/tenants/1/companies/1/backtest/run?lookback_days=365
curl http://localhost:8000/tenants/1/companies/1/backtest/report
```

## Intent graph (stub)

```bash
curl -X POST http://localhost:8000/graph/nodes \\
  -H "Content-Type: application/json" \\
  -d '{\"company_id\":1,\"node_type\":\"intent\",\"label\":\"IPO_PREP\"}'

curl -X POST http://localhost:8000/graph/edges \\
  -H "Content-Type: application/json" \\
  -d '{\"src_node_id\":1,\"dst_node_id\":2,\"relation_type\":\"precedes\",\"weight\":0.7}'

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

## Semantic drift (3 lines)

Semantic drift compares new job post text to a company’s recent baseline.
It uses embedding cosine similarity plus keyword and tech stack shifts.
Large deviations indicate intent changes before outcomes surface.

## Known limitations

- Only the mock fixture connector is fully implemented.
- Rule-based inference is minimal and not tuned with outcomes.
- Scheduler is a simple in-process loop (no retries or distributed coordination).

## Next steps

- Add more real connectors and richer role-level metadata.
- Train intent scorers on historical outcomes.
- Add alerting and caching for translated summaries.

## Scheduler (optional)

Set `ENABLE_SCHEDULER=true` in `.env` to run the pipeline on a fixed interval (default 24 hours).
