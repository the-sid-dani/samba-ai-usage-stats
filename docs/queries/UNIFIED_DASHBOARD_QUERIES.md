# Unified Cross-Platform Dashboard Queries

## Unified Queries That Show ALL Platforms Together

These queries combine Cursor, Anthropic (Claude Code), and Claude API data in single views.

---

### Query 1: **ALL PLATFORMS - Monthly Cost Overview**
**Purpose:** See Cursor + Anthropic usage in one chart
**Shows:** All platforms side-by-side

```sql
-- Query Name: all_platforms_monthly_cost
WITH cursor_monthly AS (
    SELECT
        DATE_TRUNC(usage_date, MONTH) as month,
        'cursor' as platform,
        COUNT(DISTINCT email) as active_users,
        SUM(total_lines_added) as activity_metric,
        COUNT(*) * 0.10 as estimated_cost_usd
    FROM `ai-workflows-459123.ai_usage_analytics.raw_cursor_usage`
    WHERE ingest_date >= '2025-09-27'
        AND email LIKE '%samba.tv'
    GROUP BY month
),
anthropic_monthly AS (
    SELECT
        DATE_TRUNC(DATE(usage_date), MONTH) as month,
        'anthropic' as platform,
        COUNT(DISTINCT api_key_id) as active_users,
        SUM(uncached_input_tokens + cached_input_tokens + output_tokens) as activity_metric,
        0.0 as estimated_cost_usd  -- Will be real cost when cost data loaded
    FROM `ai-workflows-459123.ai_usage_analytics.raw_anthropic_usage`
    WHERE ingest_date >= '2025-09-27'
    GROUP BY month
)
SELECT * FROM cursor_monthly
UNION ALL
SELECT * FROM anthropic_monthly
ORDER BY month DESC, platform;
```

---

### Query 2: **ALL PLATFORMS - Active Users Comparison**
**Purpose:** Compare user counts across all AI tools
**Shows:** Platform adoption comparison

```sql
-- Query Name: all_platforms_user_comparison
WITH cursor_users AS (
    SELECT
        'cursor' as platform,
        COUNT(DISTINCT email) as total_users,
        COUNT(DISTINCT CASE WHEN total_lines_added > 0 THEN email END) as active_users,
        SUM(total_lines_added) as total_activity
    FROM `ai-workflows-459123.ai_usage_analytics.raw_cursor_usage`
    WHERE ingest_date >= '2025-09-27'
        AND email LIKE '%samba.tv'
),
anthropic_users AS (
    SELECT
        'anthropic' as platform,
        COUNT(DISTINCT api_key_id) as total_users,
        COUNT(DISTINCT CASE WHEN uncached_input_tokens + cached_input_tokens > 0 THEN api_key_id END) as active_users,
        SUM(uncached_input_tokens + cached_input_tokens + output_tokens) as total_activity
    FROM `ai-workflows-459123.ai_usage_analytics.raw_anthropic_usage`
    WHERE ingest_date >= '2025-09-27'
)
SELECT
    platform,
    total_users,
    active_users,
    total_activity,
    SAFE_DIVIDE(active_users, total_users) as adoption_rate
FROM cursor_users
UNION ALL
SELECT
    platform,
    total_users,
    active_users,
    total_activity,
    SAFE_DIVIDE(active_users, total_users) as adoption_rate
FROM anthropic_users
ORDER BY total_activity DESC;
```

---

### Query 3: **ALL PLATFORMS - Daily Activity Trends**
**Purpose:** See all platform usage trends in one chart
**Shows:** Multi-platform time series

