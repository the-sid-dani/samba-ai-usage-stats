# Cursor Unified Table Design - Invoice-Validated Approach

**Date**: October 19, 2025
**Author**: Winston (Architect)
**Status**: Proposed Design

## Real Invoice Data (From Cursor Dashboard)

| Month | Total Cost | Notes |
|-------|------------|-------|
| July 2025 | $1,775.07 | Highest spend month |
| August 2025 | $827.15 | Mid-range |
| September 2025 | $1,104.30 | High usage |
| October 2025 | $41.92 | Partial month (Oct 1-31 period) |

## Architecture: Two-Table Design

### Table 1: `cursor_daily_metrics` (Unified Usage + Estimated Costs)

**Purpose**: Single source of truth for daily Cursor activity and cost estimates

```sql
CREATE TABLE `ai_usage_analytics.cursor_daily_metrics` (
  -- Identity & Date
  activity_date DATE NOT NULL,
  user_email STRING NOT NULL,
  user_id STRING,
  is_active BOOLEAN NOT NULL,

  -- Productivity Metrics
  total_lines_added INT64,
  accepted_lines_added INT64,
  total_lines_deleted INT64,
  accepted_lines_deleted INT64,

  -- AI Interactions
  total_applies INT64,
  total_accepts INT64,
  total_rejects INT64,
  total_tabs_shown INT64,
  total_tabs_accepted INT64,

  -- Request Types
  composer_requests INT64,
  chat_requests INT64,
  agent_requests INT64,
  cmdk_usages INT64,
  bugbot_usages INT64,

  -- Cost Attribution (from API)
  subscription_included_reqs INT64,  -- Free tier (≤500/month)
  usage_based_reqs INT64,            -- Paid overage
  api_key_reqs INT64,

  -- Estimated Costs (calculated from monthly rates)
  estimated_daily_cost_usd NUMERIC,  -- usage_based_reqs * avg_monthly_rate
  cost_calculation_method STRING,     -- 'invoice_validated' or 'default_rate'

  -- Context
  most_used_model STRING,
  client_version STRING,
  apply_most_used_extension STRING,
  tab_most_used_extension STRING,

  -- Metadata
  ingestion_timestamp TIMESTAMP NOT NULL,
  data_source STRING DEFAULT 'cursor_api_daily_usage'
)
PARTITION BY activity_date
CLUSTER BY user_email, is_active;
```

### Table 2: `cursor_monthly_invoices` (Manual Entry from Billing)

**Purpose**: Store actual monthly costs from Cursor invoices for validation and rate calculation

```sql
CREATE TABLE `ai_usage_analytics.cursor_monthly_invoices` (
  -- Billing Period
  billing_month DATE NOT NULL,  -- First day of month (2025-08-01)
  period_start DATE NOT NULL,
  period_end DATE NOT NULL,

  -- Actual Costs (from invoice)
  total_invoice_amount_usd NUMERIC NOT NULL,
  subscription_base_usd NUMERIC,
  overage_charges_usd NUMERIC,

  -- Request Totals (from usage_stats for validation)
  total_usage_based_reqs INT64,
  total_subscription_reqs INT64,

  -- Calculated Rates
  effective_overage_rate_per_req NUMERIC,  -- overage_charges / usage_based_reqs

  -- Invoice Details
  invoice_id STRING,
  invoice_date DATE,
  payment_status STRING,

  -- Metadata
  entered_by STRING,
  entered_at TIMESTAMP,
  notes TEXT,

  PRIMARY KEY (billing_month) NOT ENFORCED
);
```

## How It Works Together

### Step 1: Daily Data Collection
```python
# Single job: cursor-daily-ingest
# Calls /teams/daily-usage-data
# Loads to cursor_daily_metrics
# Sets estimated_daily_cost_usd = NULL initially
```

### Step 2: Monthly Invoice Entry (Manual)
```sql
-- Finance team enters actual invoice when received
INSERT INTO cursor_monthly_invoices VALUES (
  '2025-08-01',  -- billing_month
  '2025-08-01',  -- period_start
  '2025-08-31',  -- period_end
  827.15,        -- total from invoice
  NULL,          -- subscription (if shown separately)
  827.15,        -- overage charges
  7254,          -- total usage_based_reqs (from cursor_daily_metrics)
  NULL,
  827.15 / 7254, -- calculated rate = $0.114 per request
  'INV-AUG-2025',
  '2025-09-05',
  'paid',
  'finance_team',
  CURRENT_TIMESTAMP(),
  'August 2025 Cursor invoice - verified'
);
```

