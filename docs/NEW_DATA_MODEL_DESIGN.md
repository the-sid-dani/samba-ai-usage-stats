# 🏗️ AI Usage Analytics - OPTIMAL DATA MODEL REDESIGN
*Complete Ground-Up Architecture for Finance & Usage Metrics*

**Architect:** Winston | **Date:** 2025-09-27 | **Status:** DESIGN PHASE

---

## 🎯 DESIGN PRINCIPLES

### Core Requirements Analysis
1. **Finance First**: Cost allocation and ROI tracking is primary business need
2. **Usage Analytics**: Engineering productivity metrics for team optimization
3. **Platform Agnostic**: Unified metrics across Cursor, Claude Code, Claude API
4. **Real Attribution**: Accurate user-level cost and usage allocation
5. **Performance Optimized**: Sub-second query performance for dashboards

### Key Business Questions to Answer
- **Finance**: Who's spending what on AI tools and what's the ROI?
- **Engineering**: Which developers are most productive with AI assistance?
- **Operations**: Are we optimizing our AI tool usage and costs?
- **Strategy**: How should we allocate AI budgets across teams/projects?

---

## 📊 RAW DATA LAYER - API RESPONSE MAPPING

### Cursor API Raw Response
```json
{
  "data": [
    {
      "email": "developer@company.com",
      "date": "2025-09-27",
      "total_lines_added": 150,
      "accepted_lines_added": 120,
      "total_accepts": 45,
      "subscription_included_reqs": 25,
      "usage_based_reqs": 5,
      "session_id": "sess_123"
    }
  ]
}
```

### Anthropic Usage API Raw Response
```json
{
  "data": [
    {
      "starting_at": "2025-09-27T00:00:00Z",
      "results": [
        {
          "api_key_id": "apikey_01J9JbaiunVv4t2C3wCVVmkV",
          "workspace_id": "wrkspc_01WtfAtqQsV3zBDs9RYpNZdR",
          "model": "claude-3-5-sonnet-20241022",
          "uncached_input_tokens": 1500,
          "cached_input_tokens": 500,
          "cache_read_input_tokens": 200,
          "output_tokens": 800,
          "request_count": 12
        }
      ]
    }
  ],
  "has_more": false,
  "next_page": null
}
```

### Anthropic Cost API Raw Response
```json
{
  "data": [
    {
      "starting_at": "2025-09-27T00:00:00Z",
      "results": [
        {
          "amount": "0.45",
          "description": "Token usage",
          "cost_type": "input_tokens"
        }
      ]
    }
  ]
}
```

---

## 🗄️ OPTIMAL RAW DATA TABLES

### `raw_ai_events` (Unified Event Stream)
*Single table for all AI interactions across platforms*

```sql
CREATE TABLE `${project_id}.${dataset}.raw_ai_events` (
  -- Event identification
  event_id STRING NOT NULL,
  event_timestamp TIMESTAMP NOT NULL,
  event_date DATE NOT NULL,
  platform STRING NOT NULL, -- 'cursor', 'anthropic'
  event_type STRING NOT NULL, -- 'usage', 'cost', 'session'

  -- User attribution (when available)
  user_email STRING,
  api_key_id STRING,
  workspace_id STRING,
  session_id STRING,

  -- Platform-specific context
  model STRING, -- anthropic models
  service_tier STRING, -- anthropic service tier

  -- Usage metrics (nullable for cost-only events)
  input_tokens INT64,
  output_tokens INT64,
  cached_input_tokens INT64,
  cache_read_tokens INT64,
  lines_added INT64, -- cursor specific
  lines_accepted INT64, -- cursor specific
  suggestions_shown INT64,
  suggestions_accepted INT64,
  session_duration_seconds INT64,

  -- Cost metrics (nullable for usage-only events)
  cost_usd FLOAT64,
  cost_currency STRING DEFAULT 'USD',
  cost_type STRING, -- 'input_tokens', 'output_tokens', 'subscription', 'overage'
  billing_period STRING, -- 'monthly', 'usage_based'

  -- Request/session tracking
  request_count INT64 DEFAULT 1,
  subscription_requests INT64, -- cursor subscription included
  overage_requests INT64, -- cursor usage-based

  -- Pipeline metadata
  ingest_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  pipeline_run_id STRING,
  raw_response JSON, -- full API response for debugging

  -- Data quality
  attribution_method STRING, -- 'direct_email', 'api_key_mapping', 'unknown'
  data_quality_score FLOAT64, -- 0.0 to 1.0
  validation_errors ARRAY<STRING>
)
PARTITION BY event_date
CLUSTER BY platform, user_email, event_type, event_timestamp
OPTIONS (
  description = "Unified AI events stream - all platforms, usage and cost",
  require_partition_filter = true
);
```

