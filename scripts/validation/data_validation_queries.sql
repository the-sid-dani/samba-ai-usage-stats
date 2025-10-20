-- ============================================================================
-- DATA VALIDATION QUERIES FOR BIGQUERY INGESTION PIPELINES
-- ============================================================================
-- Purpose: Validate ingested data against Cursor and Claude dashboards
-- Date Range Reference: Oct 3, 2025 - Nov 3, 2025 (from screenshots)
-- ============================================================================

-- ============================================================================
-- CURSOR VALIDATION QUERIES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Query 1: Cursor Total Token Usage Validation
-- Expected: ~950.2M tokens (Oct 3 - Nov 3, 2025)
-- ----------------------------------------------------------------------------
SELECT
  'Cursor Total Tokens' AS metric_name,
  SUM(total_tokens) AS total_tokens,
  ROUND(SUM(total_tokens) / 1000000, 2) AS total_tokens_millions,
  COUNT(DISTINCT user_email) AS unique_users,
  MIN(activity_date) AS earliest_date,
  MAX(activity_date) AS latest_date
FROM `ai-workflows-459123.ai_usage_analytics.cursor_usage_stats`
WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03';

-- ----------------------------------------------------------------------------
-- Query 2: Cursor Token Usage by Model
-- Expected models: gpt-5, claude-4.5-sonnet-thinking, claude-4-sonnet, etc.
-- ----------------------------------------------------------------------------
SELECT
  model,
  SUM(total_tokens) AS total_tokens,
  ROUND(SUM(total_tokens) / 1000000, 2) AS tokens_millions,
  COUNT(DISTINCT user_email) AS unique_users,
  COUNT(*) AS record_count
FROM `ai-workflows-459123.ai_usage_analytics.cursor_usage_stats`
WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03'
GROUP BY model
ORDER BY total_tokens DESC;

-- ----------------------------------------------------------------------------
-- Query 3: Cursor Cost Validation
-- Expected: Total cost ~$691.50 (from finance screenshot)
-- Component costs should match screenshot breakdown
-- ----------------------------------------------------------------------------
SELECT
  'Cursor Total Cost' AS metric_name,
  SUM(total_cost) AS total_cost_usd,
  COUNT(DISTINCT user_email) AS unique_users,
  MIN(snapshot_date) AS earliest_date,
  MAX(snapshot_date) AS latest_date
FROM `ai-workflows-459123.ai_usage_analytics.cursor_spending`
WHERE snapshot_date BETWEEN '2025-10-03' AND '2025-11-03';

-- ----------------------------------------------------------------------------
-- Query 4: Cursor Cost by Model (Detailed Breakdown)
-- Expected breakdown matching screenshot values:
-- - Auto: $151.53
-- - claude-4.5-sonnet-thinking: $150.84
-- - claude-4-sonnet: $133.64
-- - claude-4-sonnet-1m-thinking: $113.13
-- - gpt-5: $96.00
-- - etc.
-- ----------------------------------------------------------------------------
SELECT
  model,
  SUM(total_cost) AS model_cost_usd,
  ROUND(SUM(total_cost), 2) AS model_cost_rounded,
  SUM(total_tokens) AS total_tokens,
  ROUND(SUM(total_tokens) / 1000000, 2) AS tokens_millions,
  COUNT(DISTINCT user_email) AS unique_users
FROM `ai-workflows-459123.ai_usage_analytics.cursor_spending`
WHERE snapshot_date BETWEEN '2025-10-03' AND '2025-11-03'
GROUP BY model
ORDER BY model_cost_usd DESC;

-- ----------------------------------------------------------------------------
-- Query 5: Cursor Daily Usage Trend
-- Validates data continuity and identifies gaps
-- ----------------------------------------------------------------------------
SELECT
  activity_date,
  COUNT(DISTINCT user_email) AS daily_active_users,
  SUM(total_tokens) AS daily_tokens,
  ROUND(SUM(total_tokens) / 1000000, 2) AS daily_tokens_millions,
  COUNT(*) AS daily_records
FROM `ai-workflows-459123.ai_usage_analytics.cursor_usage_stats`
WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03'
GROUP BY activity_date
ORDER BY activity_date;