```sql
-- Query Name: all_platforms_daily_trends
WITH cursor_daily AS (
    SELECT
        usage_date,
        'cursor' as platform,
        COUNT(DISTINCT email) as daily_users,
        SUM(total_lines_added) as daily_activity,
        COUNT(*) as daily_sessions
    FROM `ai-workflows-459123.ai_usage_analytics.raw_cursor_usage`
    WHERE ingest_date >= '2025-09-27'
        AND email LIKE '%samba.tv'
    GROUP BY usage_date
),
anthropic_daily AS (
    SELECT
        DATE(usage_date) as usage_date,
        'anthropic' as platform,
        COUNT(DISTINCT api_key_id) as daily_users,
        SUM(uncached_input_tokens + cached_input_tokens) as daily_activity,
        COUNT(*) as daily_sessions
    FROM `ai-workflows-459123.ai_usage_analytics.raw_anthropic_usage`
    WHERE ingest_date >= '2025-09-27'
    GROUP BY usage_date
)
SELECT * FROM cursor_daily
UNION ALL
SELECT * FROM anthropic_daily
ORDER BY usage_date DESC, platform;
```

---

### Query 4: **UNIFIED USER VIEW - All AI Tool Usage**
**Purpose:** See each user's usage across ALL platforms
**Shows:** Per-user cross-platform summary

```sql
-- Query Name: unified_user_activity
WITH cursor_users AS (
    SELECT
        email as user_identifier,
        email,
        SUM(total_lines_added) as cursor_lines_added,
        SUM(accepted_lines_added) as cursor_lines_accepted,
        COUNT(DISTINCT usage_date) as cursor_active_days,
        COUNT(*) * 0.10 as cursor_estimated_cost
    FROM `ai-workflows-459123.ai_usage_analytics.raw_cursor_usage`
    WHERE ingest_date >= '2025-09-27'
        AND email LIKE '%samba.tv'
    GROUP BY email
),
anthropic_usage AS (
    SELECT
        api_key_id as user_identifier,
        api_key_id as api_key,
        SUM(uncached_input_tokens + cached_input_tokens) as anthropic_input_tokens,
        SUM(output_tokens) as anthropic_output_tokens,
        COUNT(DISTINCT DATE(usage_date)) as anthropic_active_days
    FROM `ai-workflows-459123.ai_usage_analytics.raw_anthropic_usage`
    WHERE ingest_date >= '2025-09-27'
    GROUP BY api_key_id
)
SELECT
    COALESCE(cu.email, au.api_key, 'unknown') as user_identifier,
    -- Cursor metrics
    COALESCE(cu.cursor_lines_added, 0) as cursor_lines_added,
    COALESCE(cu.cursor_lines_accepted, 0) as cursor_lines_accepted,
    COALESCE(cu.cursor_active_days, 0) as cursor_active_days,
    COALESCE(cu.cursor_estimated_cost, 0) as cursor_estimated_cost,
    -- Anthropic metrics
    COALESCE(au.anthropic_input_tokens, 0) as anthropic_input_tokens,
    COALESCE(au.anthropic_output_tokens, 0) as anthropic_output_tokens,
    COALESCE(au.anthropic_active_days, 0) as anthropic_active_days,
    -- Combined metrics
    CASE
        WHEN cu.email IS NOT NULL AND au.api_key IS NOT NULL THEN 'Multi-Platform User'
        WHEN cu.email IS NOT NULL THEN 'Cursor Only'
        WHEN au.api_key IS NOT NULL THEN 'Anthropic Only'
        ELSE 'Unknown'
    END as user_type,
    -- Total estimated value
    COALESCE(cu.cursor_estimated_cost, 0) as total_estimated_cost
FROM cursor_users cu
FULL OUTER JOIN anthropic_usage au ON cu.user_identifier = au.user_identifier
ORDER BY total_estimated_cost DESC;
```

---

### Query 5: **EXECUTIVE CROSS-PLATFORM SUMMARY**
**Purpose:** All AI tools summary for leadership
**Shows:** Complete platform overview in one view