### `api_key_mappings` (Enhanced Attribution)
*Real-time user attribution with confidence scoring*

```sql
CREATE TABLE `${project_id}.${dataset}.api_key_mappings` (
  -- Mapping identification
  mapping_id STRING NOT NULL,
  api_key_id STRING NOT NULL,
  api_key_name STRING,

  -- User attribution
  user_email STRING NOT NULL,
  user_full_name STRING,
  department STRING,
  team STRING,
  manager_email STRING,

  -- Platform and context
  platform STRING NOT NULL, -- 'anthropic', 'cursor'
  platform_subtype STRING, -- 'claude_code', 'claude_api', 'claude_web'
  workspace_id STRING,
  environment STRING, -- 'development', 'production', 'testing'

  -- Usage context
  intended_use STRING, -- 'personal', 'team', 'project_specific'
  cost_center STRING,
  project_codes ARRAY<STRING>,

  -- Lifecycle management
  is_active BOOLEAN DEFAULT true,
  created_date DATE,
  last_verified_date DATE,
  expires_date DATE,
  auto_deactivate_after_days INT64 DEFAULT 365,

  -- Attribution confidence
  confidence_score FLOAT64, -- 0.0 to 1.0
  attribution_source STRING, -- 'manual_entry', 'google_sheets', 'sso_sync'
  last_activity_date DATE,

  -- Audit trail
  created_by STRING,
  updated_by STRING,
  updated_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  change_history JSON
)
CLUSTER BY platform, user_email, api_key_id
OPTIONS (
  description = "Enhanced API key to user mappings with confidence scoring"
);
```

---

## 🏢 DIMENSIONAL MODEL

### `dim_users` (Enhanced User Dimension)
```sql
CREATE TABLE `${project_id}.${dataset}.dim_users` (
  -- User identification
  user_sk INT64 NOT NULL, -- surrogate key
  user_email STRING NOT NULL,
  user_id STRING, -- natural key from SSO
  employee_id STRING,

  -- Personal information
  first_name STRING,
  last_name STRING,
  full_name STRING,
  display_name STRING,
  preferred_name STRING,

  -- Organizational hierarchy
  department STRING,
  department_code STRING,
  team STRING,
  sub_team STRING,
  manager_email STRING,
  director_email STRING,
  cost_center STRING,

  -- Role and permissions
  job_title STRING,
  seniority_level STRING, -- 'junior', 'mid', 'senior', 'staff', 'principal'
  employment_type STRING, -- 'full_time', 'contractor', 'intern'
  location STRING,
  timezone STRING,

  -- AI usage permissions
  ai_budget_monthly_usd FLOAT64,
  approved_platforms ARRAY<STRING>,
  usage_restrictions JSON,

  -- Status and lifecycle
  is_active BOOLEAN DEFAULT true,
  start_date DATE,
  end_date DATE,
  last_activity_date DATE,

  -- SCD Type 2 fields
  effective_date DATE,
  expiration_date DATE,
  is_current BOOLEAN DEFAULT true,

  -- Metadata
  created_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  data_source STRING DEFAULT 'manual'
)
CLUSTER BY user_email, department, is_current
OPTIONS (
  description = "Enhanced user dimension with organizational hierarchy and AI permissions"
);
```