-- ----------------------------------------------------------------------------
-- Query 6: Cursor Data Quality Check
-- Identifies NULL values, invalid dates, negative costs
-- ----------------------------------------------------------------------------
SELECT
  'Data Quality Issues' AS check_type,
  COUNTIF(user_email IS NULL) AS null_user_emails,
  COUNTIF(model IS NULL) AS null_models,
  COUNTIF(total_tokens IS NULL OR total_tokens < 0) AS invalid_tokens,
  COUNTIF(activity_date IS NULL) AS null_dates,
  COUNTIF(activity_date > CURRENT_DATE()) AS future_dates,
  COUNT(*) AS total_records
FROM `ai-workflows-459123.ai_usage_analytics.cursor_usage_stats`
WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03';


-- ============================================================================
-- CLAUDE VALIDATION QUERIES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Query 7: Claude AI Usage Stats Total Validation
-- Validates main claude_ai_usage_stats table
-- ----------------------------------------------------------------------------
SELECT
  'Claude AI Total Usage' AS metric_name,
  COUNT(*) AS total_records,
  COUNT(DISTINCT user_email) AS unique_users,
  COUNT(DISTINCT event_type) AS unique_event_types,
  MIN(activity_date) AS earliest_date,
  MAX(activity_date) AS latest_date
FROM `ai-workflows-459123.ai_usage_analytics.claude_ai_usage_stats`
WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03';

-- ----------------------------------------------------------------------------
-- Query 8: Claude AI Usage by Event Type
-- ----------------------------------------------------------------------------
SELECT
  event_type,
  COUNT(*) AS event_count,
  COUNT(DISTINCT user_email) AS unique_users,
  MIN(activity_date) AS first_occurrence,
  MAX(activity_date) AS last_occurrence
FROM `ai-workflows-459123.ai_usage_analytics.claude_ai_usage_stats`
WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03'
GROUP BY event_type
ORDER BY event_count DESC;

-- ----------------------------------------------------------------------------
-- Query 9: Claude Cost Report Validation
-- Validates token usage and costs from claude_cost_report
-- ----------------------------------------------------------------------------
SELECT
  'Claude Total Cost' AS metric_name,
  SUM(input_tokens + output_tokens + cache_creation_input_tokens + cache_read_input_tokens) AS total_tokens,
  ROUND(SUM(input_tokens + output_tokens + cache_creation_input_tokens + cache_read_input_tokens) / 1000000, 2) AS total_tokens_millions,
  SUM(total_cost) AS total_cost_usd,
  COUNT(DISTINCT workspace_id) AS unique_workspaces,
  COUNT(DISTINCT model) AS unique_models
FROM `ai-workflows-459123.ai_usage_analytics.claude_cost_report`
WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03';

-- ----------------------------------------------------------------------------
-- Query 10: Claude Cost by Model
-- ----------------------------------------------------------------------------
SELECT
  model,
  SUM(input_tokens + output_tokens + cache_creation_input_tokens + cache_read_input_tokens) AS total_tokens,
  ROUND(SUM(input_tokens + output_tokens + cache_creation_input_tokens + cache_read_input_tokens) / 1000000, 2) AS tokens_millions,
  SUM(total_cost) AS model_cost_usd,
  COUNT(*) AS record_count,
  COUNT(DISTINCT workspace_id) AS unique_workspaces
FROM `ai-workflows-459123.ai_usage_analytics.claude_cost_report`
WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03'
GROUP BY model
ORDER BY total_tokens DESC;

-- ----------------------------------------------------------------------------
-- Query 11: Claude Usage Report Validation
-- Validates claude_usage_report table
-- ----------------------------------------------------------------------------
SELECT
  'Claude Usage Report' AS metric_name,
  SUM(input_tokens + output_tokens) AS total_tokens,
  ROUND(SUM(input_tokens + output_tokens) / 1000000, 2) AS total_tokens_millions,
  COUNT(DISTINCT api_key_id) AS unique_api_keys,
  COUNT(DISTINCT workspace_id) AS unique_workspaces,
  COUNT(DISTINCT model) AS unique_models,
  COUNT(*) AS total_records
FROM `ai-workflows-459123.ai_usage_analytics.claude_usage_report`
WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03';

