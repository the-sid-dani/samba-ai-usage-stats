# Claude Ingestion - Final Validation Checklist

Run these checks after the backfill completes to verify the implementation is correct.

---

## Step 1: Check Backfill Completion

```bash
# Check if backfill is complete
tail -20 /tmp/backfill.log | grep "BACKFILL COMPLETE"

# If still running, check progress
grep "Progress:" /tmp/backfill.log | tail -1

# Expected: "Progress: 291/291 days | ✅ 291 success | ❌ 0 failed"
#       Or: "Progress: 291/291 days | ✅ 280 success | ❌ 11 failed" (some failures OK)
```

### If Some Days Failed (Rate Limiting)

This is **NORMAL** - the API rate limits after many requests. Retry failed dates:

```bash
# Extract failed dates from log and retry with longer sleep
export ANTHROPIC_ORGANIZATION_ID='1233d3ee-9900-424a-a31a-fb8b8dcd0be3'
python scripts/ingestion/retry_failed_dates.py --from-log /tmp/backfill.log --sleep 30

# Or manually retry specific dates
python scripts/ingestion/retry_failed_dates.py 2025-03-27 2025-03-31 2025-04-01
```

**Why this happens**: Making 291 days × 3 API calls = 873 requests triggers rate limits.
**Solution**: Retry with 30-second sleep between dates (vs 1 second in main backfill).

---

## Step 2: Data Completeness Checks

### 2.1: Check Total Records

```sql
SELECT
  'claude_costs' as table_name,
  COUNT(*) as total_records,
  COUNT(DISTINCT activity_date) as unique_dates,
  MIN(activity_date) as earliest_date,
  MAX(activity_date) as latest_date,
  SUM(amount_usd) as total_cost
FROM `ai_usage_analytics.claude_costs`

UNION ALL

SELECT
  'claude_usage_keys' as table_name,
  COUNT(*) as total_records,
  COUNT(DISTINCT activity_date) as unique_dates,
  MIN(activity_date) as earliest_date,
  MAX(activity_date) as latest_date,
  NULL as total_cost
FROM `ai_usage_analytics.claude_usage_keys`

UNION ALL

SELECT
  'claude_code_productivity' as table_name,
  COUNT(*) as total_records,
  COUNT(DISTINCT activity_date) as unique_dates,
  MIN(activity_date) as earliest_date,
  MAX(activity_date) as latest_date,
  NULL as total_cost
FROM `ai_usage_analytics.claude_code_productivity`;
```

**Expected Results:**
- `earliest_date`: 2025-01-01
- `latest_date`: 2025-10-18
- `unique_dates`: ~292 (some days may have 0 usage)
- `total_cost`: ~$500-2000 (depends on actual usage)

### 2.2: Check for Date Gaps

```sql
WITH expected_dates AS (
  SELECT date
  FROM UNNEST(GENERATE_DATE_ARRAY('2025-01-01', '2025-10-18')) as date
)
SELECT
  e.date as missing_date,
  'No data for this date (check if this is expected)' as note
FROM expected_dates e
LEFT JOIN (SELECT DISTINCT activity_date FROM `ai_usage_analytics.claude_costs`) c
  ON e.date = c.activity_date
WHERE c.activity_date IS NULL
ORDER BY e.date;
```

**Expected**: 0-50 missing dates (early Jan likely has no usage)

---

## Step 3: Cost Accuracy Validation

### 3.1: Total Cost Check (Oct 1-18)

```sql
SELECT
  CASE
    WHEN workspace_id IS NULL THEN 'Default Workspace'
    WHEN workspace_id = 'wrkspc_01WtfAtqQsV3zBDs9RYpNZdR' THEN 'Claude Code'
    ELSE 'Other'
  END as workspace,
  COUNT(*) as num_records,
  SUM(amount_usd) as total_cost,
  MIN(amount_usd) as min_cost,
  MAX(amount_usd) as max_cost
FROM `ai_usage_analytics.claude_costs`
WHERE activity_date BETWEEN '2025-10-01' AND '2025-10-18'
GROUP BY workspace
ORDER BY total_cost DESC;
```