### `dim_platforms` (Platform Master Data)
```sql
CREATE TABLE `${project_id}.${dataset}.dim_platforms` (
  platform_sk INT64 NOT NULL,
  platform_code STRING NOT NULL, -- 'cursor', 'anthropic'
  platform_name STRING NOT NULL,
  platform_subtype STRING, -- 'claude_code', 'claude_api', 'claude_web'

  -- Platform details
  vendor STRING,
  category STRING, -- 'coding_assistant', 'llm_api', 'chat_interface'
  primary_use_case STRING,
  cost_model STRING, -- 'subscription', 'usage_based', 'hybrid'

  -- Metrics and capabilities
  supports_token_tracking BOOLEAN,
  supports_session_tracking BOOLEAN,
  supports_productivity_metrics BOOLEAN,
  supports_real_time_cost BOOLEAN,

  -- Cost structure
  base_subscription_cost_usd FLOAT64,
  overage_rate_per_unit FLOAT64,
  unit_type STRING, -- 'tokens', 'requests', 'lines'
  billing_cycle STRING, -- 'monthly', 'annual'

  -- Technical details
  api_endpoint STRING,
  rate_limit_per_minute INT64,
  max_batch_size INT64,
  data_retention_days INT64,

  -- Status
  is_active BOOLEAN DEFAULT true,
  contract_start_date DATE,
  contract_end_date DATE,

  -- Metadata
  created_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
CLUSTER BY platform_code, category
OPTIONS (
  description = "Platform master data with cost models and capabilities"
);
```

---

## 📈 FACT TABLES (Star Schema)

### `fact_ai_usage` (Unified Usage Facts)
*Single fact table for all AI usage across platforms*

```sql
CREATE TABLE `${project_id}.${dataset}.fact_ai_usage` (
  -- Dimensions (Foreign Keys)
  user_sk INT64,
  platform_sk INT64,
  date_sk INT64, -- YYYYMMDD format
  time_sk INT64, -- HHMMSS format

  -- Degenerate dimensions
  event_id STRING,
  session_id STRING,
  api_key_id STRING,
  model STRING,

  -- Usage measures (additive)
  session_count INT64 DEFAULT 0,
  request_count INT64 DEFAULT 0,

  -- Token measures (anthropic platforms)
  input_tokens INT64 DEFAULT 0,
  output_tokens INT64 DEFAULT 0,
  cached_input_tokens INT64 DEFAULT 0,
  cache_read_tokens INT64 DEFAULT 0,
  total_tokens INT64 DEFAULT 0, -- computed

  -- Productivity measures (cursor platform)
  lines_added INT64 DEFAULT 0,
  lines_accepted INT64 DEFAULT 0,
  suggestions_shown INT64 DEFAULT 0,
  suggestions_accepted INT64 DEFAULT 0,

  -- Efficiency measures (derived)
  acceptance_rate FLOAT64, -- lines_accepted / lines_added
  suggestion_acceptance_rate FLOAT64, -- suggestions_accepted / suggestions_shown
  tokens_per_session FLOAT64, -- total_tokens / session_count
  productivity_score FLOAT64, -- lines_accepted / session_count

  -- Session measures
  session_duration_seconds INT64 DEFAULT 0,
  active_time_seconds INT64 DEFAULT 0,
  idle_time_seconds INT64 DEFAULT 0,

  -- Data quality measures
  attribution_confidence FLOAT64, -- 0.0 to 1.0
  data_completeness FLOAT64, -- % of expected fields populated

  -- Metadata
  event_timestamp TIMESTAMP,
  ingest_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  pipeline_run_id STRING
)
PARTITION BY DATE(event_timestamp)
CLUSTER BY user_sk, platform_sk, DATE(event_timestamp)
OPTIONS (
  description = "Unified AI usage facts across all platforms",
  require_partition_filter = true
);
```

### `fact_ai_costs` (Financial Facts)
*Detailed cost tracking with allocation flexibility*

