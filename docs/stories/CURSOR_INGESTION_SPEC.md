# Cursor Ingestion Job Specification - Tasks 5-7

**Archon Project**: e38ec648-5ca1-469e-8221-344ef1644d6e
**Tasks**: 5, 6, 7
**Status**: Ready for Implementation

## Current State After Tasks 1-4

✅ **cursor_daily_metrics** table ready:
- 10,366 rows (May 20 → Oct 17)
- Historical costs backfilled with 100% accuracy
- `daily_spend_usd` column populated for active users

✅ **cursor_monthly_invoices** table ready:
- 5 months of real invoice data
- Accurate per-request rates calculated

---

## Task 5: Update Ingestion Job Specification

### **Current Job** (cursor-usage-ingest):
**Endpoint**: `/teams/daily-usage-data` only
**Frequency**: Daily at 6:30 AM PT
**Target**: cursor_daily_metrics (formerly cursor_usage_stats)

### **Updated Job Requirements**:

**Call TWO endpoints**:
1. `/teams/daily-usage-data` (existing) - Usage metrics
2. `/teams/spend` (NEW) - Current cycle spending

**Pseudo-code**:
```python
#!/usr/bin/env python3
"""
Updated Cursor daily ingestion - fetches usage + spend
"""

def main():
    target_date = yesterday()

    # STEP 1: Fetch usage metrics (EXISTING LOGIC - KEEP AS-IS)
    usage_data = cursor_client.get_daily_usage_data(target_date)

    # Transform and load to cursor_daily_metrics
    # Populates all 26 existing columns
    load_usage_metrics(usage_data)

    # STEP 2: NEW - Fetch current cycle spend snapshot
    spend_data = cursor_client.get_spend()
    # Returns: teamMemberSpend, subscriptionCycleStart

    # STEP 3: NEW - Calculate and store daily spend deltas
    billing_cycle_start = spend_data['subscriptionCycleStart']

    for member in spend_data['teamMemberSpend']:
        user_email = member['email']
        current_cumulative_cents = member['spendCents'] + member.get('includedSpendCents', 0)

        # Get yesterday's cumulative for this user in this cycle
        yesterday_cumulative = get_previous_cumulative_spend(
            user_email,
            target_date - timedelta(days=1),
            billing_cycle_start
        )

        # Calculate delta
        daily_delta_cents = current_cumulative_cents - (yesterday_cumulative or 0)
        daily_delta_usd = daily_delta_cents / 100

        # Update today's row with real daily spend
        update_daily_spend(target_date, user_email, daily_delta_usd)
```

### **New API Client Method Needed**:

```python
class CursorAdminClient:
    # ... existing methods ...

    def get_spend(self, page=1, page_size=100):
        """
        Fetch current billing cycle spending.

        Endpoint: POST /teams/spend
        Returns: {
            teamMemberSpend: [{
                email: str,
                spendCents: int,  # Overage charges
                includedSpendCents: int,  # Free tier usage value
                fastPremiumRequests: int,
                ...
            }],
            subscriptionCycleStart: int,  # Timestamp in ms
            totalMembers: int,
            totalPages: int
        }
        """
        url = f"{self.base_url}/teams/spend"
        payload = {"page": page, "pageSize": page_size}
        response = self._request_with_retry("POST", url, json=payload)
        return response
```

---

## Task 6: Delta Calculation Implementation

### **The Delta Logic**:

**Problem**: `/teams/spend` returns **cumulative** spend since cycle start

**Solution**: Subtract previous day's cumulative from today's cumulative

**Example**:
```
Billing cycle starts: Oct 3, 2025

Oct 18: User A cumulative = $50
Oct 19: User A cumulative = $57
Oct 20: User A cumulative = $57

Daily costs:
- Oct 18: $50 - $0 = $50 (first snapshot in our data)
- Oct 19: $57 - $50 = $7 (actual daily spend!)
- Oct 20: $57 - $57 = $0 (no additional spend)
```

### **Implementation**:

