-- ============================================================================
-- DATA VALIDATION QUERIES FOR BIGQUERY INGESTION PIPELINES (CORRECTED)
-- ============================================================================
-- Purpose: Validate ingested data against actual table schemas
-- Date Range Reference: Oct 3, 2025 - Nov 3, 2025
--
-- NOTE: Based on ACTUAL column names from BigQuery schemas
-- ============================================================================

-- ============================================================================
-- CURSOR VALIDATION QUERIES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Query 1: Cursor Total Cost Validation
-- Table: cursor_spending
-- Columns: spend_cents, included_spend_cents, total_spend_cents
-- Expected: Total cost ~$691.50 from dashboard (Oct 3 - Nov 3, 2025)
-- ----------------------------------------------------------------------------
SELECT
  'Cursor Total Cost' AS metric_name,
  SUM(total_spend_cents) / 100.0 AS total_cost_usd,
  SUM(spend_cents) / 100.0 AS actual_spend_usd,
  SUM(included_spend_cents) / 100.0 AS included_spend_usd,
  COUNT(DISTINCT user_email) AS unique_users,
  MIN(snapshot_date) AS earliest_date,
  MAX(snapshot_date) AS latest_date,
  COUNT(*) AS total_records
FROM `ai-workflows-459123.ai_usage_analytics.cursor_spending`
WHERE snapshot_date BETWEEN '2025-10-03' AND '2025-11-03';

-- ----------------------------------------------------------------------------
-- Query 2: Cursor Cost by User
-- Shows spending breakdown per user
-- ----------------------------------------------------------------------------
SELECT
  user_email,
  user_name,
  user_role,
  SUM(total_spend_cents) / 100.0 AS total_cost_usd,
  SUM(spend_cents) / 100.0 AS actual_spend_usd,
  SUM(included_spend_cents) / 100.0 AS included_spend_usd,
  SUM(fast_premium_requests) AS total_fast_premium_requests,
  MAX(hard_limit_override_dollars) AS hard_limit_override,
  COUNT(DISTINCT snapshot_date) AS days_with_data
FROM `ai-workflows-459123.ai_usage_analytics.cursor_spending`
WHERE snapshot_date BETWEEN '2025-10-03' AND '2025-11-03'
GROUP BY user_email, user_name, user_role
ORDER BY total_cost_usd DESC;

-- ----------------------------------------------------------------------------
-- Query 3: Cursor Daily Spend Trend
-- Shows daily cost aggregation
-- ----------------------------------------------------------------------------
SELECT
  snapshot_date,
  SUM(total_spend_cents) / 100.0 AS daily_total_cost_usd,
  SUM(spend_cents) / 100.0 AS daily_actual_spend_usd,
  SUM(included_spend_cents) / 100.0 AS daily_included_spend_usd,
  COUNT(DISTINCT user_email) AS daily_active_users,
  COUNT(*) AS daily_records
FROM `ai-workflows-459123.ai_usage_analytics.cursor_spending`
WHERE snapshot_date BETWEEN '2025-10-03' AND '2025-11-03'
GROUP BY snapshot_date
ORDER BY snapshot_date;

-- ----------------------------------------------------------------------------
-- Query 4: Cursor Usage Stats - Activity Summary
-- Table: cursor_usage_stats
-- Validates user activity metrics
-- ----------------------------------------------------------------------------
SELECT
  'Cursor Usage Summary' AS metric_name,
  COUNT(DISTINCT user_email) AS total_unique_users,
  COUNTIF(is_active) AS active_users,
  SUM(total_lines_added) AS total_lines_added,
  SUM(total_lines_deleted) AS total_lines_deleted,
  SUM(accepted_lines_added) AS accepted_lines_added,
  SUM(accepted_lines_deleted) AS accepted_lines_deleted,
  SUM(total_applies) AS total_applies,
  SUM(total_accepts) AS total_accepts,
  SUM(total_rejects) AS total_rejects,
  SUM(total_tabs_shown) AS total_tabs_shown,
  SUM(total_tabs_accepted) AS total_tabs_accepted,
  SUM(composer_requests) AS composer_requests,
  SUM(chat_requests) AS chat_requests,
  SUM(agent_requests) AS agent_requests
