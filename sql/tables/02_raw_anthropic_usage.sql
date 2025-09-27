-- Raw Anthropic usage data table (for Phase 2)
-- Partitioned by ingest_date for cost optimization

CREATE TABLE IF NOT EXISTS `${project_id}.${dataset}.raw_anthropic_usage` (
  -- API identifiers
  api_key_id STRING NOT NULL,
  workspace_id STRING,

  -- Usage metrics
  model STRING,
  uncached_input_tokens INT64 DEFAULT 0,
  cached_input_tokens INT64 DEFAULT 0,
  cache_read_input_tokens INT64 DEFAULT 0,
  output_tokens INT64 DEFAULT 0,

  -- Time dimensions
  usage_date DATE NOT NULL,
  usage_hour INT64,

  -- Metadata
  ingest_date DATE NOT NULL,
  ingest_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  request_id STRING,

  -- Raw API response
  raw_response JSON
)
PARTITION BY ingest_date
CLUSTER BY api_key_id, model, usage_date
OPTIONS (
  description = "Raw Anthropic usage data from Admin API",
  require_partition_filter = true
);