```sql
CREATE TABLE `${project_id}.${dataset}.fact_ai_costs` (
  -- Dimensions
  user_sk INT64,
  platform_sk INT64,
  date_sk INT64,
  cost_center_sk INT64,

  -- Degenerate dimensions
  api_key_id STRING,
  billing_account_id STRING,
  invoice_id STRING,

  -- Cost measures (additive)
  base_cost_usd FLOAT64 DEFAULT 0.0,
  overage_cost_usd FLOAT64 DEFAULT 0.0,
  total_cost_usd FLOAT64 DEFAULT 0.0, -- computed

  -- Cost allocation measures
  allocated_cost_usd FLOAT64, -- actual allocated amount
  allocation_percentage FLOAT64, -- % of total cost allocated to this user
  allocation_method STRING, -- 'usage_based', 'equal_split', 'manual'

  -- Volume measures (for rate calculations)
  billable_tokens INT64 DEFAULT 0,
  billable_requests INT64 DEFAULT 0,
  billable_sessions INT64 DEFAULT 0,
  subscription_units FLOAT64 DEFAULT 0.0,

  -- Rate measures (semi-additive)
  cost_per_token FLOAT64,
  cost_per_request FLOAT64,
  cost_per_session FLOAT64,

  -- Billing context
  cost_type STRING, -- 'subscription', 'usage', 'overage', 'one_time'
  billing_period STRING, -- 'monthly', 'daily', 'transaction'
  currency_code STRING DEFAULT 'USD',
  exchange_rate FLOAT64 DEFAULT 1.0,

  -- Budget tracking
  budget_category STRING,
  budget_allocated_usd FLOAT64,
  budget_remaining_usd FLOAT64,
  is_over_budget BOOLEAN DEFAULT false,

  -- Data quality
  cost_confidence FLOAT64, -- 0.0 to 1.0
  allocation_confidence FLOAT64,
  reconciliation_status STRING, -- 'pending', 'reconciled', 'disputed'

  -- Metadata
  cost_timestamp TIMESTAMP,
  ingest_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  pipeline_run_id STRING
)
PARTITION BY DATE(cost_timestamp)
CLUSTER BY user_sk, platform_sk, DATE(cost_timestamp)
OPTIONS (
  description = "AI cost facts with flexible allocation and budget tracking",
  require_partition_filter = true
);
```

---

## 🎯 BUSINESS INTELLIGENCE VIEWS

