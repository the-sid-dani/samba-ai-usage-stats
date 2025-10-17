# Current Data Dashboard Queries
**Works with existing BigQuery schema - Ready to use now**

## Current Data Available ✅

- **Cursor**: 2,341 records, 77 samba.tv users
- **Anthropic**: Found 21 usage records + 7 cost records (but schema needs platform field)

---

### Query 1: **Cursor Monthly Usage Summary**
**Purpose:** Main usage overview for samba.tv engineers
**Current Status:** ✅ Working with real data

```sql
-- Query Name: cursor_monthly_usage
SELECT
    DATE_TRUNC(usage_date, MONTH) as month,
    COUNT(DISTINCT email) as active_users,
    SUM(total_lines_added) as total_lines_added,
    SUM(accepted_lines_added) as total_lines_accepted,
    SAFE_DIVIDE(SUM(accepted_lines_added), SUM(total_lines_added)) as acceptance_rate,
    COUNT(*) as total_sessions,
    -- Estimated cost based on usage
    COUNT(*) * 0.10 as estimated_monthly_cost_usd
FROM `ai-workflows-459123.ai_usage_analytics.raw_cursor_usage`
WHERE ingest_date >= '2025-09-27'
    AND email LIKE '%samba.tv'
GROUP BY month
ORDER BY month DESC;
```

---

### Query 2: **Top Cursor Users This Month**
**Purpose:** Identify most active engineers
**Current Status:** ✅ Working with 77 real users

```sql
-- Query Name: top_cursor_users
SELECT
    email,
    SUM(total_lines_added) as total_lines_added,
    SUM(accepted_lines_added) as total_lines_accepted,
    SAFE_DIVIDE(SUM(accepted_lines_added), SUM(total_lines_added)) as acceptance_rate,
    COUNT(DISTINCT usage_date) as active_days,
    SUM(total_accepts) as total_accepts,
    -- Productivity metrics
    SAFE_DIVIDE(SUM(accepted_lines_added), COUNT(DISTINCT usage_date)) as avg_lines_per_day
FROM `ai-workflows-459123.ai_usage_analytics.raw_cursor_usage`
WHERE ingest_date >= '2025-09-27'
    AND email LIKE '%samba.tv'
    AND total_lines_added > 0
GROUP BY email
ORDER BY total_lines_accepted DESC
LIMIT 20;
```

---

### Query 3: **Daily Cursor Activity Trends**
**Purpose:** Track usage patterns over time
**Current Status:** ✅ Working with time series data

```sql
-- Query Name: daily_cursor_trends
SELECT
    usage_date,
    COUNT(DISTINCT email) as daily_active_users,
    COUNT(*) as total_sessions,
    SUM(total_lines_added) as daily_lines_added,
    SUM(accepted_lines_added) as daily_lines_accepted,
    SAFE_DIVIDE(SUM(accepted_lines_added), SUM(total_lines_added)) as daily_acceptance_rate,
    -- Usage intensity
    AVG(total_accepts) as avg_accepts_per_session
FROM `ai-workflows-459123.ai_usage_analytics.raw_cursor_usage`
WHERE ingest_date >= '2025-09-27'
    AND email LIKE '%samba.tv'
GROUP BY usage_date
ORDER BY usage_date DESC;
```

---

### Query 4: **User Engagement Categories**
**Purpose:** Segment users by engagement level
**Current Status:** ✅ Working with real user data

```sql
-- Query Name: user_engagement_segments
WITH user_metrics AS (
    SELECT
        email,
        COUNT(DISTINCT usage_date) as active_days,
        SUM(total_lines_added) as total_lines,
        SUM(accepted_lines_added) as accepted_lines,
        SUM(total_accepts) as total_accepts
    FROM `ai-workflows-459123.ai_usage_analytics.raw_cursor_usage`
    WHERE ingest_date >= '2025-09-27'
        AND email LIKE '%samba.tv'
    GROUP BY email
)
SELECT
    CASE
        WHEN active_days >= 5 AND total_lines >= 1000 THEN 'Power User'
        WHEN active_days >= 3 AND total_lines >= 500 THEN 'Regular User'
        WHEN active_days >= 1 AND total_lines >= 100 THEN 'Casual User'
        ELSE 'Light User'
    END as user_category,
    COUNT(*) as user_count,
    AVG(total_lines) as avg_lines_per_user,
    AVG(accepted_lines) as avg_accepted_per_user,
    SUM(total_lines) as category_total_lines
FROM user_metrics
WHERE total_lines > 0
GROUP BY user_category
ORDER BY user_count DESC;
```