FROM `ai-workflows-459123.ai_usage_analytics.cursor_usage_stats`
WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03';

-- ----------------------------------------------------------------------------
-- Query 5: Cursor Most Active Users
-- Shows users with highest activity
-- ----------------------------------------------------------------------------
SELECT
  user_email,
  COUNT(DISTINCT activity_date) AS active_days,
  COUNTIF(is_active) AS days_marked_active,
  SUM(total_lines_added) AS lines_added,
  SUM(total_lines_deleted) AS lines_deleted,
  SUM(total_accepts) AS total_accepts,
  SUM(total_rejects) AS total_rejects,
  SUM(composer_requests + chat_requests + agent_requests) AS total_requests,
  STRING_AGG(DISTINCT most_used_model IGNORE NULLS) AS models_used
FROM `ai-workflows-459123.ai_usage_analytics.cursor_usage_stats`
WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03'
GROUP BY user_email
ORDER BY total_requests DESC
LIMIT 20;

-- ----------------------------------------------------------------------------
-- Query 6: Cursor Data Quality Check
-- Identifies NULL values and invalid data
-- ----------------------------------------------------------------------------
SELECT
  'Cursor Usage Stats Quality' AS table_name,
  COUNT(*) AS total_records,
  COUNTIF(user_email IS NULL) AS null_user_emails,
  COUNTIF(user_id IS NULL) AS null_user_ids,
  COUNTIF(activity_date IS NULL) AS null_dates,
  COUNTIF(activity_date > CURRENT_DATE()) AS future_dates,
  COUNTIF(total_lines_added < 0) AS negative_lines_added,
  COUNTIF(total_accepts < 0) AS negative_accepts,
  COUNTIF(ingestion_timestamp IS NULL) AS null_ingestion_timestamps
FROM `ai-workflows-459123.ai_usage_analytics.cursor_usage_stats`
WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03';

-- ----------------------------------------------------------------------------
-- Query 7: Cursor Spending Data Quality Check
-- ----------------------------------------------------------------------------
SELECT
  'Cursor Spending Quality' AS table_name,
  COUNT(*) AS total_records,
  COUNTIF(user_email IS NULL) AS null_user_emails,
  COUNTIF(snapshot_date IS NULL) AS null_dates,
  COUNTIF(snapshot_date > CURRENT_DATE()) AS future_dates,
  COUNTIF(total_spend_cents < 0) AS negative_total_spend,
  COUNTIF(spend_cents < 0) AS negative_spend,
  COUNTIF(included_spend_cents < 0) AS negative_included_spend,
  COUNTIF(billing_cycle_start IS NULL) AS null_billing_cycle
FROM `ai-workflows-459123.ai_usage_analytics.cursor_spending`
WHERE snapshot_date BETWEEN '2025-10-03' AND '2025-11-03';


-- ============================================================================
-- CLAUDE VALIDATION QUERIES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Query 8: Claude AI Usage Stats Summary
-- Table: claude_ai_usage_stats
-- Validates event tracking
-- ----------------------------------------------------------------------------
SELECT
  'Claude AI Usage Summary' AS metric_name,
  COUNT(*) AS total_events,
  COUNT(DISTINCT user_email) AS unique_users,
  COUNT(DISTINCT event_type) AS unique_event_types,
  COUNT(DISTINCT conversation_uuid) AS unique_conversations,
  COUNT(DISTINCT project_uuid) AS unique_projects,
  MIN(activity_date) AS earliest_date,
  MAX(activity_date) AS latest_date
FROM `ai-workflows-459123.ai_usage_analytics.claude_ai_usage_stats`
WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03';

-- ----------------------------------------------------------------------------
-- Query 9: Claude AI Events by Type
-- Shows distribution of event types
-- ----------------------------------------------------------------------------
SELECT
  event_type,
  COUNT(*) AS event_count,
  COUNT(DISTINCT user_email) AS unique_users,
  COUNT(DISTINCT conversation_uuid) AS unique_conversations,
  MIN(activity_date) AS first_occurrence,
  MAX(activity_date) AS last_occurrence
FROM `ai-workflows-459123.ai_usage_analytics.claude_ai_usage_stats`
WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03'
GROUP BY event_type
ORDER BY event_count DESC;

