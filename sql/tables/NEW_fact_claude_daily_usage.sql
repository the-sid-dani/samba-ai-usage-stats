-- Updated Claude Daily Usage Table
-- Supports all Claude platforms: claude_code, claude_api, claude_ai
-- Based on confirmed API capabilities and real field verification

CREATE TABLE IF NOT EXISTS `${project_id}.${dataset}.fact_claude_daily_usage` (
  -- Primary identifiers
  event_id STRING NOT NULL,
  usage_date DATE NOT NULL,
  platform STRING NOT NULL,                -- claude_code, claude_api, claude_ai

  -- User attribution (varies by platform and data source)
  user_email STRING,                       -- Claude Code Analytics API, claude.ai audit logs
  api_key_id STRING,                       -- All APIs (when available)
  workspace_id STRING,                     -- Platform detection and grouping

  -- ✅ CLAUDE CODE PRODUCTIVITY METRICS (from Claude Code Analytics API)
  -- Core development metrics
  claude_code_sessions INT64 DEFAULT 0,    -- num_sessions
  claude_code_lines_added INT64 DEFAULT 0, -- lines_of_code.added
  claude_code_lines_removed INT64 DEFAULT 0, -- lines_of_code.removed
  claude_code_net_lines INT64,             -- COMPUTED: added - removed
  claude_code_commits INT64 DEFAULT 0,     -- commits_by_claude_code
  claude_code_prs INT64 DEFAULT 0,         -- pull_requests_by_claude_code

  -- Tool-specific acceptance metrics (Claude Code Analytics API)
  edit_tool_accepted INT64 DEFAULT 0,      -- tool_actions.edit_tool.accepted
  edit_tool_rejected INT64 DEFAULT 0,      -- tool_actions.edit_tool.rejected
  multi_edit_tool_accepted INT64 DEFAULT 0, -- tool_actions.multi_edit_tool.accepted
  multi_edit_tool_rejected INT64 DEFAULT 0, -- tool_actions.multi_edit_tool.rejected
  write_tool_accepted INT64 DEFAULT 0,     -- tool_actions.write_tool.accepted
  write_tool_rejected INT64 DEFAULT 0,     -- tool_actions.write_tool.rejected
  notebook_edit_tool_accepted INT64 DEFAULT 0, -- tool_actions.notebook_edit_tool.accepted
  notebook_edit_tool_rejected INT64 DEFAULT 0, -- tool_actions.notebook_edit_tool.rejected

  -- ✅ CLAUDE API TOKEN METRICS (from Messages Usage Report API)
  -- Token consumption (all Claude platforms)
  uncached_input_tokens INT64 DEFAULT 0,   -- uncached_input_tokens
  cached_input_tokens INT64 DEFAULT 0,     -- cached_input_tokens (cache hits)
  cache_read_input_tokens INT64 DEFAULT 0, -- cache_read_input_tokens
  cache_creation_1h_tokens INT64 DEFAULT 0, -- cache_creation.ephemeral_1h_input_tokens
  cache_creation_5m_tokens INT64 DEFAULT 0, -- cache_creation.ephemeral_5m_input_tokens
  output_tokens INT64 DEFAULT 0,           -- output_tokens

  -- Server tool usage
  web_search_requests INT64 DEFAULT 0,     -- server_tool_use.web_search_requests

  -- ✅ CLAUDE.AI KNOWLEDGE WORK METRICS (from Enterprise Audit Logs)
  claude_ai_conversations INT64 DEFAULT 0, -- Conversations created
  claude_ai_projects INT64 DEFAULT 0,      -- Projects created
  claude_ai_files_uploaded INT64 DEFAULT 0, -- Files uploaded for analysis
  claude_ai_messages_sent INT64 DEFAULT 0, -- Messages in conversations
  claude_ai_active_time_minutes INT64 DEFAULT 0, -- Estimated session time

  -- ✅ COST METRICS (from Cost Report API)
  -- Platform-specific costs
  claude_code_cost_usd FLOAT64 DEFAULT 0,  -- When platform = claude_code
  claude_api_cost_usd FLOAT64 DEFAULT 0,   -- When platform = claude_api
  claude_ai_cost_usd FLOAT64 DEFAULT 0,    -- When platform = claude_ai
  total_cost_usd FLOAT64 DEFAULT 0,        -- Total daily cost for this platform

  -- Cost breakdown by type
  input_token_cost_usd FLOAT64 DEFAULT 0,  -- cost_type = input_tokens
  output_token_cost_usd FLOAT64 DEFAULT 0, -- cost_type = output_tokens
  cache_read_cost_usd FLOAT64 DEFAULT 0,   -- cost_type = cache_read
  web_search_cost_usd FLOAT64 DEFAULT 0,   -- cost_type = web_search
  subscription_cost_usd FLOAT64 DEFAULT 0, -- Allocated subscription cost

  -- 📊 CALCULATED PRODUCTIVITY METRICS
  -- Claude Code specific calculations
  claude_code_total_tool_suggestions INT64, -- Sum of all tool suggestions
  claude_code_total_tool_accepted INT64,    -- Sum of all tool accepts
  claude_code_total_tool_rejected INT64,    -- Sum of all tool rejects
  claude_code_acceptance_rate FLOAT64,      -- accepted / (accepted + rejected)
  claude_code_lines_per_session FLOAT64,   -- net_lines / sessions
  claude_code_productivity_score FLOAT64,  -- Composite coding productivity

  -- Universal Claude metrics
  total_tokens INT64,                      -- Sum of all token types
  tokens_per_session FLOAT64,             -- total_tokens / sessions (when available)
  cost_per_token FLOAT64,                 -- total_cost / total_tokens
  cost_per_interaction FLOAT64,           -- total_cost / interactions

  -- Platform-specific efficiency scores
  claude_ai_engagement_score FLOAT64,     -- conversations + projects activity
  claude_api_efficiency_ratio FLOAT64,    -- output_tokens / input_tokens

  -- Context and metadata
  model STRING,                           -- claude-3-5-sonnet, claude-4, etc.
  service_tier STRING,                   -- standard, priority
  context_window STRING,                 -- 0-200k, 200k+
  actor_type STRING,                     -- user_actor, api_actor

  -- Platform detection and attribution
  platform_detection_method STRING,      -- workspace_id, api_key_mapping, audit_log
  attribution_method STRING,             -- direct_email, api_key_mapping, audit_log
  attribution_confidence FLOAT64,        -- 0.0 to 1.0
  data_source STRING,                    -- claude_code_analytics, usage_report, cost_report, audit_logs

  -- Data quality indicators
  has_productivity_data BOOLEAN DEFAULT false, -- Claude Code specific
  has_token_data BOOLEAN DEFAULT false,   -- API usage data available
  has_cost_data BOOLEAN DEFAULT false,    -- Cost data available
  data_completeness_score FLOAT64,       -- Overall data quality 0.0-1.0

  -- Audit and pipeline metadata
  ingest_date DATE NOT NULL,
  ingest_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  pipeline_run_id STRING,
  source_api_endpoint STRING,            -- Which API provided this data
  raw_response JSON                      -- Full API response for debugging
)
PARTITION BY usage_date
CLUSTER BY platform, user_email, api_key_id, usage_date
OPTIONS (
  description = "Comprehensive Claude ecosystem usage: claude_code productivity, claude_api tokens, claude_ai conversations",
  require_partition_filter = true
);

-- Add platform detection logic as computed column
ALTER TABLE `${project_id}.${dataset}.fact_claude_daily_usage`
ADD COLUMN IF NOT EXISTS platform_computed STRING AS (
  CASE
    WHEN workspace_id = 'wrkspc_01WtfAtqQsV3zBDs9RYpNZdR' THEN 'claude_code'
    WHEN data_source = 'claude_code_analytics' THEN 'claude_code'
    WHEN data_source = 'audit_logs' THEN 'claude_ai'
    WHEN api_key_id IS NOT NULL AND workspace_id != 'wrkspc_01WtfAtqQsV3zBDs9RYpNZdR' THEN 'claude_api'
    ELSE 'unknown'
  END
);

-- Create indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_claude_platform_user_date
ON `${project_id}.${dataset}.fact_claude_daily_usage` (platform, user_email, usage_date);

CREATE INDEX IF NOT EXISTS idx_claude_apikey_date
ON `${project_id}.${dataset}.fact_claude_daily_usage` (api_key_id, usage_date);