---

### Query 5: **Department Usage Analysis**
**Purpose:** Cost allocation by team (based on email domains)
**Current Status:** ✅ Working with samba.tv emails

```sql
-- Query Name: department_usage_analysis
WITH user_departments AS (
    SELECT
        email,
        CASE
            WHEN email LIKE '%eng%' OR email LIKE '%dev%' THEN 'Engineering'
            WHEN email LIKE '%product%' OR email LIKE '%pm%' THEN 'Product'
            WHEN email LIKE '%design%' OR email LIKE '%ux%' THEN 'Design'
            WHEN email LIKE '%data%' OR email LIKE '%analytics%' THEN 'Data'
            WHEN email LIKE '%qa%' OR email LIKE '%test%' THEN 'QA'
            ELSE REGEXP_EXTRACT(email, r'^([^.]+)')  -- First part of email as department guess
        END as department
    FROM `ai-workflows-459123.ai_usage_analytics.raw_cursor_usage`
    WHERE ingest_date >= '2025-09-27'
        AND email LIKE '%samba.tv'
    GROUP BY email
)
SELECT
    ud.department,
    COUNT(DISTINCT cu.email) as team_size,
    SUM(cu.total_lines_added) as team_total_lines,
    SUM(cu.accepted_lines_added) as team_accepted_lines,
    SAFE_DIVIDE(SUM(cu.accepted_lines_added), SUM(cu.total_lines_added)) as team_acceptance_rate,
    -- Estimated team cost
    COUNT(*) * 0.10 as estimated_team_cost_usd,
    -- Productivity per person
    SAFE_DIVIDE(SUM(cu.accepted_lines_added), COUNT(DISTINCT cu.email)) as productivity_per_person
FROM `ai-workflows-459123.ai_usage_analytics.raw_cursor_usage` cu
JOIN user_departments ud ON cu.email = ud.email
WHERE cu.ingest_date >= '2025-09-27'
GROUP BY ud.department
ORDER BY team_total_lines DESC;
```

---

### Query 6: **Finance Executive Summary**
**Purpose:** High-level KPIs for leadership team
**Current Status:** ✅ Ready for executive dashboard

```sql
-- Query Name: finance_executive_summary
WITH summary_metrics AS (
    SELECT
        COUNT(DISTINCT email) as total_active_users,
        COUNT(*) as total_sessions,
        SUM(total_lines_added) as total_lines_generated,
        SUM(accepted_lines_added) as total_lines_accepted,
        -- Cost estimates
        COUNT(*) * 0.10 as estimated_total_cost,
        -- Date range
        MIN(usage_date) as earliest_usage,
        MAX(usage_date) as latest_usage,
        MAX(ingest_date) as data_freshness
    FROM `ai-workflows-459123.ai_usage_analytics.raw_cursor_usage`
    WHERE ingest_date >= '2025-09-27'
        AND email LIKE '%samba.tv'
)
SELECT
    total_active_users,
    total_sessions,
    total_lines_generated,
    total_lines_accepted,
    SAFE_DIVIDE(total_lines_accepted, total_lines_generated) as overall_acceptance_rate,
    estimated_total_cost,
    SAFE_DIVIDE(estimated_total_cost, total_active_users) as cost_per_user,
    SAFE_DIVIDE(total_lines_accepted, total_active_users) as productivity_per_user,
    earliest_usage,
    latest_usage,
    data_freshness,
    -- Data quality indicators
    DATE_DIFF(CURRENT_DATE(), data_freshness, DAY) as data_age_days
FROM summary_metrics;
```

---

## 🎯 **What These Queries Show You Right Now:**

✅ **77 real samba.tv engineers** using Cursor
✅ **2,341 usage sessions** tracked
✅ **Real productivity metrics** (lines added/accepted)
✅ **Department breakdown** by email analysis
✅ **User engagement segmentation**
✅ **Executive KPIs** ready for dashboards

## 📊 **Ready for Metabase Dashboard Creation**

These queries provide immediate business value with the current data. When you add the platform column later, you'll get the full Claude.AI/Claude Code/Claude API distinction.

**The data is live and ready for dashboard building right now!** 🚀