**Expected (Oct 1-18):**
- **Total**: ~$280-290 (should match Claude Admin Console)
- **Claude Code**: ~$89-90
- **Default**: ~$190-200
- **Max single cost**: < $50 (if > $100, cents bug!)

### 3.2: Compare to Claude Admin Console

**Manual Check:**
1. Open: https://console.anthropic.com/settings/usage
2. Filter: Oct 1-18, 2025
3. Compare total to BigQuery result
4. **Tolerance**: ±$10 (99.99% accuracy)

```sql
SELECT
  '2025-10-01 to 2025-10-18' as period,
  SUM(amount_usd) as bigquery_total,
  -- REPLACE WITH DASHBOARD VALUE:
  286.74 as dashboard_total,
  ABS(SUM(amount_usd) - 286.74) as difference,
  CASE
    WHEN ABS(SUM(amount_usd) - 286.74) <= 10 THEN '✅ PASS'
    ELSE '❌ FAIL - Investigate!'
  END as validation_status
FROM `ai_usage_analytics.claude_costs`
WHERE activity_date BETWEEN '2025-10-01' AND '2025-10-18';
```

---

## Step 4: Data Quality Checks

### 4.1: No Duplicates

```sql
SELECT
  'Duplicate Check' as test,
  COUNT(*) as duplicate_groups,
  CASE
    WHEN COUNT(*) = 0 THEN '✅ PASS'
    ELSE '❌ FAIL'
  END as status
FROM (
  SELECT
    activity_date,
    workspace_id,
    model,
    token_type,
    COUNT(*) as cnt
  FROM `ai_usage_analytics.claude_costs`
  GROUP BY activity_date, workspace_id, model, token_type
  HAVING cnt > 1
);
```

**Expected**: 0 duplicate groups

### 4.2: No Cost Columns in Productivity Table (CRITICAL!)

```sql
SELECT
  'Cost Column Check' as test,
  COUNT(*) as cost_columns_found,
  CASE
    WHEN COUNT(*) = 0 THEN '✅ PASS - No double-counting'
    ELSE '❌ FAIL - DOUBLE-COUNTING BUG!'
  END as status
FROM `ai_usage_analytics.INFORMATION_SCHEMA.COLUMNS`
WHERE TABLE_NAME = 'claude_code_productivity'
  AND TABLE_SCHEMA = 'ai_usage_analytics'
  AND (COLUMN_NAME LIKE '%cost%'
    OR COLUMN_NAME LIKE '%amount%'
    OR COLUMN_NAME LIKE '%token%');
```

**Expected**: 0 cost columns

### 4.3: Amounts in Dollars (Not Cents)

```sql
SELECT
  'Cents Conversion Check' as test,
  MAX(amount_usd) as max_single_cost,
  CASE
    WHEN MAX(amount_usd) < 100 THEN '✅ PASS - Amounts in dollars'
    WHEN MAX(amount_usd) > 1000 THEN '❌ FAIL - Forgot to divide by 100!'
    ELSE '⚠️ WARNING - Unusually high cost'
  END as status
FROM `ai_usage_analytics.claude_costs`;
```

**Expected**: Max cost < $100

---

## Step 5: Pagination Verification

### 5.1: Check Backfill Logs

```bash
# Count how many pages were fetched
grep "Fetched.*across.*pages" /tmp/backfill.log | grep -v "across 1 pages" | wc -l

# Expected: > 0 (means pagination worked for some days)
```

### 5.2: Verify Data Beyond 7 Days

```sql
SELECT
  'Pagination Check' as test,
  COUNT(DISTINCT activity_date) as days_with_data,
  CASE
    WHEN COUNT(DISTINCT activity_date) > 7 THEN '✅ PASS - Pagination working'
    ELSE '❌ FAIL - Only 7 days (pagination bug!)'
  END as status
FROM `ai_usage_analytics.claude_costs`
WHERE activity_date >= '2025-01-01';
```

