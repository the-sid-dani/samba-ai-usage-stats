-- Claude App Usage Productivity Metrics
--
-- This file contains queries for analyzing Claude.ai usage patterns
-- to derive productivity insights

-- ============================================================
-- 1. Daily Active Users and Activity Summary
-- ============================================================
SELECT
  activity_date,
  COUNT(DISTINCT user_email) as daily_active_users,
  COUNT(*) as total_events,

  -- Event type breakdown
  SUM(CASE WHEN event_type = 'conversation_created' THEN 1 ELSE 0 END) as conversations_created,
  SUM(CASE WHEN event_type = 'file_uploaded' THEN 1 ELSE 0 END) as files_uploaded,
  SUM(CASE WHEN event_type = 'project_created' THEN 1 ELSE 0 END) as projects_created,

  -- Platform breakdown
  SUM(CASE WHEN client_platform = 'desktop_app' THEN 1 ELSE 0 END) as desktop_events,
  SUM(CASE WHEN client_platform = 'web_claude_ai' THEN 1 ELSE 0 END) as web_events,
  SUM(CASE WHEN client_platform = 'ios' THEN 1 ELSE 0 END) as ios_events,
  SUM(CASE WHEN client_platform = 'android' THEN 1 ELSE 0 END) as android_events

FROM `ai-workflows-459123.ai_usage_analytics.claude_app_usage_logs`
WHERE activity_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY activity_date
ORDER BY activity_date DESC;


-- ============================================================
-- 2. User Productivity Profile (Last 30 Days)
-- ============================================================
SELECT
  user_email,
  user_name,

  -- Activity metrics
  COUNT(DISTINCT activity_date) as days_active,
  COUNT(*) as total_activities,

  -- Conversation metrics
  SUM(CASE WHEN event_type = 'conversation_created' THEN 1 ELSE 0 END) as conversations,

  -- Research/document metrics
  SUM(CASE WHEN event_type = 'file_uploaded' THEN 1 ELSE 0 END) as files_uploaded,
  ROUND(
    SUM(CASE WHEN event_type = 'file_uploaded' THEN 1 ELSE 0 END) * 100.0 /
    NULLIF(SUM(CASE WHEN event_type = 'conversation_created' THEN 1 ELSE 0 END), 0),
    1
  ) as files_per_conversation_pct,

  -- Collaboration metrics
  SUM(CASE WHEN event_type = 'project_created' THEN 1 ELSE 0 END) as projects_created,
  COUNT(DISTINCT project_uuid) as unique_projects,

  -- Platform preference
  ARRAY_AGG(client_platform ORDER BY cnt DESC LIMIT 1)[OFFSET(0)] as preferred_platform,

  -- Engagement score (weighted)
  (
    SUM(CASE WHEN event_type = 'conversation_created' THEN 2 ELSE 0 END) +
    SUM(CASE WHEN event_type = 'file_uploaded' THEN 1 ELSE 0 END) +
    SUM(CASE WHEN event_type = 'project_created' THEN 3 ELSE 0 END)
  ) as engagement_score

FROM `ai-workflows-459123.ai_usage_analytics.claude_app_usage_logs`
CROSS JOIN UNNEST([client_platform]) as platform
LEFT JOIN (
  SELECT client_platform, COUNT(*) as cnt
  FROM `ai-workflows-459123.ai_usage_analytics.claude_app_usage_logs`
  GROUP BY client_platform
) platform_counts ON platform = platform_counts.client_platform
WHERE activity_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY user_email, user_name
ORDER BY engagement_score DESC;


