-- Deploy New Two-Table Architecture Schema
-- Executes all DDL statements for Architecture v3.0
-- Run this script to create all new tables

-- Set dataset variables (update as needed)
DECLARE project_id STRING DEFAULT 'ai-workflows-459123';
DECLARE dataset STRING DEFAULT 'ai_usage_analytics';

-- Create enhanced user dimension table
CREATE TABLE IF NOT EXISTS `ai-workflows-459123.ai_usage_analytics.dim_users_enhanced` (
  user_sk INT64 NOT NULL,
  user_email STRING NOT NULL,
  first_name STRING,
  last_name STRING,
  full_name STRING,
  display_name STRING,
  department STRING,
  sub_department STRING,
  team STRING,
  job_level STRING,
  manager_email STRING,
  director_email STRING,
  ai_user_type STRING,
  primary_ai_tools ARRAY<STRING>,
  ai_budget_monthly_usd FLOAT64,
  is_active BOOLEAN DEFAULT true,
  start_date DATE,
  end_date DATE,
  created_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
CLUSTER BY department, team, user_email
OPTIONS (
  description = "Enhanced user dimension with organizational hierarchy"
);

-- Create date dimension table
CREATE TABLE IF NOT EXISTS `ai-workflows-459123.ai_usage_analytics.dim_date` (
  date_sk INT64 NOT NULL,
  calendar_date DATE NOT NULL,
  year_num INT64,
  quarter_num INT64,
  month_num INT64,
  month_name STRING,
  week_num INT64,
  day_of_week INT64,
  day_name STRING,
  is_weekend BOOLEAN,
  is_business_day BOOLEAN,
  is_holiday BOOLEAN,
  fiscal_year INT64,
  fiscal_quarter INT64,
  year_month_label STRING,
  quarter_label STRING,
  week_label STRING,
  business_days_in_month INT64,
  days_since_month_start INT64,
  days_until_month_end INT64
)
CLUSTER BY calendar_date
OPTIONS (
  description = "Time dimension optimized for Metabase filtering and fiscal reporting"
);

-- Create Cursor fact table
CREATE TABLE IF NOT EXISTS `ai-workflows-459123.ai_usage_analytics.fact_cursor_daily_usage` (
  event_id STRING NOT NULL,
  usage_date DATE NOT NULL,
  user_email STRING NOT NULL,
  total_lines_added INT64 DEFAULT 0,
  total_lines_deleted INT64 DEFAULT 0,
  accepted_lines_added INT64 DEFAULT 0,
  accepted_lines_deleted INT64 DEFAULT 0,
  net_lines_accepted INT64,
  total_applies INT64 DEFAULT 0,
  total_accepts INT64 DEFAULT 0,
  total_rejects INT64 DEFAULT 0,
  total_tabs_shown INT64 DEFAULT 0,
  total_tabs_accepted INT64 DEFAULT 0,
  composer_requests INT64 DEFAULT 0,
  chat_requests INT64 DEFAULT 0,
  agent_requests INT64 DEFAULT 0,
  cmdk_usages INT64 DEFAULT 0,
  subscription_included_reqs INT64 DEFAULT 0,
  usage_based_reqs INT64 DEFAULT 0,
  api_key_reqs INT64 DEFAULT 0,
  most_used_model STRING,
  client_version STRING,
  is_active BOOLEAN,
  line_acceptance_rate FLOAT64,
  tab_acceptance_rate FLOAT64,
  overall_acceptance_rate FLOAT64,
  productivity_velocity FLOAT64,
  estimated_subscription_cost FLOAT64,
  estimated_overage_cost FLOAT64,
  estimated_total_cost FLOAT64,
  attribution_confidence FLOAT64 DEFAULT 1.0,
  ingest_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  pipeline_run_id STRING
)
PARTITION BY usage_date
CLUSTER BY user_email, usage_date, is_active
OPTIONS (
  description = "Cursor coding assistant productivity and cost metrics",
  require_partition_filter = true
);

-- Create Claude fact table (comprehensive schema)
CREATE TABLE IF NOT EXISTS `ai-workflows-459123.ai_usage_analytics.fact_claude_daily_usage` (
  event_id STRING NOT NULL,
  usage_date DATE NOT NULL,
  platform STRING NOT NULL,
  user_email STRING,
  api_key_id STRING,
  workspace_id STRING,
  claude_code_sessions INT64 DEFAULT 0,
  claude_code_lines_added INT64 DEFAULT 0,
  claude_code_lines_removed INT64 DEFAULT 0,
  claude_code_net_lines INT64,
  claude_code_commits INT64 DEFAULT 0,
  claude_code_prs INT64 DEFAULT 0,
  edit_tool_accepted INT64 DEFAULT 0,
  edit_tool_rejected INT64 DEFAULT 0,
  multi_edit_tool_accepted INT64 DEFAULT 0,
  multi_edit_tool_rejected INT64 DEFAULT 0,
  write_tool_accepted INT64 DEFAULT 0,
  write_tool_rejected INT64 DEFAULT 0,
  notebook_edit_tool_accepted INT64 DEFAULT 0,
  notebook_edit_tool_rejected INT64 DEFAULT 0,
  uncached_input_tokens INT64 DEFAULT 0,
  cached_input_tokens INT64 DEFAULT 0,
  cache_read_input_tokens INT64 DEFAULT 0,
  cache_creation_1h_tokens INT64 DEFAULT 0,
  cache_creation_5m_tokens INT64 DEFAULT 0,
  output_tokens INT64 DEFAULT 0,
  web_search_requests INT64 DEFAULT 0,
  claude_ai_conversations INT64 DEFAULT 0,
  claude_ai_projects INT64 DEFAULT 0,
  claude_ai_files_uploaded INT64 DEFAULT 0,
  claude_ai_messages_sent INT64 DEFAULT 0,
  claude_ai_active_time_minutes INT64 DEFAULT 0,
  claude_code_cost_usd FLOAT64 DEFAULT 0,
  claude_api_cost_usd FLOAT64 DEFAULT 0,
  claude_ai_cost_usd FLOAT64 DEFAULT 0,
  total_cost_usd FLOAT64 DEFAULT 0,
  input_token_cost_usd FLOAT64 DEFAULT 0,
  output_token_cost_usd FLOAT64 DEFAULT 0,
  cache_read_cost_usd FLOAT64 DEFAULT 0,
  web_search_cost_usd FLOAT64 DEFAULT 0,
  subscription_cost_usd FLOAT64 DEFAULT 0,
  claude_code_total_tool_suggestions INT64,
  claude_code_total_tool_accepted INT64,
  claude_code_total_tool_rejected INT64,
  claude_code_acceptance_rate FLOAT64,
  claude_code_lines_per_session FLOAT64,
  claude_code_productivity_score FLOAT64,
  total_tokens INT64,
  tokens_per_session FLOAT64,
  cost_per_token FLOAT64,
  cost_per_interaction FLOAT64,
  claude_ai_engagement_score FLOAT64,
  claude_api_efficiency_ratio FLOAT64,
  model STRING,
  service_tier STRING,
  context_window STRING,
  actor_type STRING,
  platform_detection_method STRING,
  attribution_method STRING,
  attribution_confidence FLOAT64,
  data_source STRING,
  has_productivity_data BOOLEAN DEFAULT false,
  has_token_data BOOLEAN DEFAULT false,
  has_cost_data BOOLEAN DEFAULT false,
  data_completeness_score FLOAT64,
  ingest_date DATE NOT NULL,
  ingest_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  pipeline_run_id STRING,
  source_api_endpoint STRING,
  raw_response JSON
)
PARTITION BY usage_date
CLUSTER BY platform, user_email, api_key_id, usage_date
OPTIONS (
  description = "Comprehensive Claude ecosystem usage: claude_code productivity, claude_api tokens, claude_ai conversations",
  require_partition_filter = true
);

-- Platform detection computed column
ALTER TABLE `ai-workflows-459123.ai_usage_analytics.fact_claude_daily_usage`
ADD COLUMN IF NOT EXISTS platform_computed STRING AS (
  CASE
    WHEN workspace_id = 'wrkspc_01WtfAtqQsV3zBDs9RYpNZdR' THEN 'claude_code'
    WHEN data_source = 'claude_code_analytics' THEN 'claude_code'
    WHEN data_source = 'audit_logs' THEN 'claude_ai'
    WHEN api_key_id IS NOT NULL AND workspace_id != 'wrkspc_01WtfAtqQsV3zBDs9RYpNZdR' THEN 'claude_api'
    ELSE 'unknown'
  END
);