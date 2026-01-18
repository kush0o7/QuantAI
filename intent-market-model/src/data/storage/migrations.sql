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
  greenhouse_board VARCHAR(255),
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
  snippet TEXT,
  structured_fields JSONB DEFAULT '{}'::jsonb,
  diff JSONB DEFAULT '{}'::jsonb,
  vectorizer_version VARCHAR(50),
  tokens JSONB DEFAULT '[]'::jsonb,
  drift_score FLOAT,
  top_terms_delta JSONB DEFAULT '[]'::jsonb,
  role_bucket_delta JSONB DEFAULT '{}'::jsonb,
  tech_tag_delta JSONB DEFAULT '{}'::jsonb,
  event_hash VARCHAR(64) NOT NULL,
  embedding VECTOR(256),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE signal_events
  ADD COLUMN IF NOT EXISTS event_hash VARCHAR(64);

ALTER TABLE signal_events
  ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64);

UPDATE signal_events
  SET event_hash = content_hash
  WHERE event_hash IS NULL;

ALTER TABLE signal_events
  ADD COLUMN IF NOT EXISTS snippet TEXT;

ALTER TABLE signal_events
  ADD COLUMN IF NOT EXISTS vectorizer_version VARCHAR(50);

ALTER TABLE signal_events
  ADD COLUMN IF NOT EXISTS tokens JSONB DEFAULT '[]'::jsonb;

ALTER TABLE signal_events
  ADD COLUMN IF NOT EXISTS drift_score FLOAT;

ALTER TABLE signal_events
  ADD COLUMN IF NOT EXISTS top_terms_delta JSONB DEFAULT '[]'::jsonb;

ALTER TABLE signal_events
  ADD COLUMN IF NOT EXISTS role_bucket_delta JSONB DEFAULT '{}'::jsonb;

ALTER TABLE signal_events
  ADD COLUMN IF NOT EXISTS tech_tag_delta JSONB DEFAULT '{}'::jsonb;

DROP INDEX IF EXISTS idx_signal_events_hash;

CREATE UNIQUE INDEX IF NOT EXISTS idx_signal_events_hash
  ON signal_events (company_id, event_hash);

CREATE TABLE IF NOT EXISTS intent_hypotheses (
  id SERIAL PRIMARY KEY,
  tenant_id INTEGER NOT NULL REFERENCES tenants(id),
  company_id INTEGER NOT NULL REFERENCES companies(id),
  intent_type VARCHAR(100) NOT NULL,
  confidence FLOAT NOT NULL,
  readiness_score FLOAT,
  alert_eligible BOOLEAN DEFAULT FALSE,
  alert_reason TEXT,
  evidence JSONB DEFAULT '[]'::jsonb,
  rule_hits_json JSONB DEFAULT '[]'::jsonb,
  explanations_json JSONB DEFAULT '[]'::jsonb,
  explanation TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE companies
  ADD COLUMN IF NOT EXISTS greenhouse_board VARCHAR(255);

CREATE INDEX IF NOT EXISTS idx_intent_company_created
  ON intent_hypotheses (company_id, created_at DESC);

ALTER TABLE intent_hypotheses
  ADD COLUMN IF NOT EXISTS readiness_score FLOAT;

ALTER TABLE intent_hypotheses
  ADD COLUMN IF NOT EXISTS alert_eligible BOOLEAN DEFAULT FALSE;

ALTER TABLE intent_hypotheses
  ADD COLUMN IF NOT EXISTS alert_reason TEXT;

ALTER TABLE intent_hypotheses
  ADD COLUMN IF NOT EXISTS rule_hits_json JSONB DEFAULT '[]'::jsonb;

ALTER TABLE intent_hypotheses
  ADD COLUMN IF NOT EXISTS explanations_json JSONB DEFAULT '[]'::jsonb;

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

CREATE TABLE IF NOT EXISTS api_keys (
  id SERIAL PRIMARY KEY,
  tenant_id INTEGER NOT NULL REFERENCES tenants(id),
  name VARCHAR(255) NOT NULL,
  key_hash VARCHAR(64) NOT NULL,
  rate_limit_per_min INTEGER DEFAULT 60,
  last_used_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_api_keys_hash
  ON api_keys (key_hash);

CREATE TABLE IF NOT EXISTS rate_limits (
  id SERIAL PRIMARY KEY,
  api_key_id INTEGER NOT NULL REFERENCES api_keys(id),
  window_start TIMESTAMPTZ NOT NULL,
  count INTEGER DEFAULT 0
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_rate_limits_window
  ON rate_limits (api_key_id, window_start);

CREATE TABLE IF NOT EXISTS response_cache (
  id SERIAL PRIMARY KEY,
  cache_key VARCHAR(255) NOT NULL,
  payload JSONB DEFAULT '{}'::jsonb,
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_response_cache_key
  ON response_cache (cache_key);

CREATE TABLE IF NOT EXISTS audit_logs (
  id SERIAL PRIMARY KEY,
  api_key_id INTEGER REFERENCES api_keys(id),
  tenant_id INTEGER REFERENCES tenants(id),
  method VARCHAR(10) NOT NULL,
  path VARCHAR(255) NOT NULL,
  status_code INTEGER NOT NULL,
  duration_ms INTEGER NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