```python
def get_previous_cumulative_spend(user_email, previous_date, billing_cycle_start):
    """
    Get the most recent cumulative spend for a user in the current cycle.
    """
    query = '''
        SELECT
            SUM(daily_spend_usd) as cumulative_in_cycle
        FROM `ai_usage_analytics.cursor_daily_metrics`
        WHERE user_email = @user_email
          AND activity_date < @current_date
          AND activity_date >= DATE(@billing_cycle_start)
        GROUP BY user_email
    '''

    result = bq_client.query(query, {
        'user_email': user_email,
        'current_date': previous_date,
        'billing_cycle_start': billing_cycle_start
    }).result()

    # Return cumulative or 0 if first day in cycle
    return next(iter(result), {}).get('cumulative_in_cycle', 0)

def calculate_daily_delta(user_email, current_date, current_cumulative_usd, billing_cycle_start):
    """
    Calculate today's actual spending from cumulative snapshots.
    """
    # Get sum of all previous daily_spend_usd in this cycle
    previous_cumulative = get_previous_cumulative_spend(
        user_email,
        current_date,
        billing_cycle_start
    )

    # Delta = today's total - previous total
    daily_delta = current_cumulative_usd - previous_cumulative

    # Validation
    if daily_delta < 0:
        logger.warning(f"Negative delta for {user_email} on {current_date}: ${daily_delta}")
        return 0  # Shouldn't happen, but handle gracefully

    return daily_delta
```

### **Critical Edge Cases**:

1. **First day we capture spend** (e.g., Oct 18):
   - No previous snapshot exists
   - Delta = full cumulative amount
   - Expected: Higher value (accumulation since cycle start Oct 3)

2. **Billing cycle changes** (e.g., Nov 1):
   - New cycle starts
   - Previous cumulative resets to $0
   - Delta = new cycle's first day spend

3. **User not in yesterday's data**:
   - Previous cumulative = 0
   - Delta = today's full cumulative

---

## Task 7: Test Plan

### **Test with October 18-20 Data**:

**Step 1**: Manually call `/teams/spend` to get current snapshot
```bash
curl -X POST https://api.cursor.com/teams/spend \
  -u "$CURSOR_API_KEY:" \
  -H "Content-Type: application/json" \
  -d '{"page": 1, "pageSize": 100}'
```

**Step 2**: Simulate delta calculation for 2-3 sample users

**Step 3**: Compare calculated deltas with expected values

**Expected Test Results**:
- Oct 18: Should show ~$721 total (first snapshot, so delta = cumulative)
- Oct 20: Should show ~$0-20 total (little change from Oct 18)
- No negative values
- 76 users captured both days

**Validation Query**:
```sql
SELECT
  activity_date,
  COUNT(DISTINCT user_email) as users,
  SUM(daily_spend_usd) as daily_total,
  MIN(daily_spend_usd) as min_spend,
  MAX(daily_spend_usd) as max_spend
FROM cursor_daily_metrics
WHERE activity_date IN ('2025-10-18', '2025-10-20')
  AND daily_spend_usd IS NOT NULL
GROUP BY activity_date
ORDER BY activity_date;
```

---

## Implementation Files Needed

### **New Files to Create**:
1. `src/ingestion/cursor_client.py` - Add `get_spend()` method
2. `src/ingestion/ingest_cursor_daily.py` - Combined usage + spend ingestion
3. `Dockerfile` - For Cloud Run deployment
4. `tests/test_cursor_spend_delta.py` - Unit tests for delta calculation

### **Configuration**:
```yaml
# Cloud Run Job Environment Variables
CURSOR_SECRET_PROJECT: ai-workflows-459123
CURSOR_SECRET_ID: cursor-api-key
CURSOR_SECRET_VERSION: latest
TARGET_GCP_PROJECT: ai-workflows-459123
TARGET_BQ_DATASET: ai_usage_analytics
TARGET_TABLE: cursor_daily_metrics
LOG_LEVEL: INFO
```

---

## Next Steps

**Since we don't have the ingestion script locally**, we have two options:

**Option A**: Retrieve existing script from Cloud Run container
**Option B**: Write new clean script from scratch

**QUESTION**: Would you like me to write a clean new ingestion script that implements this specification, or should we try to retrieve the existing one from Cloud Run?

---

**Tasks 1-4 are complete and committed. Ready for your decision on Tasks 5-7!**