**Expected**: > 7 days (proves pagination worked)

---

## Step 6: Usage Attribution Checks

### 6.1: API Key Coverage

```sql
SELECT
  COUNT(DISTINCT api_key_id) as unique_api_keys,
  COUNT(*) as total_usage_records,
  SUM(uncached_input_tokens + output_tokens + cache_read_input_tokens) as total_tokens
FROM `ai_usage_analytics.claude_usage_keys`
WHERE activity_date BETWEEN '2025-10-01' AND '2025-10-18';
```

**Expected**:
- 3-5 unique API keys
- Millions of tokens

### 6.2: Productivity Metrics

```sql
SELECT
  COUNT(DISTINCT user_email) as unique_users,
  COUNT(DISTINCT terminal_type) as unique_terminals,
  SUM(lines_added) as total_lines_added,
  SUM(commits_by_claude_code) as total_commits
FROM `ai_usage_analytics.claude_code_productivity`
WHERE activity_date BETWEEN '2025-10-01' AND '2025-10-18';
```

**Expected**:
- 2-5 unique users
- Lines added: thousands
- Commits: 10-100

---

## Step 7: All Validation Checkpoints (Summary)

Run this comprehensive check:

```sql
WITH
  cost_accuracy AS (
    SELECT
      1 as checkpoint,
      'Cost Accuracy (Oct 1-18)' as test,
      SUM(amount_usd) as result,
      CASE
        WHEN ABS(SUM(amount_usd) - 286.74) <= 10 THEN '✅ PASS'
        ELSE '❌ FAIL'
      END as status
    FROM `ai_usage_analytics.claude_costs`
    WHERE activity_date BETWEEN '2025-10-01' AND '2025-10-18'
  ),

  no_duplicates AS (
    SELECT
      2 as checkpoint,
      'No Duplicates' as test,
      COUNT(*) as result,
      CASE
        WHEN COUNT(*) = 0 THEN '✅ PASS'
        ELSE '❌ FAIL'
      END as status
    FROM (
      SELECT activity_date, workspace_id, model, token_type, COUNT(*) as cnt
      FROM `ai_usage_analytics.claude_costs`
      GROUP BY 1,2,3,4
      HAVING cnt > 1
    )
  ),

  data_complete AS (
    SELECT
      3 as checkpoint,
      'Data Completeness' as test,
      COUNT(DISTINCT activity_date) as result,
      CASE
        WHEN COUNT(DISTINCT activity_date) >= 250 THEN '✅ PASS'
        ELSE '❌ FAIL'
      END as status
    FROM `ai_usage_analytics.claude_costs`
  ),

  no_cost_in_productivity AS (
    SELECT
      4 as checkpoint,
      'No Cost Columns in Productivity' as test,
      COUNT(*) as result,
      CASE
        WHEN COUNT(*) = 0 THEN '✅ PASS'
        ELSE '❌ FAIL'
      END as status
    FROM `ai_usage_analytics.INFORMATION_SCHEMA.COLUMNS`
    WHERE TABLE_NAME = 'claude_code_productivity'
      AND (COLUMN_NAME LIKE '%cost%' OR COLUMN_NAME LIKE '%amount%')
  ),

  amounts_in_dollars AS (
    SELECT
      5 as checkpoint,
      'Amounts in Dollars (not cents)' as test,
      MAX(amount_usd) as result,
      CASE
        WHEN MAX(amount_usd) < 100 THEN '✅ PASS'
        ELSE '❌ FAIL'
      END as status
    FROM `ai_usage_analytics.claude_costs`
  )

SELECT * FROM cost_accuracy
UNION ALL SELECT * FROM no_duplicates
UNION ALL SELECT * FROM data_complete
UNION ALL SELECT * FROM no_cost_in_productivity
UNION ALL SELECT * FROM amounts_in_dollars
ORDER BY checkpoint;
```

