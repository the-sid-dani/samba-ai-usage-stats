-- Raw Cursor usage data table
-- Partitioned by ingest_date, clustered by email and usage_date for optimal query performance

CREATE TABLE IF NOT EXISTS `${project_id}.${dataset}.raw_cursor_usage` (
  -- Primary identifiers
  email STRING NOT NULL,
  usage_date DATE NOT NULL,

  -- Usage metrics
  total_lines_added INT64 DEFAULT 0,
  accepted_lines_added INT64 DEFAULT 0,
  total_accepts INT64 DEFAULT 0,
  subscription_included_reqs INT64 DEFAULT 0,
  usage_based_reqs INT64 DEFAULT 0,

  -- Metadata
  ingest_date DATE NOT NULL,
  ingest_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  request_id STRING,

  -- Raw API response for debugging
  raw_response JSON
)
PARTITION BY ingest_date
CLUSTER BY email, usage_date
OPTIONS (
  description = "Raw Cursor usage data from Admin API",
  require_partition_filter = true
);