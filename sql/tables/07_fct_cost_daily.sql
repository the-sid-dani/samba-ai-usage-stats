-- Daily cost fact table for financial reporting

CREATE TABLE IF NOT EXISTS `${project_id}.${dataset}.fct_cost_daily` (
  -- Time dimension
  cost_date DATE NOT NULL,

  -- Platform and user dimensions
  platform STRING NOT NULL,
  user_email STRING NOT NULL,
  user_id STRING,
  api_key_id STRING,

  -- Model and workspace context
  model STRING,
  workspace_id STRING,

  -- Cost metrics (USD)
  cost_usd FLOAT64 DEFAULT 0.0,
  cost_type STRING, -- 'input_tokens', 'output_tokens', 'subscription', 'usage_based'

  -- Volume for cost per unit calculations
  volume_units INT64 DEFAULT 0, -- tokens, requests, etc.
  unit_type STRING, -- 'tokens', 'requests', 'sessions'

  -- Metadata
  ingest_date DATE NOT NULL,
  created_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  request_id STRING
)
PARTITION BY cost_date
CLUSTER BY platform, user_email, model
OPTIONS (
  description = "Daily cost facts for financial reporting and ROI analysis",
  require_partition_filter = true
);