-- ----------------------------------------------------------------------------
-- Query 10: Claude AI Most Active Users
-- ----------------------------------------------------------------------------
SELECT
  user_email,
  user_name,
  COUNT(*) AS total_events,
  COUNT(DISTINCT event_type) AS unique_event_types,
  COUNT(DISTINCT conversation_uuid) AS conversations,
  COUNT(DISTINCT activity_date) AS active_days,
  COUNT(DISTINCT client_platform) AS platforms_used
FROM `ai-workflows-459123.ai_usage_analytics.claude_ai_usage_stats`
WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03'
GROUP BY user_email, user_name
ORDER BY total_events DESC
LIMIT 20;

-- ----------------------------------------------------------------------------
-- Query 11: Claude Cost Report Summary
-- Table: claude_cost_report
-- Validates cost tracking
-- ----------------------------------------------------------------------------
SELECT
  'Claude Cost Summary' AS metric_name,
  SUM(amount_usd) AS total_cost_usd,
  COUNT(DISTINCT organization_id) AS unique_organizations,
  COUNT(DISTINCT workspace_id) AS unique_workspaces,
  COUNT(DISTINCT model) AS unique_models,
  COUNT(DISTINCT cost_type) AS unique_cost_types,
  MIN(activity_date) AS earliest_date,
  MAX(activity_date) AS latest_date
FROM `ai-workflows-459123.ai_usage_analytics.claude_cost_report`
WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03';

-- ----------------------------------------------------------------------------
-- Query 12: Claude Cost by Model
-- ----------------------------------------------------------------------------
SELECT
  model,
  SUM(amount_usd) AS total_cost_usd,
  COUNT(*) AS record_count,
  COUNT(DISTINCT workspace_id) AS unique_workspaces,
  STRING_AGG(DISTINCT cost_type ORDER BY cost_type) AS cost_types
FROM `ai-workflows-459123.ai_usage_analytics.claude_cost_report`
WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03'
  AND model IS NOT NULL
GROUP BY model
ORDER BY total_cost_usd DESC;

-- ----------------------------------------------------------------------------
-- Query 13: Claude Cost by Type
-- Shows breakdown by cost type (tokens, cache, etc.)
-- ----------------------------------------------------------------------------
SELECT
  cost_type,
  token_type,
  SUM(amount_usd) AS total_cost_usd,
  COUNT(*) AS record_count,
  COUNT(DISTINCT model) AS models_involved
FROM `ai-workflows-459123.ai_usage_analytics.claude_cost_report`
WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03'
GROUP BY cost_type, token_type
ORDER BY total_cost_usd DESC;

-- ----------------------------------------------------------------------------
-- Query 14: Claude Usage Report Summary
-- Table: claude_usage_report
-- Validates token usage tracking
-- ----------------------------------------------------------------------------
SELECT
  'Claude Usage Report' AS metric_name,
  SUM(uncached_input_tokens) AS total_uncached_input_tokens,
  SUM(output_tokens) AS total_output_tokens,
  SUM(cache_read_input_tokens) AS total_cache_read_tokens,
  SUM(cache_creation_1h_tokens) AS total_cache_creation_1h_tokens,
  SUM(cache_creation_5m_tokens) AS total_cache_creation_5m_tokens,
  SUM(web_search_requests) AS total_web_search_requests,
  COUNT(DISTINCT organization_id) AS unique_organizations,
  COUNT(DISTINCT workspace_id) AS unique_workspaces,
  COUNT(DISTINCT model) AS unique_models
FROM `ai-workflows-459123.ai_usage_analytics.claude_usage_report`
WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03';

-- ----------------------------------------------------------------------------
-- Query 15: Claude Usage by Model
-- ----------------------------------------------------------------------------
SELECT
  model,
  SUM(uncached_input_tokens) AS uncached_input_tokens,
  SUM(output_tokens) AS output_tokens,
  SUM(cache_read_input_tokens) AS cache_read_tokens,
  SUM(cache_creation_1h_tokens + cache_creation_5m_tokens) AS cache_creation_tokens,
  ROUND((SUM(uncached_input_tokens) + SUM(output_tokens) +
         SUM(cache_read_input_tokens) + SUM(cache_creation_1h_tokens) +
         SUM(cache_creation_5m_tokens)) / 1000000.0, 2) AS total_tokens_millions,
  COUNT(DISTINCT workspace_id) AS unique_workspaces
