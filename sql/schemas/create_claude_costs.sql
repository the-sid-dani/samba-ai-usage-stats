-- Table 1: claude_costs (Primary Financial Source)
-- Purpose: Single source of truth for ALL Claude organization costs
-- Source API: GET /v1/organizations/cost_report

CREATE TABLE IF NOT EXISTS `ai_usage_analytics.claude_costs` (
  activity_date DATE NOT NULL,
  organization_id STRING NOT NULL,
  workspace_id STRING,                     -- NULL="Default", non-NULL="Claude Code"
  model STRING NOT NULL,
  token_type STRING NOT NULL,
  cost_type STRING NOT NULL,
  amount_usd NUMERIC(10,4) NOT NULL,       -- DIVIDED by 100 from API response (cents -> dollars)
  currency STRING NOT NULL,
  description STRING,
  service_tier STRING,
  context_window STRING,
  ingestion_timestamp TIMESTAMP NOT NULL
)
PARTITION BY activity_date
CLUSTER BY workspace_id, model, token_type
OPTIONS(
  description="Primary financial data for all Claude costs. Source: /cost_report API. Contains API + Workbench + Claude Code costs.",
  labels=[("source", "claude_admin_api"), ("table_type", "financial")]
);