### `vw_executive_dashboard` (C-Suite KPIs)
```sql
CREATE OR REPLACE VIEW `${project_id}.${dataset}.vw_executive_dashboard` AS
WITH monthly_summary AS (
  SELECT
    DATE_TRUNC(DATE(cost_timestamp), MONTH) as month,
    COUNT(DISTINCT user_sk) as active_users,
    SUM(total_cost_usd) as total_monthly_cost,
    SUM(allocated_cost_usd) as allocated_monthly_cost,

    -- Platform breakdown
    SUM(CASE WHEN p.platform_code = 'cursor' THEN total_cost_usd ELSE 0 END) as cursor_cost,
    SUM(CASE WHEN p.platform_code = 'anthropic' THEN total_cost_usd ELSE 0 END) as anthropic_cost,

    -- Growth metrics
    LAG(SUM(total_cost_usd)) OVER (ORDER BY DATE_TRUNC(DATE(cost_timestamp), MONTH)) as prev_month_cost,
    LAG(COUNT(DISTINCT user_sk)) OVER (ORDER BY DATE_TRUNC(DATE(cost_timestamp), MONTH)) as prev_month_users

  FROM fact_ai_costs c
  JOIN dim_platforms p ON c.platform_sk = p.platform_sk
  WHERE DATE(cost_timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
  GROUP BY 1
),
productivity_summary AS (
  SELECT
    DATE_TRUNC(DATE(event_timestamp), MONTH) as month,
    SUM(lines_accepted) as total_lines_produced,
    AVG(acceptance_rate) as avg_acceptance_rate,
    AVG(productivity_score) as avg_productivity_score
  FROM fact_ai_usage
  WHERE DATE(event_timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
    AND lines_accepted > 0
  GROUP BY 1
)
SELECT
  ms.month,

  -- Financial KPIs
  ms.total_monthly_cost,
  ms.allocated_monthly_cost,
  ms.total_monthly_cost / ms.active_users as cost_per_user,

  -- Growth KPIs
  SAFE_DIVIDE(ms.total_monthly_cost - ms.prev_month_cost, ms.prev_month_cost) as cost_growth_mom,
  SAFE_DIVIDE(ms.active_users - ms.prev_month_users, ms.prev_month_users) as user_growth_mom,

  -- Platform mix
  SAFE_DIVIDE(ms.cursor_cost, ms.total_monthly_cost) as cursor_cost_share,
  SAFE_DIVIDE(ms.anthropic_cost, ms.total_monthly_cost) as anthropic_cost_share,

  -- ROI indicators
  ps.total_lines_produced,
  SAFE_DIVIDE(ms.total_monthly_cost, ps.total_lines_produced) as cost_per_line_produced,
  ps.avg_acceptance_rate,

  -- Forecasting
  ms.total_monthly_cost * 12 as annual_run_rate,

  -- Executive summary
  CASE
    WHEN SAFE_DIVIDE(ms.total_monthly_cost, ps.total_lines_produced) <= 0.10 THEN 'Excellent ROI'
    WHEN SAFE_DIVIDE(ms.total_monthly_cost, ps.total_lines_produced) <= 0.25 THEN 'Good ROI'
    WHEN SAFE_DIVIDE(ms.total_monthly_cost, ps.total_lines_produced) <= 0.50 THEN 'Acceptable ROI'
    ELSE 'Review Required'
  END as roi_status

FROM monthly_summary ms
LEFT JOIN productivity_summary ps ON ms.month = ps.month
ORDER BY ms.month DESC;
```

