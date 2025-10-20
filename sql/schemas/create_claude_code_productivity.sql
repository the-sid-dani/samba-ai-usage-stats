-- Table 3: claude_code_productivity (IDE Metrics ONLY)
-- Purpose: Developer productivity metrics WITHOUT costs (prevents double-counting)
-- Source API: GET /v1/organizations/usage_report/claude_code

-- CRITICAL: This table contains NO cost or token fields to prevent double-counting
-- All costs are in claude_costs table (workspace breakdown shows Claude Code costs)

CREATE TABLE IF NOT EXISTS `ai_usage_analytics.claude_code_productivity` (
  activity_date DATE NOT NULL,
  organization_id STRING NOT NULL,
  actor_type STRING NOT NULL,
  user_email STRING,
  api_key_name STRING,
  terminal_type STRING,
  customer_type STRING,

  -- Productivity metrics ONLY (NO costs or tokens)
  num_sessions INT64,
  lines_added INT64,
  lines_removed INT64,
  commits_by_claude_code INT64,
  pull_requests_by_claude_code INT64,
  edit_tool_accepted INT64,
  edit_tool_rejected INT64,
  multi_edit_tool_accepted INT64,
  multi_edit_tool_rejected INT64,
  write_tool_accepted INT64,
  write_tool_rejected INT64,
  notebook_edit_tool_accepted INT64,
  notebook_edit_tool_rejected INT64,

  -- Audit
  ingestion_timestamp TIMESTAMP NOT NULL
)
PARTITION BY activity_date
CLUSTER BY user_email, terminal_type
OPTIONS(
  description="Claude Code IDE productivity metrics ONLY. NO costs (already in claude_costs table). Source: /usage_report/claude_code API.",
  labels=[("source", "claude_admin_api"), ("table_type", "productivity")]
);
