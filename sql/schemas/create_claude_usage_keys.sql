-- Table 2: claude_usage_keys (Per-Key Attribution)
-- Purpose: Token usage per API key (enables proportional cost allocation)
-- Source API: GET /v1/organizations/usage_report/messages

CREATE TABLE IF NOT EXISTS `ai_usage_analytics.claude_usage_keys` (
  activity_date DATE NOT NULL,
  organization_id STRING NOT NULL,
  api_key_id STRING NOT NULL,
  workspace_id STRING,
  model STRING NOT NULL,
  uncached_input_tokens INT64 NOT NULL,
  output_tokens INT64 NOT NULL,
  cache_read_input_tokens INT64 NOT NULL,
  cache_creation_5m_tokens INT64 NOT NULL,
  cache_creation_1h_tokens INT64 NOT NULL,
  web_search_requests INT64 NOT NULL,
  ingestion_timestamp TIMESTAMP NOT NULL
)
PARTITION BY activity_date
CLUSTER BY api_key_id, workspace_id, model
OPTIONS(
  description="Per-API-key token usage for cost attribution. Source: /usage_report/messages API. Contains token counts only, NO costs.",
  labels=[("source", "claude_admin_api"), ("table_type", "usage_attribution")]
);
