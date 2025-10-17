-- Cursor Daily Usage Fact Table
-- AI Coding Agent productivity metrics with direct email attribution
-- Optimized for engineering productivity analytics

CREATE TABLE IF NOT EXISTS `${project_id}.${dataset}.fact_cursor_daily_usage` (
  -- Primary identifiers
  event_id STRING NOT NULL,
  usage_date DATE NOT NULL,
  user_email STRING NOT NULL,              -- ✅ Direct attribution (high confidence)

  -- ✅ Cursor Productivity Metrics (API-verified)
  total_lines_added INT64 DEFAULT 0,       -- totalLinesAdded
  total_lines_deleted INT64 DEFAULT 0,     -- totalLinesDeleted
  accepted_lines_added INT64 DEFAULT 0,    -- acceptedLinesAdded
  accepted_lines_deleted INT64 DEFAULT 0,  -- acceptedLinesDeleted
  net_lines_accepted INT64,                -- computed: accepted_added - accepted_deleted

  -- ✅ AI Interaction Metrics (API-verified)
  total_applies INT64 DEFAULT 0,           -- totalApplies
  total_accepts INT64 DEFAULT 0,           -- totalAccepts
  total_rejects INT64 DEFAULT 0,           -- totalRejects
  total_tabs_shown INT64 DEFAULT 0,        -- totalTabsShown
  total_tabs_accepted INT64 DEFAULT 0,     -- totalTabsAccepted

  -- ✅ Request Type Breakdown (API-verified)
  composer_requests INT64 DEFAULT 0,       -- composerRequests
  chat_requests INT64 DEFAULT 0,           -- chatRequests
  agent_requests INT64 DEFAULT 0,          -- agentRequests
  cmdk_usages INT64 DEFAULT 0,             -- cmdkUsages

  -- ✅ Cost Attribution (API-verified)
  subscription_included_reqs INT64 DEFAULT 0, -- subscriptionIncludedReqs
  usage_based_reqs INT64 DEFAULT 0,        -- usageBasedReqs
  api_key_reqs INT64 DEFAULT 0,            -- apiKeyReqs

  -- ✅ Context Data (API-verified)
  most_used_model STRING,                  -- mostUsedModel
  client_version STRING,                   -- clientVersion
  is_active BOOLEAN,                       -- isActive

  -- 📊 Calculated Productivity Metrics
  line_acceptance_rate FLOAT64,            -- accepted_lines_added / total_lines_added
  tab_acceptance_rate FLOAT64,             -- total_tabs_accepted / total_tabs_shown
  overall_acceptance_rate FLOAT64,         -- weighted average acceptance
  productivity_velocity FLOAT64,           -- net_lines_accepted per request

  -- 💰 Cost Estimation (hybrid subscription + overage model)
  estimated_subscription_cost FLOAT64,     -- allocated subscription cost
  estimated_overage_cost FLOAT64,          -- usage-based costs
  estimated_total_cost FLOAT64,            -- total daily cost

  -- Data quality
  attribution_confidence FLOAT64 DEFAULT 1.0, -- high confidence (direct email)

  -- Metadata
  ingest_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  pipeline_run_id STRING
)
PARTITION BY usage_date
CLUSTER BY user_email, usage_date, is_active
OPTIONS (
  description = "Cursor coding assistant productivity and cost metrics",
  require_partition_filter = true
);