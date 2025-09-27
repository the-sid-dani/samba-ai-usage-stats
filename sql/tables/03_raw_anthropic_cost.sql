-- Raw Anthropic cost data table (for Phase 2)
-- Partitioned by ingest_date for cost reconciliation

CREATE TABLE IF NOT EXISTS `${project_id}.${dataset}.raw_anthropic_cost` (
  -- API identifiers
  api_key_id STRING NOT NULL,
  workspace_id STRING,

  -- Cost metrics
  model STRING,
  cost_usd FLOAT64 DEFAULT 0.0,
  cost_type STRING, -- e.g., 'input_tokens', 'output_tokens', 'cache_read'

  -- Time dimensions
  cost_date DATE NOT NULL,
  cost_hour INT64,

  -- Metadata
  ingest_date DATE NOT NULL,
  ingest_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  request_id STRING,

  -- Raw API response
  raw_response JSON
)
PARTITION BY ingest_date
CLUSTER BY api_key_id, model, cost_date
OPTIONS (
  description = "Raw Anthropic cost data from Admin API",
  require_partition_filter = true
);