### `vw_team_productivity` (Engineering Manager Dashboard)
```sql
CREATE OR REPLACE VIEW `${project_id}.${dataset}.vw_team_productivity` AS
WITH user_monthly_metrics AS (
  SELECT
    DATE_TRUNC(DATE(u.event_timestamp), MONTH) as month,
    usr.department,
    usr.team,
    usr.user_email,
    usr.full_name,

    -- Usage metrics
    SUM(u.session_count) as monthly_sessions,
    SUM(u.lines_accepted) as monthly_lines_produced,
    SUM(u.total_tokens) as monthly_tokens,
    AVG(u.acceptance_rate) as avg_acceptance_rate,
    AVG(u.productivity_score) as avg_productivity_score,

    -- Engagement metrics
    COUNT(DISTINCT DATE(u.event_timestamp)) as active_days,
    COUNT(DISTINCT DATE(u.event_timestamp)) / DATE_DIFF(LAST_DAY(DATE_TRUNC(DATE(u.event_timestamp), MONTH)), DATE_TRUNC(DATE(u.event_timestamp), MONTH), DAY) as engagement_rate,

    -- Cost allocation
    COALESCE(SUM(c.allocated_cost_usd), 0) as monthly_allocated_cost

  FROM fact_ai_usage u
  JOIN dim_users usr ON u.user_sk = usr.user_sk AND usr.is_current = true
  LEFT JOIN fact_ai_costs c ON u.user_sk = c.user_sk AND DATE(u.event_timestamp) = DATE(c.cost_timestamp)
  WHERE DATE(u.event_timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH)
  GROUP BY 1, 2, 3, 4, 5
),
team_benchmarks AS (
  SELECT
    month,
    department,
    team,

    -- Team aggregates
    COUNT(*) as team_size,
    SUM(monthly_lines_produced) as team_total_lines,
    SUM(monthly_allocated_cost) as team_total_cost,
    AVG(avg_acceptance_rate) as team_avg_acceptance_rate,

    -- Benchmarks
    APPROX_QUANTILES(avg_acceptance_rate, 4)[OFFSET(2)] as median_acceptance_rate,
    APPROX_QUANTILES(monthly_lines_produced, 4)[OFFSET(2)] as median_productivity,
    APPROX_QUANTILES(monthly_allocated_cost, 4)[OFFSET(2)] as median_cost_per_user

  FROM user_monthly_metrics
  GROUP BY 1, 2, 3
)
SELECT
  umm.*,

  -- Team context
  tb.team_size,
  tb.team_total_lines,
  tb.team_total_cost,

  -- Individual rankings
  RANK() OVER (PARTITION BY umm.month, umm.department, umm.team ORDER BY umm.monthly_lines_produced DESC) as productivity_rank,
  RANK() OVER (PARTITION BY umm.month, umm.department, umm.team ORDER BY umm.avg_acceptance_rate DESC) as acceptance_rank,
  RANK() OVER (PARTITION BY umm.month, umm.department, umm.team ORDER BY umm.monthly_allocated_cost ASC) as cost_efficiency_rank,

  -- Performance vs benchmarks
  CASE
    WHEN umm.avg_acceptance_rate >= tb.median_acceptance_rate * 1.2 THEN 'Top Performer'
    WHEN umm.avg_acceptance_rate >= tb.median_acceptance_rate THEN 'Above Average'
    WHEN umm.avg_acceptance_rate >= tb.median_acceptance_rate * 0.8 THEN 'Below Average'
    ELSE 'Needs Support'
  END as performance_tier,

  -- Cost efficiency
  SAFE_DIVIDE(umm.monthly_allocated_cost, umm.monthly_lines_produced) as cost_per_line,
  SAFE_DIVIDE(umm.monthly_lines_produced, umm.monthly_sessions) as lines_per_session,

  -- Growth tracking
  LAG(umm.monthly_lines_produced) OVER (PARTITION BY umm.user_email ORDER BY umm.month) as prev_month_productivity,
  SAFE_DIVIDE(
    umm.monthly_lines_produced - LAG(umm.monthly_lines_produced) OVER (PARTITION BY umm.user_email ORDER BY umm.month),
    LAG(umm.monthly_lines_produced) OVER (PARTITION BY umm.user_email ORDER BY umm.month)
  ) as productivity_growth_mom

FROM user_monthly_metrics umm
JOIN team_benchmarks tb ON umm.month = tb.month
  AND umm.department = tb.department
  AND umm.team = tb.team
ORDER BY umm.month DESC, umm.department, umm.team, umm.productivity_rank;
```