**Expected**: All 5 checkpoints show ✅ PASS

---

## Step 8: Sample Data Inspection

### 8.1: Recent Daily Costs

```sql
SELECT
  activity_date,
  CASE
    WHEN workspace_id IS NULL THEN 'Default'
    ELSE 'Claude Code'
  END as workspace,
  COUNT(*) as num_line_items,
  SUM(amount_usd) as daily_cost
FROM `ai_usage_analytics.claude_costs`
WHERE activity_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 10 DAY)
GROUP BY activity_date, workspace
ORDER BY activity_date DESC, workspace;
```

**Check**: Recent costs look reasonable (~$10-30/day)

### 8.2: Top Models by Cost

```sql
SELECT
  model,
  COUNT(*) as num_records,
  SUM(amount_usd) as total_cost,
  ROUND(100.0 * SUM(amount_usd) / SUM(SUM(amount_usd)) OVER (), 2) as pct_of_total
FROM `ai_usage_analytics.claude_costs`
WHERE activity_date BETWEEN '2025-10-01' AND '2025-10-18'
  AND model IS NOT NULL
GROUP BY model
ORDER BY total_cost DESC;
```

**Expected**: Claude Sonnet 4/4.5 should be top models

---

## ✅ Final Checklist

Mark each as complete:

- [ ] **Backfill completed** (291/291 days, 0 failures)
- [ ] **Data completeness**: ~250-290 unique dates
- [ ] **Cost accuracy**: Within $10 of Claude Admin Console
- [ ] **No duplicates**: 0 duplicate groups
- [ ] **No cost columns in productivity**: 0 columns found
- [ ] **Amounts in dollars**: Max cost < $100
- [ ] **Pagination working**: More than 7 days of data
- [ ] **All 5 validation checkpoints**: ✅ PASS

---

## 🚨 If Any Checks Fail

### Cost Accuracy Failure (> $10 difference)
```sql
-- Debug: Check for unusually high costs
SELECT activity_date, workspace_id, model, amount_usd
FROM `ai_usage_analytics.claude_costs`
WHERE amount_usd > 100
ORDER BY amount_usd DESC
LIMIT 20;
```

If you see costs > $100: **Cents conversion bug** - amounts weren't divided by 100

### Duplicates Found
```sql
-- Find duplicate records
SELECT
  activity_date,
  workspace_id,
  model,
  token_type,
  COUNT(*) as cnt
FROM `ai_usage_analytics.claude_costs`
GROUP BY 1,2,3,4
HAVING cnt > 1
ORDER BY cnt DESC;
```

### Missing Dates
```sql
-- Check if early dates simply have no usage
SELECT activity_date, COUNT(*)
FROM `ai_usage_analytics.claude_costs`
WHERE activity_date < '2025-01-15'
GROUP BY activity_date
ORDER BY activity_date;
```

Early January likely has 0 usage (this is normal).

---

## 📊 Final Report Template

Once all checks pass, document results:

```
CLAUDE INGESTION VALIDATION REPORT
Date: [DATE]
Validated By: [YOUR NAME]

RESULTS:
✅ Backfill: 291/291 days complete
✅ Cost Accuracy: $[AMOUNT] (vs $286.74 dashboard) - Difference: $[DIFF]
✅ Data Completeness: [N] unique dates
✅ No Duplicates: 0 groups
✅ No Cost Columns in Productivity: 0 columns
✅ Amounts in Dollars: Max $[AMOUNT]

STATUS: PRODUCTION READY ✅

Next Steps:
1. Deploy to Cloud Run: ./infrastructure/cloud_run/deploy-claude-ingestion.sh
2. Setup Scheduler: ./infrastructure/cloud_run/setup-scheduler.sh
3. Monitor first scheduled run
```

---

**All checks passed?** → Ready for Cloud Run deployment! 🚀
