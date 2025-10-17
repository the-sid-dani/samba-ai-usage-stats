# Corrected Sample Queries for Three-Platform Testing

## 🚨 **ISSUES IDENTIFIED & FIXES**

### **1. Session Calculation Fixed**
```sql
-- ✅ CORRECTED: Count conversations for claude.ai, user-days for cursor
COUNT(CASE WHEN event_type = 'conversation_created' THEN 1 END) as conversations  -- claude.ai
COUNT(DISTINCT CONCAT(email, usage_date)) as unique_sessions                       -- cursor
```

### **2. Cursor Productivity Data Reality**
- **Finding**: Most users have 0 productivity (4603/4605 records)
- **But**: Some users DO have data (max 100 lines, 85 accepted)
- **Solution**: Query active users only, expand date range

## 📊 **CORRECTED TEST QUERIES**

### **Query 1: Active Users Only (Non-Zero Productivity)**
```sql
-- Find users with actual productivity data
SELECT
  email,
  COUNT(DISTINCT usage_date) as active_days,
  SUM(total_lines_added) as total_lines,
  SUM(accepted_lines_added) as accepted_lines,
  SUM(total_accepts) as total_accepts,
  ROUND(SAFE_DIVIDE(SUM(accepted_lines_added), SUM(total_lines_added)) * 100, 1) as acceptance_rate
FROM `ai-workflows-459123.ai_usage_analytics.raw_cursor_usage`
WHERE ingest_date >= '2025-09-27'
  AND email LIKE '%samba.tv'
  AND (total_lines_added > 0 OR accepted_lines_added > 0 OR total_accepts > 0)
GROUP BY email
ORDER BY total_lines DESC
```

### **Query 2: Multi-Platform User Analysis (Corrected)**
```sql
-- Comprehensive multi-platform user analytics
WITH cursor_productivity AS (
  SELECT
    email as user_email,
    'cursor' as platform,
    COUNT(DISTINCT usage_date) as active_days,
    SUM(total_lines_added) as metric_value,
    'lines_added' as metric_type
  FROM `ai-workflows-459123.ai_usage_analytics.raw_cursor_usage`
  WHERE ingest_date >= '2025-09-27'
    AND email LIKE '%samba.tv'
    AND total_lines_added > 0  -- Only include active users
  GROUP BY email
),

claude_ai_productivity AS (
  SELECT
    actor_email as user_email,
    'claude_ai' as platform,
    COUNT(DISTINCT event_date) as active_days,
    COUNT(CASE WHEN event_type = 'conversation_created' THEN 1 END) as metric_value,
    'conversations_created' as metric_type
  FROM `ai-workflows-459123.ai_usage_analytics.raw_claude_ai_audit_events`
  WHERE event_date >= '2025-09-27'
    AND actor_email LIKE '%samba.tv'
  GROUP BY actor_email
)

SELECT
  user_email,
  platform,
  active_days,
  metric_value,
  metric_type,
  ROUND(metric_value / active_days, 1) as daily_average
FROM cursor_productivity

UNION ALL

SELECT
  user_email,
  platform,
  active_days,
  metric_value,
  metric_type,
  ROUND(metric_value / active_days, 1) as daily_average
FROM claude_ai_productivity

ORDER BY user_email, platform
```

### **Query 3: Daily Platform Activity (Working Users Only)**
```sql
-- Daily activity for users with actual productivity
WITH active_cursor_users AS (
  SELECT DISTINCT email
  FROM `ai-workflows-459123.ai_usage_analytics.raw_cursor_usage`
  WHERE ingest_date >= '2025-09-27'
    AND (total_lines_added > 0 OR accepted_lines_added > 0 OR total_accepts > 0)
),

daily_cursor AS (
  SELECT
    usage_date,
    'cursor' as platform,
    COUNT(DISTINCT email) as active_users,
    SUM(total_lines_added) as total_lines,
    SUM(accepted_lines_added) as accepted_lines,
    COUNT(*) as sessions
  FROM `ai-workflows-459123.ai_usage_analytics.raw_cursor_usage`
  WHERE ingest_date >= '2025-09-27'
    AND email IN (SELECT email FROM active_cursor_users)
  GROUP BY usage_date
),

daily_claude_ai AS (
  SELECT
    event_date as usage_date,
    'claude_ai' as platform,
    COUNT(DISTINCT actor_email) as active_users,
    COUNT(CASE WHEN event_type = 'conversation_created' THEN 1 END) as total_conversations,
    COUNT(CASE WHEN event_type = 'file_uploaded' THEN 1 END) as files_uploaded,
    COUNT(*) as total_events
  FROM `ai-workflows-459123.ai_usage_analytics.raw_claude_ai_audit_events`
  WHERE event_date >= '2025-09-27'
    AND actor_email LIKE '%samba.tv'
  GROUP BY event_date
)

SELECT
  usage_date,
  'cursor' as platform,
  active_users,
  total_lines as primary_metric,
  'lines_added' as metric_type,
  sessions
FROM daily_cursor

UNION ALL

SELECT
  usage_date,
  'claude_ai' as platform,
  active_users,
  total_conversations as primary_metric,
  'conversations' as metric_type,
  total_events as sessions
FROM daily_claude_ai

ORDER BY usage_date DESC, platform
```

### **Query 4: Cross-Platform User Journey**
```sql
-- Test user journey across platforms (for dashboard design)
WITH user_timeline AS (
  SELECT
    email as user_email,
    usage_date,
    'cursor' as platform,
    CONCAT('Coded ', total_lines_added, ' lines') as activity_summary
  FROM `ai-workflows-459123.ai_usage_analytics.raw_cursor_usage`
  WHERE ingest_date >= '2025-09-27'
    AND email = 'sid.dani@samba.tv'
    AND total_lines_added > 0

  UNION ALL

  SELECT
    actor_email as user_email,
    event_date as usage_date,
    'claude_ai' as platform,
    CONCAT(COUNT(CASE WHEN event_type = 'conversation_created' THEN 1 END), ' conversations, ',
           COUNT(CASE WHEN event_type = 'file_uploaded' THEN 1 END), ' files') as activity_summary
  FROM `ai-workflows-459123.ai_usage_analytics.raw_claude_ai_audit_events`
  WHERE event_date >= '2025-09-27'
    AND actor_email = 'sid.dani@samba.tv'
  GROUP BY actor_email, event_date
)

SELECT
  usage_date,
  platform,
  activity_summary
FROM user_timeline
ORDER BY usage_date DESC, platform
```

## 🔧 **IMMEDIATE FIX NEEDED**

**Issue**: Cursor productivity data is mostly zeros, indicating a **pipeline data ingestion problem**.

**Recommendation**: Before creating BigQuery views, we should:
1. **Check production pipeline** for Cursor data transformation issues
2. **Verify Cursor API** is returning productivity data correctly
3. **Test with users who have recent coding activity** (not just Sid)

**For now, use these corrected queries to test the claude.ai data (which is working correctly) and identify active Cursor users for proper testing!**