### `vw_cost_allocation_detailed` (Finance Dashboard)
```sql
CREATE OR REPLACE VIEW `${project_id}.${dataset}.vw_cost_allocation_detailed` AS
WITH allocation_summary AS (
  SELECT
    DATE_TRUNC(DATE(c.cost_timestamp), MONTH) as month,
    usr.department,
    usr.cost_center,
    usr.user_email,
    p.platform_name,

    -- Cost breakdown
    SUM(c.base_cost_usd) as base_cost,
    SUM(c.overage_cost_usd) as overage_cost,
    SUM(c.total_cost_usd) as total_cost,
    SUM(c.allocated_cost_usd) as allocated_cost,

    -- Allocation metrics
    AVG(c.allocation_confidence) as avg_allocation_confidence,
    AVG(c.cost_confidence) as avg_cost_confidence,

    -- Usage context
    SUM(c.billable_tokens) as billable_tokens,
    SUM(c.billable_requests) as billable_requests,

    -- Budget tracking
    MAX(c.budget_allocated_usd) as budget_allocated,
    SUM(CASE WHEN c.is_over_budget THEN c.total_cost_usd ELSE 0 END) as over_budget_amount,

    -- Reconciliation status
    SUM(CASE WHEN c.reconciliation_status = 'reconciled' THEN c.total_cost_usd ELSE 0 END) as reconciled_cost,
    SUM(CASE WHEN c.reconciliation_status = 'pending' THEN c.total_cost_usd ELSE 0 END) as pending_cost,
    SUM(CASE WHEN c.reconciliation_status = 'disputed' THEN c.total_cost_usd ELSE 0 END) as disputed_cost

  FROM fact_ai_costs c
  JOIN dim_users usr ON c.user_sk = usr.user_sk AND usr.is_current = true
  JOIN dim_platforms p ON c.platform_sk = p.platform_sk
  WHERE DATE(c.cost_timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
  GROUP BY 1, 2, 3, 4, 5
)
SELECT
  *,

  -- Cost efficiency metrics
  SAFE_DIVIDE(total_cost, billable_tokens) * 1000 as cost_per_1k_tokens,
  SAFE_DIVIDE(total_cost, billable_requests) as cost_per_request,
  SAFE_DIVIDE(allocated_cost, total_cost) as allocation_rate,

  -- Budget variance
  SAFE_DIVIDE(total_cost - budget_allocated, budget_allocated) as budget_variance_pct,
  CASE
    WHEN total_cost > budget_allocated * 1.1 THEN 'Over Budget'
    WHEN total_cost > budget_allocated * 0.9 THEN 'Near Budget'
    ELSE 'Under Budget'
  END as budget_status,

  -- Data quality indicators
  CASE
    WHEN avg_allocation_confidence >= 0.9 AND avg_cost_confidence >= 0.9 THEN 'High Confidence'
    WHEN avg_allocation_confidence >= 0.7 AND avg_cost_confidence >= 0.7 THEN 'Medium Confidence'
    ELSE 'Low Confidence'
  END as data_quality_tier,

  -- Reconciliation completeness
  SAFE_DIVIDE(reconciled_cost, total_cost) as reconciliation_rate,
  SAFE_DIVIDE(disputed_cost, total_cost) as dispute_rate,

  -- Month-over-month growth
  LAG(total_cost) OVER (PARTITION BY department, user_email, platform_name ORDER BY month) as prev_month_cost,
  SAFE_DIVIDE(
    total_cost - LAG(total_cost) OVER (PARTITION BY department, user_email, platform_name ORDER BY month),
    LAG(total_cost) OVER (PARTITION BY department, user_email, platform_name ORDER BY month)
  ) as cost_growth_mom

FROM allocation_summary
ORDER BY month DESC, department, total_cost DESC;
```

---

## 🔄 MIGRATION STRATEGY

### Phase 1: Parallel System (Week 1-2)
1. **Create new tables** alongside existing ones
2. **Dual-write pipeline** - populate both old and new schemas
3. **Build new views** targeting new schema
4. **Quality validation** - compare results between systems

### Phase 2: Business Validation (Week 3-4)
1. **Dashboard migration** - point Looker to new views
2. **User acceptance testing** with finance and engineering teams
3. **Performance validation** - query performance benchmarking
4. **Data quality verification** - attribution accuracy validation

### Phase 3: Full Cutover (Week 5)
1. **Stop old pipeline** - disable writes to legacy tables
2. **Single-write mode** - only populate new schema
3. **Legacy cleanup** - archive/drop old tables after validation
4. **Documentation update** - update all technical documentation

### Rollback Plan
- Keep legacy tables for 30 days post-cutover
- Maintain dual-write capability for emergency rollback
- Automated data validation alerts for anomaly detection

---

## 🚀 IMPLEMENTATION NEXT STEPS

### Immediate Actions Required:
1. **Review & Approve** this data model design
2. **Create SQL DDL scripts** for all new tables
3. **Update pipeline code** to populate new schema
4. **Build migration scripts** for historical data
5. **Create new dashboard views** for business teams

### Success Metrics:
- **Query Performance**: < 3 seconds for all dashboard queries
- **Attribution Accuracy**: > 95% of usage/cost records properly attributed
- **Data Freshness**: < 2 hours from API to dashboard
- **User Satisfaction**: > 90% approval from finance and engineering teams

**Ready to proceed with implementation? I can create the detailed SQL DDL scripts and migration code next.**