FROM `ai-workflows-459123.ai_usage_analytics.claude_usage_report`
WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03'
  AND model IS NOT NULL
GROUP BY model
ORDER BY total_tokens_millions DESC;

-- ----------------------------------------------------------------------------
-- Query 16: Claude Code Usage Stats Summary
-- Table: claude_code_usage_stats
-- ----------------------------------------------------------------------------
SELECT
  'Claude Code Usage' AS metric_name,
  COUNT(DISTINCT user_email) AS unique_users,
  COUNT(DISTINCT organization_id) AS unique_organizations,
  SUM(num_sessions) AS total_sessions,
  SUM(lines_added) AS total_lines_added,
  SUM(lines_removed) AS total_lines_removed,
  SUM(commits_by_claude_code) AS total_commits,
  SUM(pull_requests_by_claude_code) AS total_pull_requests,
  SUM(edit_tool_accepted + multi_edit_tool_accepted + write_tool_accepted + notebook_edit_tool_accepted) AS total_tool_accepts,
  SUM(edit_tool_rejected + multi_edit_tool_rejected + write_tool_rejected + notebook_edit_tool_rejected) AS total_tool_rejects,
  SUM(total_input_tokens + total_output_tokens) AS total_tokens,
  SUM(total_estimated_cost_usd) AS total_estimated_cost_usd
FROM `ai-workflows-459123.ai_usage_analytics.claude_code_usage_stats`
WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03';

-- ----------------------------------------------------------------------------
-- Query 17: Claude Code Most Active Users
-- ----------------------------------------------------------------------------
SELECT
  user_email,
  terminal_type,
  SUM(num_sessions) AS sessions,
  SUM(lines_added) AS lines_added,
  SUM(lines_removed) AS lines_removed,
  SUM(commits_by_claude_code) AS commits,
  SUM(total_input_tokens + total_output_tokens) AS total_tokens,
  SUM(total_estimated_cost_usd) AS estimated_cost_usd,
  COUNT(DISTINCT activity_date) AS active_days
FROM `ai-workflows-459123.ai_usage_analytics.claude_code_usage_stats`
WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03'
GROUP BY user_email, terminal_type
ORDER BY sessions DESC
LIMIT 20;

-- ----------------------------------------------------------------------------
-- Query 18: Claude Data Quality Checks
-- ----------------------------------------------------------------------------
SELECT
  'Claude AI Usage Stats Quality' AS table_name,
  COUNT(*) AS total_records,
  COUNTIF(user_email IS NULL) AS null_user_emails,
  COUNTIF(event_type IS NULL) AS null_event_types,
  COUNTIF(activity_date IS NULL) AS null_dates,
  COUNTIF(activity_date > CURRENT_DATE()) AS future_dates,
  COUNTIF(event_id IS NULL) AS null_event_ids,
  COUNT(DISTINCT event_id) AS unique_event_ids
FROM `ai-workflows-459123.ai_usage_analytics.claude_ai_usage_stats`
WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03';


-- ============================================================================
-- CROSS-PLATFORM VALIDATION QUERIES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Query 19: Combined Platform Costs
-- Using the view to compare platform costs
-- ----------------------------------------------------------------------------
SELECT
  provider,
  SUM(amount_usd) AS total_cost_usd,
  COUNT(DISTINCT user_email) AS unique_users,
  COUNT(DISTINCT cost_date) AS days_with_data,
  MIN(cost_date) AS earliest_date,
  MAX(cost_date) AS latest_date
FROM `ai-workflows-459123.ai_usage_analytics.vw_combined_daily_costs`
WHERE cost_date BETWEEN '2025-10-03' AND '2025-11-03'
GROUP BY provider
ORDER BY total_cost_usd DESC;

-- ----------------------------------------------------------------------------
-- Query 20: Daily Combined Costs
-- Shows daily cost trend across platforms
-- ----------------------------------------------------------------------------
SELECT
  cost_date,
  provider,
  SUM(amount_usd) AS daily_cost_usd,
  COUNT(DISTINCT user_email) AS daily_users
