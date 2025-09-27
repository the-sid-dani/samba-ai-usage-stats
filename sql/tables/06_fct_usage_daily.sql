-- Daily usage fact table - normalized across all platforms

CREATE TABLE IF NOT EXISTS `${project_id}.${dataset}.fct_usage_daily` (
  -- Time dimension
  usage_date DATE NOT NULL,

  -- Platform and user dimensions
  platform STRING NOT NULL, -- 'cursor', 'anthropic_api', 'anthropic_code', 'anthropic_web'
  user_email STRING NOT NULL,
  user_id STRING,
  api_key_id STRING,

  -- Model and workspace context
  model STRING,
  workspace_id STRING,

  -- Normalized usage metrics
  input_tokens INT64 DEFAULT 0,
  output_tokens INT64 DEFAULT 0,
  cached_input_tokens INT64 DEFAULT 0,
  cache_read_tokens INT64 DEFAULT 0,

  -- Platform-specific metrics
  sessions INT64 DEFAULT 0,
  lines_of_code_added INT64 DEFAULT 0,
  lines_of_code_accepted INT64 DEFAULT 0,
  acceptance_rate FLOAT64, -- Calculated: accepted/added
  total_accepts INT64 DEFAULT 0,

  -- Request tracking
  subscription_requests INT64 DEFAULT 0,
  usage_based_requests INT64 DEFAULT 0,

  -- Metadata
  ingest_date DATE NOT NULL,
  created_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  request_id STRING
)
PARTITION BY usage_date
CLUSTER BY platform, user_email, model
OPTIONS (
  description = "Daily usage facts normalized across all AI platforms",
  require_partition_filter = true
);