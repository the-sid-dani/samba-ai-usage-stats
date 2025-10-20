# Cursor Cost Data Architecture - Correct Approach

**Date**: October 19, 2025
**Author**: Winston (Architect)
**Status**: Design Document

## Problem Statement

Initial implementation incorrectly treated Cursor spending data, leading to:
- ✗ Double-counting of cumulative billing cycle totals
- ✗ Fake "estimates" stored as real data
- ✗ Confusion between usage metrics and actual costs
- ✗ Inability to answer "What did Cursor cost in August?"

## Root Cause

**Cursor API Data Model Mismatch**:

| API Endpoint | Data Type | Coverage | Granularity |
|--------------|-----------|----------|-------------|
| `/teams/daily-usage-data` | Usage metrics (requests, lines of code) | 90 days historical | Daily |
| `/teams/spend` | **Cumulative cycle total** | Current billing cycle ONLY | Billing cycle snapshot |

**The Fundamental Issue**: You CANNOT get historical daily spending from Cursor API. It doesn't exist.

## What We Actually Have

### ✅ **cursor_usage_stats** (Complete & Accurate)
**Source**: `/teams/daily-usage-data` API
**Coverage**: May 20, 2025 → Present
**Records**: 10,366
**Granularity**: Daily per user

**Key Fields**:
- `usage_based_reqs` - Real overage request counts from API
- `subscription_included_reqs` - Real free-tier request counts
- All productivity metrics (lines added, accepted, etc.)

### ⚠️ **cursor_spending** (Cumulative Snapshots Only)
**Source**: `/teams/spend` API
**Coverage**: Current billing cycle only (Oct 3 → Present)
**Records**: 152 (76 users × 2 snapshots)
**Granularity**: Cumulative cycle totals

**Key Fields**:
- `total_spend_cents` - CUMULATIVE spend since cycle start
- NOT daily spending, NOT historical

## Correct Architecture

### **Recommended Approach: Separate Usage from Billing**

```
cursor_usage_stats (Daily Usage Metrics)
├── Source: /teams/daily-usage-data
├── Coverage: Historical (90 days rolling)
├── Purpose: Track daily activity, requests, productivity
└── Cost Proxy: usage_based_reqs × [pricing rate from invoice]

cursor_billing_cycles (Cycle Summary)
├── Source: /teams/spend (periodic snapshots)
├── Coverage: Current cycle + manual historical entry
├── Purpose: Actual verified spending per billing period
└── One row per billing cycle with cycle_start, cycle_end, total_spend
```

### **For Cost Analysis**

**Current Cycle** (has real API data):
```sql
-- Get latest snapshot for current cycle
SELECT
  MAX(snapshot_date) as as_of_date,
  billing_cycle_start as cycle_start,
  SUM(total_spend_cents)/100 as total_cycle_spend_usd
FROM cursor_spending
WHERE user_id NOT LIKE 'user_backfill_%'
GROUP BY billing_cycle_start
```

**Historical Periods** (no API data available):
```sql
-- Use usage_based_reqs as proxy
SELECT
  DATE_TRUNC(activity_date, MONTH) as month,
  SUM(usage_based_reqs) as overage_requests,
  SUM(usage_based_reqs) * 0.10 as estimated_cost_usd,  -- Update 0.10 with real rate from invoice
  'ESTIMATED from usage data' as data_quality_flag
FROM cursor_usage_stats
WHERE activity_date < [current_cycle_start]
GROUP BY month
```

## What to Tell Finance Team

**For August & September 2025**:

"Cursor API does not provide historical billing data. We have two data points:

1. **Usage Metrics** (from API):
   - August: 7,254 overage requests (real)
   - September: 8,343 overage requests (real)

2. **Estimated Cost** (calculated):
   - Multiply requests × Cursor's overage rate
   - Rate unknown - need invoice to verify
   - Estimate at $0.10/req: Aug ~$725, Sep ~$834

3. **Current Cycle** (real from API):
   - Oct 3-20: $720.63 actual spend
   - 17 days = $42/day average"

## View Fix Required

**File**: `vw_combined_daily_costs`

**Current (WRONG)**:
```sql
SELECT
  snapshot_date AS cost_date,
  'cursor' AS provider,
  SAFE_DIVIDE(CAST(total_spend_cents AS NUMERIC), 100) AS amount_usd
FROM cursor_spending
-- This sums cumulative snapshots! Double-counting!
```

**Corrected Option A** (Latest snapshot only):
```sql
SELECT
  snapshot_date AS cost_date,
  'cursor' AS provider,
  SAFE_DIVIDE(CAST(total_spend_cents AS NUMERIC), 100) AS amount_usd
FROM cursor_spending
WHERE (user_email, snapshot_date) IN (
  SELECT user_email, MAX(snapshot_date)
  FROM cursor_spending
  GROUP BY user_email, billing_cycle_start
)
```

**Corrected Option B** (Daily deltas):
```sql
WITH cursor_deltas AS (
  SELECT
    snapshot_date,
    user_email,
    total_spend_cents - COALESCE(
      LAG(total_spend_cents) OVER (
        PARTITION BY user_email, billing_cycle_start
        ORDER BY snapshot_date
      ), 0
    ) AS daily_spend_cents
  FROM cursor_spending
)
SELECT
  snapshot_date AS cost_date,
  'cursor' AS provider,
  SAFE_DIVIDE(CAST(daily_spend_cents AS NUMERIC), 100) AS amount_usd
FROM cursor_deltas
WHERE daily_spend_cents > 0  -- Only positive deltas
```

**Corrected Option C** (Don't include cursor in combined costs view):
```sql
-- Remove cursor_spending from vw_combined_daily_costs entirely
-- Show it separately as "billing cycle totals" not "daily costs"
-- OR use usage_based_reqs as cost proxy
```

## Recommended Action Plan

### Immediate (Today):
1. ✅ Delete fake backfilled data (DONE)
2. ✅ Document API limitations (this file)
3. ⏳ Fix `vw_combined_daily_costs` view to handle cumulative data correctly
4. ⏳ Update dashboards to show Cursor separately or with data quality flags

### Short-term (This Week):
1. Get actual Cursor invoice for one month
2. Calculate real overage rate ($/request)
3. Update estimates with correct pricing
4. Validate against invoice totals

### Long-term (Ongoing):
1. Track billing cycle changes (when new cycles start)
2. Snapshot `/teams/spend` at cycle end for historical record
3. Build separate "Cursor Billing Cycles" dashboard
4. Accept that daily Cursor costs aren't available historically

## Key Takeaways

1. **Cursor API Limitation**: No historical billing data via API
2. **What We Have**: Request counts (accurate) and current cycle totals (cumulative)
3. **What We Don't Have**: Historical daily spending in dollars
4. **Best Solution**: Use usage_based_reqs as proxy + validate against invoices
5. **Don't Fake Data**: Label estimates clearly, don't mix with real spending data

## Files Requiring Updates

- [ ] `sql/views/vw_combined_daily_costs.sql` - Fix cursor_spending logic
- [ ] `docs/stories/2.7.backfill-cursor-spending-historical-data.md` - Update with corrected approach
- [ ] Dashboard SQL queries - Add data quality indicators for Cursor estimates
- [ ] Architecture docs - Document Cursor billing cycle model

---

**Bottom Line**: We need to accept Cursor's API limitations and design around them properly, not try to fake data that doesn't exist.