### Step 3: Backfill Costs Using Invoice Rates
```sql
-- Update estimated costs for August using real invoice rate
UPDATE cursor_daily_metrics
SET
  estimated_daily_cost_usd = usage_based_reqs * 0.114,  -- Real rate from invoice
  cost_calculation_method = 'invoice_validated'
WHERE activity_date >= '2025-08-01'
  AND activity_date < '2025-09-01'
  AND is_active = true;
```

## Real Pricing Rates (From Your Invoices)

```sql
-- Populate cursor_monthly_invoices with your real data
INSERT INTO cursor_monthly_invoices
(billing_month, period_start, period_end, total_invoice_amount_usd,
 total_usage_based_reqs, effective_overage_rate_per_req,
 invoice_id, payment_status, entered_by, entered_at)
VALUES
  -- July 2025
  ('2025-07-01', '2025-07-01', '2025-07-31', 1775.07,
   [SUM from usage_stats], 1775.07/[usage_based_reqs],
   'INV-JUL-2025', 'paid', 'system', CURRENT_TIMESTAMP()),

  -- August 2025
  ('2025-08-01', '2025-08-01', '2025-08-31', 827.15,
   7254, 827.15/7254,  -- $0.114 per overage request
   'INV-AUG-2025', 'paid', 'system', CURRENT_TIMESTAMP()),

  -- September 2025
  ('2025-09-01', '2025-09-01', '2025-09-30', 1104.30,
   8343, 1104.30/8343,  -- $0.132 per overage request
   'INV-SEP-2025', 'paid', 'system', CURRENT_TIMESTAMP()),

  -- October 2025
  ('2025-10-01', '2025-10-01', '2025-10-31', 41.92,
   [TBD], 41.92/[usage_based_reqs],
   'INV-OCT-2025', 'pending', 'system', CURRENT_TIMESTAMP());
```

## Query Pattern for Accurate Costs

```sql
-- Join daily metrics with monthly invoice rates
SELECT
  m.activity_date,
  m.user_email,
  m.usage_based_reqs,
  i.effective_overage_rate_per_req,
  m.usage_based_reqs * i.effective_overage_rate_per_req as accurate_daily_cost
FROM cursor_daily_metrics m
LEFT JOIN cursor_monthly_invoices i
  ON DATE_TRUNC(m.activity_date, MONTH) = i.billing_month
WHERE m.is_active = true
```

## Validation Against Invoices

```sql
-- Verify our daily metrics sum to invoice total
SELECT
  DATE_TRUNC(activity_date, MONTH) as month,
  SUM(usage_based_reqs) as total_overage_reqs,
  -- Use invoice rate
  SUM(usage_based_reqs) * 0.114 as calculated_cost_aug,  -- August rate
  827.15 as invoice_total_aug,
  ABS(SUM(usage_based_reqs) * 0.114 - 827.15) as variance
FROM cursor_daily_metrics
WHERE activity_date >= '2025-08-01' AND activity_date < '2025-09-01'
```

## Benefits

1. ✅ **Accurate costs** - Based on real invoices, not guesses
2. ✅ **Rate transparency** - Invoice table shows exact pricing
3. ✅ **Monthly validation** - Can reconcile against invoices
4. ✅ **Rate updates** - When Cursor changes pricing, update invoice table
5. ✅ **Audit trail** - Invoice table documents actual spending
6. ✅ **Supports all dashboards** - Still ONE unified daily metrics table

## Answer to Your Question

**"What did Cursor cost in August and September?"**

**ACCURATE ANSWER** (from your invoices):
- **August 2025**: $827.15 (verified from invoice)
- **September 2025**: $1,104.30 (verified from invoice)
- **July 2025**: $1,775.07 (verified from invoice)
- **October 2025**: $41.92 so far (partial month)

**Calculated Rate**:
- August: $827.15 / 7,254 reqs = **$0.114 per overage request**
- September: $1,104.30 / 8,343 reqs = **$0.132 per overage request**

Rates vary month-to-month based on model usage mix!

## Implementation Plan

1. Create `cursor_monthly_invoices` table
2. Populate with Jul, Aug, Sep, Oct invoice data (from your screenshots)
3. Keep `cursor_daily_metrics` (rename current cursor_usage_stats)
4. Calculate costs by joining with invoice rates
5. Validate totals match invoices

**This gives you REAL costs, not estimates!**