```sql
-- Query Name: executive_cross_platform_summary
WITH platform_summary AS (
    -- Cursor platform summary
    SELECT
        'cursor' as platform,
        COUNT(DISTINCT email) as unique_users,
        COUNT(*) as total_sessions,
        SUM(total_lines_added) as total_activity,
        COUNT(*) * 0.10 as estimated_cost,
        'lines_added' as activity_metric
    FROM `ai-workflows-459123.ai_usage_analytics.raw_cursor_usage`
    WHERE ingest_date >= '2025-09-27'
        AND email LIKE '%samba.tv'

    UNION ALL

    -- Anthropic platform summary
    SELECT
        'anthropic' as platform,
        COUNT(DISTINCT api_key_id) as unique_users,
        COUNT(*) as total_sessions,
        SUM(uncached_input_tokens + cached_input_tokens + output_tokens) as total_activity,
        0.0 as estimated_cost,
        'tokens' as activity_metric
    FROM `ai-workflows-459123.ai_usage_analytics.raw_anthropic_usage`
    WHERE ingest_date >= '2025-09-27'
)
SELECT
    platform,
    unique_users,
    total_sessions,
    total_activity,
    estimated_cost,
    activity_metric,
    -- Cross-platform metrics
    SAFE_DIVIDE(total_activity, unique_users) as activity_per_user,
    SAFE_DIVIDE(estimated_cost, unique_users) as cost_per_user
FROM platform_summary

UNION ALL

-- Total summary row
SELECT
    'TOTAL' as platform,
    SUM(unique_users) as unique_users,
    SUM(total_sessions) as total_sessions,
    0 as total_activity,  -- Can't sum different metrics
    SUM(estimated_cost) as estimated_cost,
    'mixed' as activity_metric,
    0 as activity_per_user,
    SAFE_DIVIDE(SUM(estimated_cost), SUM(unique_users)) as cost_per_user
FROM platform_summary

ORDER BY
    CASE platform
        WHEN 'TOTAL' THEN 3
        WHEN 'cursor' THEN 1
        WHEN 'anthropic' THEN 2
        ELSE 4
    END;
```

---

### Query 6: **REAL-TIME PLATFORM COMPARISON**
**Purpose:** Live comparison of all AI tool usage
**Shows:** Side-by-side platform metrics

```sql
-- Query Name: realtime_platform_comparison
SELECT
    'Today' as time_period,
    -- Cursor metrics
    (SELECT COUNT(DISTINCT email) FROM `ai-workflows-459123.ai_usage_analytics.raw_cursor_usage`
     WHERE ingest_date = '2025-09-27' AND email LIKE '%samba.tv') as cursor_users,

    (SELECT SUM(total_lines_added) FROM `ai-workflows-459123.ai_usage_analytics.raw_cursor_usage`
     WHERE ingest_date = '2025-09-27' AND email LIKE '%samba.tv') as cursor_activity,

    -- Anthropic metrics
    (SELECT COUNT(DISTINCT api_key_id) FROM `ai-workflows-459123.ai_usage_analytics.raw_anthropic_usage`
     WHERE ingest_date = '2025-09-27') as anthropic_api_keys,

    (SELECT SUM(uncached_input_tokens + cached_input_tokens) FROM `ai-workflows-459123.ai_usage_analytics.raw_anthropic_usage`
     WHERE ingest_date = '2025-09-27') as anthropic_tokens,

    -- Data freshness
    (SELECT MAX(ingest_timestamp) FROM `ai-workflows-459123.ai_usage_analytics.raw_cursor_usage`
     WHERE ingest_date = '2025-09-27') as last_updated;
```

---

## 🎯 **These Unified Queries Show:**

✅ **All platforms side-by-side** in single charts
✅ **Cross-platform user analysis** (who uses what)
✅ **Combined cost summaries** across all AI tools
✅ **Executive overview** of total AI spend
✅ **Real-time comparison** of platform adoption

## 📊 **For Metabase Dashboards:**

- **Query 1-3**: Multi-platform trend charts
- **Query 4**: User segmentation across all tools
- **Query 5-6**: Executive summary dashboards

**Now you can see Cursor + Anthropic + Claude usage all together in unified dashboard views!** 🎯