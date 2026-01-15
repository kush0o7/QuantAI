CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS tenants (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS companies (
  id SERIAL PRIMARY KEY,
  tenant_id INTEGER NOT NULL REFERENCES tenants(id),
  name VARCHAR(255) NOT NULL,
  domain VARCHAR(255),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS signal_events (
  id SERIAL PRIMARY KEY,
  tenant_id INTEGER NOT NULL REFERENCES tenants(id),
  company_id INTEGER NOT NULL REFERENCES companies(id),
  source VARCHAR(100) NOT NULL,
  timestamp TIMESTAMPTZ NOT NULL,
  signal_type VARCHAR(100) NOT NULL,
  raw_text TEXT NOT NULL,
  raw_text_uri TEXT,
  structured_fields JSONB DEFAULT '{}'::jsonb,
  diff JSONB DEFAULT '{}'::jsonb,
  content_hash VARCHAR(64) NOT NULL,
  embedding VECTOR(256),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_signal_events_hash
  ON signal_events (company_id, content_hash);

CREATE TABLE IF NOT EXISTS intent_hypotheses (
  id SERIAL PRIMARY KEY,
  tenant_id INTEGER NOT NULL REFERENCES tenants(id),
  company_id INTEGER NOT NULL REFERENCES companies(id),
  intent_type VARCHAR(100) NOT NULL,
  confidence FLOAT NOT NULL,
  evidence JSONB DEFAULT '[]'::jsonb,
  explanation TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_intent_company_created
  ON intent_hypotheses (company_id, created_at DESC);

CREATE TABLE IF NOT EXISTS outcome_events (
  id SERIAL PRIMARY KEY,
  tenant_id INTEGER NOT NULL REFERENCES tenants(id),
  company_id INTEGER NOT NULL REFERENCES companies(id),
  outcome_type VARCHAR(100) NOT NULL,
  timestamp TIMESTAMPTZ NOT NULL,
  source VARCHAR(100) NOT NULL,
  details JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS intent_graph_nodes (
  id SERIAL PRIMARY KEY,
  company_id INTEGER REFERENCES companies(id),
  tenant_id INTEGER REFERENCES tenants(id),
  node_type VARCHAR(100) NOT NULL,
  label VARCHAR(255) NOT NULL,
  details JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS intent_graph_edges (
  id SERIAL PRIMARY KEY,
  src_node_id INTEGER NOT NULL REFERENCES intent_graph_nodes(id),
  dst_node_id INTEGER NOT NULL REFERENCES intent_graph_nodes(id),
  relation_type VARCHAR(100) NOT NULL,
  weight FLOAT DEFAULT 0.0,
  details JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS intent_backtest_results (
  id SERIAL PRIMARY KEY,
  tenant_id INTEGER NOT NULL REFERENCES tenants(id),
  company_id INTEGER NOT NULL REFERENCES companies(id),
  outcome_id INTEGER,
  outcome_type VARCHAR(100) NOT NULL,
  intent_id INTEGER,
  intent_type VARCHAR(100),
  outcome_timestamp TIMESTAMPTZ NOT NULL,
  intent_timestamp TIMESTAMPTZ,
  lag_days FLOAT,
  matched BOOLEAN DEFAULT FALSE,
  run_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