-- ============================================================
-- 3. Power Users: High File Upload to Conversation Ratio
-- (Research-intensive users)
-- ============================================================
WITH user_metrics AS (
  SELECT
    user_email,
    user_name,
    SUM(CASE WHEN event_type = 'conversation_created' THEN 1 ELSE 0 END) as conversations,
    SUM(CASE WHEN event_type = 'file_uploaded' THEN 1 ELSE 0 END) as files_uploaded
  FROM `ai-workflows-459123.ai_usage_analytics.claude_app_usage_logs`
  WHERE activity_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  GROUP BY user_email, user_name
)
SELECT
  user_email,
  user_name,
  conversations,
  files_uploaded,
  ROUND(files_uploaded * 1.0 / NULLIF(conversations, 0), 2) as files_per_conversation,
  CASE
    WHEN files_uploaded * 1.0 / NULLIF(conversations, 0) >= 3 THEN 'Research-Heavy'
    WHEN files_uploaded * 1.0 / NULLIF(conversations, 0) >= 1 THEN 'Balanced'
    ELSE 'Conversation-Focused'
  END as user_type
FROM user_metrics
WHERE conversations > 0
ORDER BY files_per_conversation DESC;


-- ============================================================
-- 4. Platform Adoption Over Time
-- ============================================================
SELECT
  DATE_TRUNC(activity_date, WEEK) as week,
  client_platform,
  COUNT(DISTINCT user_email) as unique_users,
  COUNT(*) as total_events
FROM `ai-workflows-459123.ai_usage_analytics.claude_app_usage_logs`
WHERE activity_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
  AND client_platform IS NOT NULL
GROUP BY week, client_platform
ORDER BY week DESC, unique_users DESC;


-- ============================================================
-- 5. Collaboration Activity (Projects)
-- ============================================================
SELECT
  activity_date,
  COUNT(DISTINCT CASE WHEN event_type = 'project_created' THEN user_email END) as users_creating_projects,
  SUM(CASE WHEN event_type = 'project_created' THEN 1 ELSE 0 END) as projects_created,
  COUNT(DISTINCT project_uuid) as unique_projects_active,
  COUNT(DISTINCT CASE WHEN project_uuid IS NOT NULL THEN user_email END) as users_in_projects
FROM `ai-workflows-459123.ai_usage_analytics.claude_app_usage_logs`
WHERE activity_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY activity_date
ORDER BY activity_date DESC;


-- ============================================================
-- 6. Event Type Distribution
-- ============================================================
SELECT
  event_type,
  COUNT(*) as event_count,
  COUNT(DISTINCT user_email) as unique_users,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as pct_of_total
FROM `ai-workflows-459123.ai_usage_analytics.claude_app_usage_logs`
WHERE activity_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY event_type
ORDER BY event_count DESC;


-- ============================================================
-- 7. Weekly Cohort Activity (Week-over-Week Retention)
-- ============================================================
WITH weekly_activity AS (
  SELECT
    DATE_TRUNC(activity_date, WEEK) as week,
    user_email
  FROM `ai-workflows-459123.ai_usage_analytics.claude_app_usage_logs`
  WHERE activity_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 WEEK)
  GROUP BY week, user_email
)
SELECT
  w1.week as cohort_week,
  COUNT(DISTINCT w1.user_email) as week_0_users,
  COUNT(DISTINCT w2.user_email) as week_1_users,
  COUNT(DISTINCT w3.user_email) as week_2_users,
  COUNT(DISTINCT w4.user_email) as week_4_users,

  ROUND(COUNT(DISTINCT w2.user_email) * 100.0 / COUNT(DISTINCT w1.user_email), 1) as week_1_retention_pct,
  ROUND(COUNT(DISTINCT w4.user_email) * 100.0 / COUNT(DISTINCT w1.user_email), 1) as week_4_retention_pct
FROM weekly_activity w1
LEFT JOIN weekly_activity w2 ON w1.user_email = w2.user_email AND w2.week = DATE_ADD(w1.week, INTERVAL 1 WEEK)
LEFT JOIN weekly_activity w3 ON w1.user_email = w3.user_email AND w3.week = DATE_ADD(w1.week, INTERVAL 2 WEEK)
LEFT JOIN weekly_activity w4 ON w1.user_email = w4.user_email AND w4.week = DATE_ADD(w1.week, INTERVAL 4 WEEK)
GROUP BY w1.week
ORDER BY w1.week DESC;
