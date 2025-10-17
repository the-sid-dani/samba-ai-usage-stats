-- Migration 002: Drop Old Tables (Breaking Change)
-- ⚠️ EXECUTE ONLY AFTER NEW TABLES ARE VALIDATED
-- Project: ai-workflows-459123, Dataset: ai_usage_analytics

-- Validation check - ensure new tables exist before dropping old ones
SELECT
  'Pre-migration validation' as check_type,
  COUNT(*) as new_tables_count
FROM `ai-workflows-459123.ai_usage_analytics.INFORMATION_SCHEMA.TABLES`
WHERE table_name IN ('fact_cursor_daily_usage', 'fact_claude_daily_usage', 'dim_users_enhanced', 'dim_date');

-- If validation passes (new_tables_count = 4), proceed with drops:

-- Drop old raw tables
DROP TABLE IF EXISTS `ai-workflows-459123.ai_usage_analytics.raw_cursor_usage`;
DROP TABLE IF EXISTS `ai-workflows-459123.ai_usage_analytics.raw_anthropic_usage`;
DROP TABLE IF EXISTS `ai-workflows-459123.ai_usage_analytics.raw_anthropic_cost`;

-- Drop old fact tables
DROP TABLE IF EXISTS `ai-workflows-459123.ai_usage_analytics.fct_usage_daily`;
DROP TABLE IF EXISTS `ai-workflows-459123.ai_usage_analytics.fct_cost_daily`;

-- Drop old dimension tables
DROP TABLE IF EXISTS `ai-workflows-459123.ai_usage_analytics.dim_users`;
DROP TABLE IF EXISTS `ai-workflows-459123.ai_usage_analytics.dim_api_keys`;

-- Validation check - confirm old tables are dropped
SELECT
  'Post-migration validation' as check_type,
  COUNT(*) as old_tables_remaining
FROM `ai-workflows-459123.ai_usage_analytics.INFORMATION_SCHEMA.TABLES`
WHERE table_name IN ('raw_cursor_usage', 'raw_anthropic_usage', 'raw_anthropic_cost', 'fct_usage_daily', 'fct_cost_daily', 'dim_users', 'dim_api_keys');

-- Success message
SELECT 'Migration 002 completed - old tables dropped successfully' as status;