-- ----------------------------------------------------------------------------
-- Query 12: Claude Code Usage Stats
-- Validates claude_code_usage_stats table
-- ----------------------------------------------------------------------------
SELECT
  'Claude Code Usage' AS metric_name,
  COUNT(*) AS total_records,
  COUNT(DISTINCT user_email) AS unique_users,
  COUNT(DISTINCT terminal_type) AS unique_terminal_types,
  MIN(activity_date) AS earliest_date,
  MAX(activity_date) AS latest_date
FROM `ai-workflows-459123.ai_usage_analytics.claude_code_usage_stats`
WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03';

-- ----------------------------------------------------------------------------
-- Query 13: Claude Data Quality Check
-- ----------------------------------------------------------------------------
SELECT
  'Claude Data Quality' AS check_type,
  COUNTIF(user_email IS NULL) AS null_user_emails,
  COUNTIF(event_type IS NULL) AS null_event_types,
  COUNTIF(activity_date IS NULL) AS null_dates,
  COUNTIF(activity_date > CURRENT_DATE()) AS future_dates,
  COUNT(*) AS total_records
FROM `ai-workflows-459123.ai_usage_analytics.claude_ai_usage_stats`
WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03';


-- ============================================================================
-- CROSS-PLATFORM VALIDATION QUERIES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Query 14: Combined Daily Costs View Validation
-- Validates the vw_combined_daily_costs view
-- ----------------------------------------------------------------------------
SELECT
  cost_date,
  platform,
  SUM(daily_cost) AS total_daily_cost,
  COUNT(DISTINCT user_identifier) AS unique_users
FROM `ai-workflows-459123.ai_usage_analytics.vw_combined_daily_costs`
WHERE cost_date BETWEEN '2025-10-03' AND '2025-11-03'
GROUP BY cost_date, platform
ORDER BY cost_date, platform;

-- ----------------------------------------------------------------------------
-- Query 15: Engineering Productivity View Validation
-- ----------------------------------------------------------------------------
SELECT
  activity_date,
  COUNT(DISTINCT user_email) AS active_users,
  SUM(total_events) AS total_events
FROM `ai-workflows-459123.ai_usage_analytics.vw_engineering_productivity`
WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03'
GROUP BY activity_date
ORDER BY activity_date;

-- ----------------------------------------------------------------------------
-- Query 16: Partition Validation - Check for Missing Dates
-- Identifies gaps in daily partitions
-- ----------------------------------------------------------------------------
WITH date_range AS (
  SELECT date
  FROM UNNEST(GENERATE_DATE_ARRAY('2025-10-03', '2025-11-03')) AS date
),
cursor_dates AS (
  SELECT DISTINCT activity_date AS date
  FROM `ai-workflows-459123.ai_usage_analytics.cursor_usage_stats`
  WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03'
),
claude_dates AS (
  SELECT DISTINCT activity_date AS date
  FROM `ai-workflows-459123.ai_usage_analytics.claude_ai_usage_stats`
  WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03'
)
SELECT
  dr.date,
  CASE WHEN cd.date IS NOT NULL THEN 'Present' ELSE 'MISSING' END AS cursor_data,
  CASE WHEN cld.date IS NOT NULL THEN 'Present' ELSE 'MISSING' END AS claude_data
FROM date_range dr
LEFT JOIN cursor_dates cd ON dr.date = cd.date
LEFT JOIN claude_dates cld ON dr.date = cld.date
ORDER BY dr.date;


-- ============================================================================
-- REFERENCE VALUES FROM DASHBOARDS
-- ============================================================================
/*
CURSOR EXPECTED VALUES (Oct 3 - Nov 3, 2025):
- Total Tokens: 950.2M
- Total Cost: $691.50
- Model Breakdown:
  * Auto: 412.2M tokens, $151.53
  * claude-4.5-sonnet-thinking: 146.4M tokens, $150.84
  * claude-4-sonnet: 155.7M tokens, $133.64
  * claude-4-sonnet-1m-thinking: 95.1M tokens, $113.13
  * gpt-5: 106M tokens, $96.00
  * claude-4-sonnet-thinking: 29.1M tokens, $41.43
  * gemini-2.5-pro: 2.9M tokens, $3.02
  * gpt-5-fast: 628K tokens, $0.61
  * claude-4.5-sonnet: 259.7K tokens, $0.45
  * gpt-5-codex: 597.2K tokens, $0.44

CLAUDE EXPECTED VALUES:
- Active Users: 39 (vs 34 last period, +15.0%)
- Analytics available for users on Cursor 1.5+
*/
