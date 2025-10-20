# Cursor Data Pipeline Redesign - Invoice-Accurate Costs

**Archon Project ID**: e38ec648-5ca1-469e-8221-344ef1644d6e
**Date**: October 19, 2025
**Author**: Winston (Architect)
**Status**: Ready for Execution

## Executive Summary

Redesign Cursor cost tracking to use **REAL invoice data** instead of estimates, providing 100% accurate per-user daily spending for finance dashboards.

**Current Problem**:
- cursor_spending table had incorrect cumulative data
- Costs were being double-counted
- Historical costs were estimates ($0.10/req guess)

**Solution**:
- Use real monthly invoice totals
- Calculate historical daily costs from invoice rates
- Capture daily `/teams/spend` snapshots for current cycle
- Calculate deltas for real-time daily costs

---

## Current State

### ✅ **What We Have (Good Quality)**:
| Table | Records | Date Range | Quality |
|-------|---------|------------|---------|
| cursor_usage_stats | 10,366 | May 20 → Oct 17 | ⭐⭐⭐ Perfect |
| cursor_monthly_invoices | 5 | Jun-Oct 2025 | ⭐⭐⭐ Real invoices |

### ✅ **Real Invoice Data** (From Cursor Dashboard):
| Month | Invoice Total | Overage Requests | Rate/Req |
|-------|---------------|------------------|----------|
| June 2025 | $1,048.90 | 11,876 | $0.088 |
| July 2025 | $1,775.07 | 16,753 | $0.106 |
| August 2025 | $827.15 | 7,254 | $0.114 |
| September 2025 | $1,104.30 | 8,343 | $0.132 |
| October 2025 | $41.92 | 801 | $0.052 |

**Total Jun-Oct**: $4,797.34

---

## Tasks (Priority Order)

### **PHASE 1: Fix Historical Data (Tasks 1-4)**

#### Task 1: Rename Table
**What**: `cursor_usage_stats` → `cursor_daily_metrics`
**Why**: Table will contain usage + cost data
**Risk**: None (simple rename)
**Archon**: 94cbb300-98e1-4904-b2c7-2392ccbe220b

#### Task 2: Add Cost Column
**What**: Add `daily_spend_usd NUMERIC` column
**Why**: Store calculated daily spending
**Risk**: None (adding nullable column)
**Archon**: 15db8c1c-c844-49e7-929e-c8cc9970691e

#### Task 3: Backfill Historical Costs
**What**: Calculate daily_spend_usd for 10,366 rows
**Formula**: `usage_based_reqs × monthly_invoice_rate`
**Risk**: ⚠️ **HIGH** - Updates 10,366 rows
**Validation Required**: Sums must match invoices EXACTLY
**Archon**: 1bfcb63c-c214-4f3b-9e6c-ef9b8dd2dd11

**QUESTION**: Proceed with 10,366 row update?

#### Task 4: Validate Against Invoices
**What**: Verify monthly sums = invoice totals
**Pass**: All variances ≤ $0.01
**Fail**: STOP and investigate
**Archon**: c0be488c-4bfb-4028-95c0-cb8987a645d9

---

### **PHASE 2: Current/Future Ingestion (Tasks 5-7)**

#### Task 5: Update Ingestion Job
**What**: Modify job to call BOTH endpoints:
- `/teams/daily-usage-data` (usage metrics)
- `/teams/spend` (current cycle cumulative)

**Why**: Get real spend data going forward
**Archon**: 682282e9-def1-445a-a5ce-c5a556161ba7

#### Task 6: Implement Delta Calculation
**What**: Calculate daily spend from cumulative snapshots
**Formula**: `today_cumulative - yesterday_cumulative`
**Why**: Convert cumulative to daily amounts
**Archon**: 4544c342-8283-4765-892c-dc6bb2b796b2

#### Task 7: Test with Last 2 Days
**What**: Test with Oct 18-20 data
**Why**: Verify delta logic works before deploying
**Pass**: Costs > $0, no negatives, 76 users/day
**Archon**: 46013dd5-c825-4864-89c7-3563d32c7965

---

## Architecture

### **Final Schema**:
```
cursor_daily_metrics (unified table)
├── All existing usage columns (10,366 rows)
├── NEW: daily_spend_usd (calculated for historical, real deltas for current)
└── ONE table, ONE job, clean design

cursor_monthly_invoices (reference table)
├── 5 rows (Jun-Oct invoices)
├── Used for: Historical rate calculation
└── Updated manually each month
```

### **Data Flow**:
```
Historical (Jun-Oct 17):
  usage_based_reqs × invoice_rate → daily_spend_usd

Current Cycle (Oct 18+):
  /teams/spend cumulative → calculate delta → daily_spend_usd

Future (Nov+):
  Same as current - daily deltas from /teams/spend
```

---

## Critical Validation Points

### **After Task 3 (Backfill)**:
```sql
-- MUST run this validation
SELECT
  FORMAT_DATE('%B', activity_date) as month,
  ROUND(SUM(daily_spend_usd), 2) as calculated,
  i.total_invoice_amount_usd as invoice,
  ROUND(ABS(SUM(daily_spend_usd) - i.total_invoice_amount_usd), 2) as variance
FROM cursor_daily_metrics m
JOIN cursor_monthly_invoices i
  ON DATE_TRUNC(m.activity_date, MONTH) = i.billing_month
GROUP BY month, i.total_invoice_amount_usd
ORDER BY month;
```

**Expected**: All variances = $0.00

**If variance > $0.01**: STOP, investigate before continuing

---

## Questions Before Execution

### **Task 3 Confirmation Needed**:
1. **Confirm**: Update 10,366 rows with calculated costs?
2. **Confirm**: Use invoice rates from cursor_monthly_invoices table?
3. **Confirm**: Only update where is_active = true?

### **Task 5 Confirmation Needed**:
1. **Where is current ingestion script?** (Cloud Run container? Local?)
2. **Can you provide script location?** Need to modify it

### **Task 7 Confirmation Needed**:
1. **Test on production table or create test copy?**
2. **Acceptable to test with real Oct data?**

---

## Expected Outcomes

### **After Completion**:
- ✅ ONE table: `cursor_daily_metrics` (10,366+ rows)
- ✅ Real historical costs (Jun-Oct) matching invoices
- ✅ Real current cycle costs from daily deltas
- ✅ ONE job fetching usage + spend
- ✅ 100% accurate costs for dashboards

### **Monthly Totals** (Accurate):
- June: $1,048.90
- July: $1,775.07
- August: $827.15
- September: $1,104.30
- October: $41.92 (partial)

---

## Risk Assessment

| Task | Risk Level | Mitigation |
|------|------------|------------|
| 1-2 | Low | Schema changes only |
| 3 | **HIGH** | Validate before/after, have rollback plan |
| 4 | Low | Read-only validation |
| 5-6 | Medium | Test before deploy |
| 7 | Low | Testing phase |

---

**Ready to proceed? Please confirm answers to the questions above before I execute Task 3 (the 10,366 row update).**