FROM `ai-workflows-459123.ai_usage_analytics.vw_combined_daily_costs`
WHERE cost_date BETWEEN '2025-10-03' AND '2025-11-03'
GROUP BY cost_date, provider
ORDER BY cost_date, provider;

-- ----------------------------------------------------------------------------
-- Query 21: Missing Dates Check
-- Identifies gaps in daily data across all main tables
-- ----------------------------------------------------------------------------
WITH date_range AS (
  SELECT date
  FROM UNNEST(GENERATE_DATE_ARRAY('2025-10-03', '2025-11-03')) AS date
),
cursor_spending_dates AS (
  SELECT DISTINCT snapshot_date AS date
  FROM `ai-workflows-459123.ai_usage_analytics.cursor_spending`
  WHERE snapshot_date BETWEEN '2025-10-03' AND '2025-11-03'
),
cursor_usage_dates AS (
  SELECT DISTINCT activity_date AS date
  FROM `ai-workflows-459123.ai_usage_analytics.cursor_usage_stats`
  WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03'
),
claude_ai_dates AS (
  SELECT DISTINCT activity_date AS date
  FROM `ai-workflows-459123.ai_usage_analytics.claude_ai_usage_stats`
  WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03'
),
claude_cost_dates AS (
  SELECT DISTINCT activity_date AS date
  FROM `ai-workflows-459123.ai_usage_analytics.claude_cost_report`
  WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03'
),
claude_usage_dates AS (
  SELECT DISTINCT activity_date AS date
  FROM `ai-workflows-459123.ai_usage_analytics.claude_usage_report`
  WHERE activity_date BETWEEN '2025-10-03' AND '2025-11-03'
)
SELECT
  dr.date,
  CASE WHEN csd.date IS NOT NULL THEN 'Present' ELSE 'MISSING' END AS cursor_spending,
  CASE WHEN cud.date IS NOT NULL THEN 'Present' ELSE 'MISSING' END AS cursor_usage,
  CASE WHEN cad.date IS NOT NULL THEN 'Present' ELSE 'MISSING' END AS claude_ai_usage,
  CASE WHEN ccd.date IS NOT NULL THEN 'Present' ELSE 'MISSING' END AS claude_cost,
  CASE WHEN clu.date IS NOT NULL THEN 'Present' ELSE 'MISSING' END AS claude_usage_report
FROM date_range dr
LEFT JOIN cursor_spending_dates csd ON dr.date = csd.date
LEFT JOIN cursor_usage_dates cud ON dr.date = cud.date
LEFT JOIN claude_ai_dates cad ON dr.date = cad.date
LEFT JOIN claude_cost_dates ccd ON dr.date = ccd.date
LEFT JOIN claude_usage_dates clu ON dr.date = clu.date
ORDER BY dr.date;


-- ============================================================================
-- REFERENCE NOTES
-- ============================================================================
/*
TABLE SCHEMAS VERIFIED:

1. cursor_spending:
   - snapshot_date, user_email, user_id, spend_cents, included_spend_cents,
     total_spend_cents, fast_premium_requests, billing_cycle_start

2. cursor_usage_stats:
   - activity_date, user_email, is_active, total_lines_added, total_accepts,
     total_rejects, composer_requests, chat_requests, most_used_model

3. claude_ai_usage_stats:
   - activity_date, user_email, event_type, conversation_uuid, event_id

4. claude_cost_report:
   - activity_date, organization_id, workspace_id, model, cost_type,
     token_type, amount_usd

5. claude_usage_report:
   - activity_date, model, uncached_input_tokens, output_tokens,
     cache_read_input_tokens, cache_creation_1h_tokens

6. claude_code_usage_stats:
   - activity_date, user_email, terminal_type, num_sessions, lines_added,
     total_input_tokens, total_output_tokens, total_estimated_cost_usd

EXPECTED VALUES (from Cursor dashboard Oct 3 - Nov 3, 2025):
- Cursor Total Cost: ~$691.50
- Note: Dashboard shows per-model breakdown but BigQuery doesn't have that granularity
- We can only validate total costs, not per-model costs
*/
