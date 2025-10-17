-- Test New Two-Table Schema
-- Basic validation that tables can be created and accept data

-- Test Cursor table insertion
INSERT INTO `ai-workflows-459123.ai_usage_analytics.fact_cursor_daily_usage`
(event_id, usage_date, user_email, total_lines_added, accepted_lines_added, is_active, attribution_confidence, pipeline_run_id)
VALUES
('test_001', CURRENT_DATE(), 'test@samba.tv', 100, 80, true, 1.0, 'test_run_001');

-- Test Claude table insertion
INSERT INTO `ai-workflows-459123.ai_usage_analytics.fact_claude_daily_usage`
(event_id, usage_date, platform, user_email, claude_code_lines_added, attribution_confidence, pipeline_run_id)
VALUES
('test_002', CURRENT_DATE(), 'claude_code', 'test@samba.tv', 50, 0.9, 'test_run_001');

-- Test dimension table insertion
INSERT INTO `ai-workflows-459123.ai_usage_analytics.dim_users_enhanced`
(user_sk, user_email, full_name, department, ai_user_type, is_active)
VALUES
(1, 'test@samba.tv', 'Test User', 'Engineering', 'engineering', true);

-- Validate insertions worked
SELECT 'Cursor Test' as table_name, COUNT(*) as record_count
FROM `ai-workflows-459123.ai_usage_analytics.fact_cursor_daily_usage`
WHERE event_id = 'test_001'

UNION ALL

SELECT 'Claude Test' as table_name, COUNT(*) as record_count
FROM `ai-workflows-459123.ai_usage_analytics.fact_claude_daily_usage`
WHERE event_id = 'test_002'

UNION ALL

SELECT 'Users Test' as table_name, COUNT(*) as record_count
FROM `ai-workflows-459123.ai_usage_analytics.dim_users_enhanced`
WHERE user_sk = 1;

-- Clean up test data
DELETE FROM `ai-workflows-459123.ai_usage_analytics.fact_cursor_daily_usage` WHERE event_id = 'test_001';
DELETE FROM `ai-workflows-459123.ai_usage_analytics.fact_claude_daily_usage` WHERE event_id = 'test_002';
DELETE FROM `ai-workflows-459123.ai_usage_analytics.dim_users_enhanced` WHERE user_sk = 1;