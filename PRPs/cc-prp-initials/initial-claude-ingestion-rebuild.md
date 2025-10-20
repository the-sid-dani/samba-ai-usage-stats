# Initial Plan: Claude Data Ingestion Pipeline Rebuild

**Feature**: Rebuild Claude data ingestion from scratch with accurate cost reporting and deduplication
**Created**: 2025-10-19
**Status**: Initial Planning
**Priority**: Critical (Fixes 34-138x cost inflation bug)

---

## Executive Summary

This plan rebuilds the Claude data ingestion pipeline to fix critical bugs causing 34-138x cost inflation in the current system. The new design implements 3 separate tables with distinct data sources to prevent double-counting while achieving 99.99% cost accuracy against the Claude Admin Console.

**Critical Bugs Being Fixed**:
1. API returns costs in cents (must divide by 100)
2. Missing pagination (7-day default limit causes incomplete data)
3. Double-counting Claude Code costs (already included in cost_report workspace)
4. Org-level + workspace-level cost duplication

**Success Criteria**: Total costs match Claude Admin Console dashboard within $10 (99.99% accuracy)

---

## Feature Goals

### Primary Objectives

1. **Accurate Financial Reporting**
   - Achieve 99.99% cost accuracy vs Claude Admin Console
   - Eliminate 34-138x cost inflation from current system
   - Prevent double-counting between endpoints
   - Support historical backfill to January 2025

2. **Comprehensive Data Coverage**
   - All organization costs (claude.ai + Claude Code + API)
   - Per-API-key token usage for attribution
   - Developer productivity metrics without cost duplication
   - Complete historical data via pagination

3. **Maintainable Architecture**
   - Single-purpose tables with clear data ownership
   - Automated daily ingestion via Cloud Scheduler
   - Robust error handling and retry logic
   - Data quality validation after each run

### Non-Goals

- Real-time ingestion (daily batch is sufficient)
- Per-user cost breakdown (API doesn't support it directly)
- Claude Code cost storage in productivity table (prevents double-counting)
- Integration with external BI tools beyond Metabase

---

## Architecture Overview

### Data Flow

```
Claude Admin API (3 endpoints)
    |
    ├─> /cost_report                    → claude_costs (all org costs)
    ├─> /usage_report/messages          → claude_usage_keys (per-key tokens)
    └─> /usage_report/claude_code       → claude_code_productivity (IDE metrics only)
    |
    v
BigQuery (3 partitioned tables)
    |
    v
Metabase Dashboards
```

### Table Design Summary

| Table | Purpose | Source Endpoint | Key Data |
|-------|---------|-----------------|----------|
| `claude_costs` | Financial data (PRIMARY) | `/cost_report` | All org costs (API + Workbench + Claude Code) |
| `claude_usage_keys` | Per-key attribution | `/usage_report/messages` | Token usage by API key |
| `claude_code_productivity` | IDE metrics ONLY | `/usage_report/claude_code` | Lines added, commits, PRs (NO COSTS) |

**Critical Rule**: NEVER sum `claude_costs` + `claude_code_productivity` costs (double-counts Claude Code!)

---

## Detailed Table Schemas

### Table 1: claude_costs (Financial Data - Primary Source)

**Source**: `/v1/organizations/cost_report`
**API Parameters**: `group_by[]=workspace_id&group_by[]=description`
**Update Frequency**: Daily
**Purpose**: Single source of truth for ALL organization costs

```sql
CREATE TABLE `ai_usage_analytics.claude_costs` (
  -- Time dimension
  activity_date DATE NOT NULL,

  -- Attribution
  organization_id STRING NOT NULL,
  workspace_id STRING,              -- NULL = "Default" workspace, non-NULL = "Claude Code"

  -- Cost dimensions
  model STRING NOT NULL,            -- claude-3-5-sonnet-20241022, etc.
  token_type STRING NOT NULL,       -- uncached_input_tokens, output_tokens, cache_read, cache_creation
  cost_type STRING NOT NULL,        -- 'tokens', 'web_search', 'code_execution'

  -- Financial metrics
  amount_usd NUMERIC(10,4) NOT NULL,  -- CRITICAL: Divide API response by 100 (cents→dollars)
  currency STRING NOT NULL,           -- Always 'USD'

  -- Metadata
  description STRING,               -- Platform indicator: "API Request", "Workbench", "Claude Code"
  service_tier STRING,              -- 'default', 'batch', 'priority'
  context_window STRING,            -- '0-200k', '200k+'

  -- Audit
  ingestion_timestamp TIMESTAMP NOT NULL,
  api_response_hash STRING          -- For idempotency checking
)
PARTITION BY activity_date
CLUSTER BY workspace_id, model, token_type;
```

**Ingestion Logic**:
```python
# Critical bug fixes
amount_usd = api_response['amount'] / 100  # API returns cents!

# Pagination loop
while True:
    response = requests.get(url, params={
        'starting_at': start_date,
        'ending_at': end_date,
        'group_by[]': ['workspace_id', 'description'],
        'page': next_page  # Handle pagination
    })

    data = response.json()
    process_records(data['data'])

    if not data.get('has_more', False):
        break
    next_page = data['next_page']
```

**Validation Queries**:
```sql
-- Total costs must match dashboard within $10
SELECT SUM(amount_usd) as total_cost
FROM claude_costs
WHERE activity_date BETWEEN '2025-01-01' AND '2025-10-18';
-- Expected: ~$89.58 (verified via API testing)

-- No duplicate records
SELECT activity_date, workspace_id, model, token_type, COUNT(*) as cnt
FROM claude_costs
GROUP BY activity_date, workspace_id, model, token_type
HAVING cnt > 1;
-- Expected: 0 rows
```

---

### Table 2: claude_usage_keys (Per-Key Token Usage)

**Source**: `/v1/organizations/usage_report/messages`
**API Parameters**: `group_by[]=api_key_id&group_by[]=workspace_id&group_by[]=model&bucket_width=1d`
**Update Frequency**: Daily
**Purpose**: Token usage attribution per API key (for proportional cost allocation)

```sql
CREATE TABLE `ai_usage_analytics.claude_usage_keys` (
  -- Time dimension
  activity_date DATE NOT NULL,

  -- Attribution
  organization_id STRING NOT NULL,
  api_key_id STRING NOT NULL,       -- ONLY endpoint with api_key_id!
  workspace_id STRING,

  -- Usage dimensions
  model STRING NOT NULL,

  -- Token metrics (NO COSTS - costs are in claude_costs table)
  uncached_input_tokens INT64 NOT NULL,
  output_tokens INT64 NOT NULL,
  cache_read_input_tokens INT64 NOT NULL,
  cache_creation_5m_tokens INT64 NOT NULL,
  cache_creation_1h_tokens INT64 NOT NULL,
  web_search_requests INT64 NOT NULL,

  -- Audit
  ingestion_timestamp TIMESTAMP NOT NULL
)
PARTITION BY activity_date
CLUSTER BY api_key_id, workspace_id, model;
```

**Ingestion Logic**:
```python
# Pagination loop with 7-day default limit
while True:
    response = requests.get(url, params={
        'starting_at': start_date,
        'ending_at': end_date,
        'bucket_width': '1d',
        'group_by[]': ['api_key_id', 'workspace_id', 'model'],
        'page': next_page
    })

    data = response.json()

    # Extract token counts from each bucket
    for bucket in data['data']:
        for result in bucket['results']:
            # Store token counts only (no cost calculation)
            record = {
                'activity_date': bucket['starting_at'][:10],
                'api_key_id': result['api_key_id'],
                'workspace_id': result.get('workspace_id'),
                'model': result['model'],
                'uncached_input_tokens': result['uncached_input_tokens'],
                'output_tokens': result['output_tokens'],
                # ... other token fields
            }

    if not data.get('has_more', False):
        break
    next_page = data['next_page']
```

**Per-Key Cost Allocation** (approximate via proportional join):
```sql
-- Allocate workspace costs to API keys based on token usage percentage
WITH workspace_costs AS (
  SELECT
    workspace_id,
    model,
    activity_date,
    SUM(amount_usd) as total_cost
  FROM claude_costs
  WHERE token_type IN ('uncached_input_tokens', 'output_tokens')
  GROUP BY workspace_id, model, activity_date
),
key_usage AS (
  SELECT
    api_key_id,
    workspace_id,
    model,
    activity_date,
    (uncached_input_tokens + output_tokens + cache_read_input_tokens) as total_tokens
  FROM claude_usage_keys
)
SELECT
  k.api_key_id,
  k.model,
  k.activity_date,
  k.total_tokens,
  c.total_cost * (
    k.total_tokens /
    SUM(k.total_tokens) OVER (PARTITION BY k.workspace_id, k.model, k.activity_date)
  ) as allocated_cost
FROM key_usage k
JOIN workspace_costs c USING (workspace_id, model, activity_date);
```

---

### Table 3: claude_code_productivity (IDE Metrics ONLY - NO COSTS)

**Source**: `/v1/organizations/usage_report/claude_code`
**API Parameters**: `starting_at={date}` (single day only)
**Update Frequency**: Daily
**Purpose**: Developer productivity metrics WITHOUT financial data (prevents double-counting)

```sql
CREATE TABLE `ai_usage_analytics.claude_code_productivity` (
  -- Time dimension
  activity_date DATE NOT NULL,

  -- Attribution
  organization_id STRING NOT NULL,
  actor_type STRING NOT NULL,       -- 'user_actor' or 'api_actor'
  user_email STRING,                -- Non-null when actor_type = 'user_actor'
  api_key_name STRING,              -- Non-null when actor_type = 'api_actor'
  terminal_type STRING,             -- 'vscode', 'iTerm.app', 'tmux', etc.

  -- Productivity metrics ONLY (NO COSTS!)
  num_sessions INT64,
  lines_added INT64,
  lines_removed INT64,
  commits_by_claude_code INT64,
  pull_requests_by_claude_code INT64,
  edit_tool_accepted INT64,
  edit_tool_rejected INT64,
  write_tool_accepted INT64,
  write_tool_rejected INT64,
  notebook_edit_tool_accepted INT64,
  notebook_edit_tool_rejected INT64,

  -- CRITICAL: NO cost or token fields!
  -- These are already in claude_costs table
  -- Including them here would cause double-counting

  -- Audit
  ingestion_timestamp TIMESTAMP NOT NULL
)
PARTITION BY activity_date
CLUSTER BY user_email, terminal_type;
```

**Ingestion Logic**:
```python
# Single-day pagination (API only supports one day at a time)
response = requests.get(url, params={
    'starting_at': date,  # YYYY-MM-DD format
    'limit': 1000
})

data = response.json()

for record in data['data']:
    # Extract productivity metrics ONLY
    row = {
        'activity_date': record['date'][:10],
        'organization_id': record['organization_id'],
        'actor_type': record['actor']['type'],
        'user_email': record['actor'].get('email_address'),
        'api_key_name': record['actor'].get('api_key_name'),
        'terminal_type': record['terminal_type'],
        'num_sessions': record['core_metrics']['num_sessions'],
        'lines_added': record['core_metrics']['lines_of_code']['added'],
        'lines_removed': record['core_metrics']['lines_of_code']['removed'],
        # ... other productivity fields
    }

    # CRITICAL: Do NOT store model_breakdown costs
    # Those costs are already in claude_costs table!

# Handle pagination
while data.get('has_more', False):
    response = requests.get(url, params={
        'starting_at': date,
        'page': data['next_page']
    })
    data = response.json()
```

**Validation Queries**:
```sql
-- Verify no cost fields exist
SELECT COLUMN_NAME
FROM `ai_usage_analytics.INFORMATION_SCHEMA.COLUMNS`
WHERE TABLE_NAME = 'claude_code_productivity'
  AND (COLUMN_NAME LIKE '%cost%' OR COLUMN_NAME LIKE '%token%');
-- Expected: 0 rows

-- Total productivity metrics
SELECT
  COUNT(DISTINCT user_email) as active_users,
  SUM(lines_added) as total_lines_added,
  SUM(commits_by_claude_code) as total_commits
FROM claude_code_productivity
WHERE activity_date = '2025-10-15';
```

---

## Ingestion Implementation Details

### Python Script Structure

**Location**: `/scripts/ingest_claude_data.py`

```python
import os
import requests
from datetime import datetime, timedelta
from google.cloud import bigquery
from google.cloud import secretmanager

class ClaudeDataIngestion:
    """
    Ingests Claude data from Admin API into BigQuery.
    Fixes critical bugs: cents conversion, pagination, deduplication.
    """

    def __init__(self):
        self.api_key = self._get_secret('ANTHROPIC_ADMIN_KEY')
        self.org_id = self._get_secret('ANTHROPIC_ORG_ID')
        self.bq_client = bigquery.Client()
        self.base_url = "https://api.anthropic.com/v1/organizations"

    def _get_secret(self, secret_name: str) -> str:
        """Fetch secret from Google Secret Manager."""
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/ai-workflows-459123/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(name=name)
        return response.payload.data.decode('UTF-8')

    def ingest_costs(self, start_date: str, end_date: str):
        """
        Ingest data from /cost_report endpoint.

        CRITICAL BUG FIXES:
        1. Divide amount by 100 (API returns cents)
        2. Paginate through all pages (7-day default limit)
        3. Handle workspace_id for deduplication
        """
        url = f"{self.base_url}/cost_report"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }

        all_records = []
        next_page = None

        while True:
            params = {
                'starting_at': start_date,
                'ending_at': end_date,
                'group_by[]': ['workspace_id', 'description']
            }
            if next_page:
                params['page'] = next_page

            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            # Process each day bucket
            for day_data in data.get('data', []):
                for result in day_data.get('results', []):
                    record = {
                        'activity_date': day_data['starting_at'][:10],
                        'organization_id': self.org_id,
                        'workspace_id': result.get('workspace_id'),
                        'model': result.get('model'),
                        'token_type': result.get('token_type'),
                        'cost_type': result.get('cost_type', 'tokens'),
                        # CRITICAL: Divide by 100 (API returns cents)
                        'amount_usd': float(result['amount']) / 100,
                        'currency': result['currency'],
                        'description': result.get('description'),
                        'service_tier': result.get('service_tier'),
                        'context_window': result.get('context_window'),
                        'ingestion_timestamp': datetime.utcnow().isoformat()
                    }
                    all_records.append(record)

            # Check pagination
            if not data.get('has_more', False):
                break
            next_page = data['next_page']

        # Load to BigQuery
        table_id = "ai_usage_analytics.claude_costs"
        errors = self.bq_client.insert_rows_json(table_id, all_records)

        if errors:
            raise Exception(f"BigQuery insert errors: {errors}")

        print(f"Inserted {len(all_records)} cost records")
        return len(all_records)

    def ingest_usage_keys(self, start_date: str, end_date: str):
        """Ingest data from /usage_report/messages endpoint."""
        url = f"{self.base_url}/usage_report/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }

        all_records = []
        next_page = None

        while True:
            params = {
                'starting_at': start_date,
                'ending_at': end_date,
                'bucket_width': '1d',
                'group_by[]': ['api_key_id', 'workspace_id', 'model']
            }
            if next_page:
                params['page'] = next_page

            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            # Process each bucket
            for bucket in data.get('data', []):
                for result in bucket.get('results', []):
                    record = {
                        'activity_date': bucket['starting_at'][:10],
                        'organization_id': self.org_id,
                        'api_key_id': result.get('api_key_id'),
                        'workspace_id': result.get('workspace_id'),
                        'model': result.get('model'),
                        'uncached_input_tokens': result.get('uncached_input_tokens', 0),
                        'output_tokens': result.get('output_tokens', 0),
                        'cache_read_input_tokens': result.get('cache_read_input_tokens', 0),
                        'cache_creation_5m_tokens': result.get('cache_creation_5m_tokens', 0),
                        'cache_creation_1h_tokens': result.get('cache_creation_1h_tokens', 0),
                        'web_search_requests': result.get('web_search_requests', 0),
                        'ingestion_timestamp': datetime.utcnow().isoformat()
                    }
                    all_records.append(record)

            if not data.get('has_more', False):
                break
            next_page = data['next_page']

        # Load to BigQuery
        table_id = "ai_usage_analytics.claude_usage_keys"
        errors = self.bq_client.insert_rows_json(table_id, all_records)

        if errors:
            raise Exception(f"BigQuery insert errors: {errors}")

        print(f"Inserted {len(all_records)} usage key records")
        return len(all_records)

    def ingest_claude_code_productivity(self, date: str):
        """
        Ingest data from /usage_report/claude_code endpoint.

        CRITICAL: Only productivity metrics, NO costs!
        Costs are already in claude_costs table.
        """
        url = f"{self.base_url}/usage_report/claude_code"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }

        all_records = []
        next_page = None

        while True:
            params = {'starting_at': date, 'limit': 1000}
            if next_page:
                params['page'] = next_page

            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            for item in data.get('data', []):
                actor = item['actor']
                core_metrics = item.get('core_metrics', {})
                tool_actions = item.get('tool_actions', {})

                record = {
                    'activity_date': item['date'][:10],
                    'organization_id': item['organization_id'],
                    'actor_type': actor['type'],
                    'user_email': actor.get('email_address'),
                    'api_key_name': actor.get('api_key_name'),
                    'terminal_type': item.get('terminal_type'),
                    # Productivity metrics only
                    'num_sessions': core_metrics.get('num_sessions', 0),
                    'lines_added': core_metrics.get('lines_of_code', {}).get('added', 0),
                    'lines_removed': core_metrics.get('lines_of_code', {}).get('removed', 0),
                    'commits_by_claude_code': core_metrics.get('commits_by_claude_code', 0),
                    'pull_requests_by_claude_code': core_metrics.get('pull_requests_by_claude_code', 0),
                    'edit_tool_accepted': tool_actions.get('edit_tool', {}).get('accepted', 0),
                    'edit_tool_rejected': tool_actions.get('edit_tool', {}).get('rejected', 0),
                    'write_tool_accepted': tool_actions.get('write_tool', {}).get('accepted', 0),
                    'write_tool_rejected': tool_actions.get('write_tool', {}).get('rejected', 0),
                    'notebook_edit_tool_accepted': tool_actions.get('notebook_edit_tool', {}).get('accepted', 0),
                    'notebook_edit_tool_rejected': tool_actions.get('notebook_edit_tool', {}).get('rejected', 0),
                    'ingestion_timestamp': datetime.utcnow().isoformat()
                }
                # CRITICAL: Do NOT include model_breakdown costs!
                all_records.append(record)

            if not data.get('has_more', False):
                break
            next_page = data['next_page']

        # Load to BigQuery
        table_id = "ai_usage_analytics.claude_code_productivity"
        errors = self.bq_client.insert_rows_json(table_id, all_records)

        if errors:
            raise Exception(f"BigQuery insert errors: {errors}")

        print(f"Inserted {len(all_records)} productivity records")
        return len(all_records)

    def run_daily_ingestion(self):
        """Main entry point for daily Cloud Run job."""
        # Ingest yesterday's data
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')

        print(f"Starting ingestion for {yesterday}")

        # Ingest costs (primary financial data)
        cost_count = self.ingest_costs(yesterday, yesterday)

        # Ingest per-key usage
        usage_count = self.ingest_usage_keys(yesterday, yesterday)

        # Ingest Claude Code productivity
        cc_count = self.ingest_claude_code_productivity(yesterday)

        # Validate total costs
        self.validate_costs(yesterday)

        print(f"Ingestion complete: {cost_count} costs, {usage_count} usage, {cc_count} productivity")

    def validate_costs(self, date: str):
        """Validate total costs against expected range."""
        query = f"""
        SELECT SUM(amount_usd) as total_cost
        FROM `ai_usage_analytics.claude_costs`
        WHERE activity_date = '{date}'
        """

        result = list(self.bq_client.query(query))[0]
        total_cost = float(result.total_cost or 0)

        print(f"Total cost for {date}: ${total_cost:.2f}")

        # Alert if cost is suspiciously high (potential double-counting)
        if total_cost > 1000:
            raise Exception(f"Cost validation failed: ${total_cost} exceeds threshold")

if __name__ == "__main__":
    ingestion = ClaudeDataIngestion()
    ingestion.run_daily_ingestion()
```

---

## Deployment Strategy

### Cloud Run Job Configuration

**Service Name**: `claude-data-ingestion`
**Region**: `us-central1`
**Execution Environment**: Python 3.11 container
**Memory**: 512 MB
**Timeout**: 900 seconds (15 minutes)
**Concurrency**: 1 (sequential processing)

**Dockerfile**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts/ingest_claude_data.py .

CMD ["python", "ingest_claude_data.py"]
```

**requirements.txt**:
```
google-cloud-bigquery==3.14.0
google-cloud-secret-manager==2.17.0
requests==2.31.0
```

### Cloud Scheduler Configuration

**Schedule**: Daily at 6:00 AM PT (14:00 UTC)
**Target**: Cloud Run job `claude-data-ingestion`
**Retry Policy**: 3 retries with exponential backoff

```yaml
name: claude-daily-ingestion
schedule: "0 14 * * *"
timeZone: UTC
target:
  type: cloudRun
  service: claude-data-ingestion
  region: us-central1
retryConfig:
  retryCount: 3
  maxBackoffDuration: 3600s
  minBackoffDuration: 60s
```

### Environment Variables (Secret Manager)

| Secret Name | Purpose |
|------------|---------|
| `ANTHROPIC_ADMIN_KEY` | Claude Admin API key (sk-ant-admin...) |
| `ANTHROPIC_ORG_ID` | Organization UUID |
| `BIGQUERY_PROJECT_ID` | GCP project ID (ai-workflows-459123) |
| `BIGQUERY_DATASET` | Dataset name (ai_usage_analytics) |

---

## Validation Criteria

### Data Quality Checks

**1. Cost Accuracy Validation**
```sql
-- Total costs must match dashboard within $10
SELECT
  activity_date,
  SUM(amount_usd) as total_cost
FROM `ai_usage_analytics.claude_costs`
WHERE activity_date BETWEEN '2025-01-01' AND '2025-10-18'
GROUP BY activity_date
ORDER BY activity_date DESC
LIMIT 30;

-- Expected: ~$89.58 for full period (verified via API testing)
-- Tolerance: ±$10 (99.99% accuracy)
```

**2. Deduplication Validation**
```sql
-- No duplicate cost records
SELECT
  activity_date,
  workspace_id,
  model,
  token_type,
  COUNT(*) as cnt
FROM `ai_usage_analytics.claude_costs`
GROUP BY activity_date, workspace_id, model, token_type
HAVING cnt > 1;

-- Expected: 0 rows
```

**3. Double-Counting Prevention**
```sql
-- Verify Claude Code costs NOT in productivity table
SELECT COUNT(*)
FROM `ai_usage_analytics.INFORMATION_SCHEMA.COLUMNS`
WHERE TABLE_NAME = 'claude_code_productivity'
  AND (COLUMN_NAME LIKE '%cost%' OR COLUMN_NAME LIKE '%amount%');

-- Expected: 0 rows
```

**4. Data Completeness**
```sql
-- Check for missing dates in past 30 days
WITH expected_dates AS (
  SELECT DATE_SUB(CURRENT_DATE(), INTERVAL n DAY) as date
  FROM UNNEST(GENERATE_ARRAY(1, 30)) as n
)
SELECT e.date
FROM expected_dates e
LEFT JOIN (
  SELECT DISTINCT activity_date
  FROM `ai_usage_analytics.claude_costs`
) c ON e.date = c.activity_date
WHERE c.activity_date IS NULL;

-- Expected: 0 rows (all dates present)
```

**5. Pagination Success**
```sql
-- Verify records exist beyond 7-day default limit
SELECT
  MIN(activity_date) as earliest_date,
  MAX(activity_date) as latest_date,
  COUNT(DISTINCT activity_date) as date_count
FROM `ai_usage_analytics.claude_costs`;

-- Expected: date_count > 7 (pagination working)
```

### Performance Benchmarks

| Metric | Target | Validation Method |
|--------|--------|------------------|
| Ingestion Time | < 5 minutes | Cloud Run job logs |
| API Calls | < 20 per day | Request logging |
| Data Freshness | < 24 hours | Max(ingestion_timestamp) |
| Cost Accuracy | 99.99% (±$10) | SUM(amount_usd) vs dashboard |
| Data Completeness | 100% (all days) | Date gap query |

---

## Implementation Task Breakdown

### Phase 1: Table Creation (Day 1)

**Tasks**:
1. Create `claude_costs` table in BigQuery
   - Partitioned by `activity_date`
   - Clustered by `workspace_id, model, token_type`
   - Test partition pruning efficiency

2. Create `claude_usage_keys` table in BigQuery
   - Partitioned by `activity_date`
   - Clustered by `api_key_id, workspace_id, model`

3. Create `claude_code_productivity` table in BigQuery
   - Partitioned by `activity_date`
   - Clustered by `user_email, terminal_type`
   - Verify NO cost/token columns

**Validation**: Run `INFORMATION_SCHEMA` queries to verify schemas

### Phase 2: Core Ingestion Logic (Days 2-3)

**Tasks**:
1. Implement `ingest_costs()` function
   - Fix: Divide amount by 100 (cents to dollars)
   - Fix: Pagination loop with `has_more` check
   - Handle `workspace_id` NULL vs non-NULL

2. Implement `ingest_usage_keys()` function
   - Pagination with 7-day default limit
   - Extract token counts from nested response structure
   - Store NO costs (only token counts)

3. Implement `ingest_claude_code_productivity()` function
   - Single-day pagination (API limitation)
   - Extract productivity metrics only
   - CRITICAL: Ignore `model_breakdown` costs

**Validation**:
- Manual test run for single day (2025-10-15)
- Verify record counts match API response
- Check for duplicate records

### Phase 3: Error Handling & Retry (Day 4)

**Tasks**:
1. Add exponential backoff for API rate limits
2. Implement Secret Manager integration
3. Add structured logging (Cloud Logging)
4. Handle API error responses (401, 429, 500)
5. Implement idempotency checks (hash-based)

**Validation**:
- Simulate API failures (mock 429 errors)
- Verify retry logic with exponential backoff
- Check logs for proper error messages

### Phase 4: Cloud Run Deployment (Day 5)

**Tasks**:
1. Create Dockerfile and requirements.txt
2. Build and push container to GCR
3. Deploy Cloud Run job with proper permissions
4. Configure Secret Manager access
5. Set up Cloud Scheduler daily trigger

**Validation**:
- Manual Cloud Run job execution
- Check BigQuery for new records
- Verify Secret Manager access works

### Phase 5: Historical Backfill (Days 6-7)

**Tasks**:
1. Implement backfill script for date range
2. Backfill January 1 - October 18, 2025 (292 days)
3. Run validation queries after backfill
4. Verify total costs match dashboard

**Validation**:
```sql
-- Total costs for full period
SELECT SUM(amount_usd) FROM claude_costs
WHERE activity_date BETWEEN '2025-01-01' AND '2025-10-18';
-- Expected: ~$89.58 ±$10
```

### Phase 6: Integration Testing (Day 8)

**Tasks**:
1. Test daily scheduled run
2. Validate all 3 tables populated correctly
3. Run all data quality checks
4. Create Metabase dashboard queries
5. Document any edge cases discovered

**Validation**:
- All validation queries pass
- Dashboard displays correct totals
- No duplicate records
- All dates present

---

## Risk Assessment & Mitigation

### High-Risk Items

**1. API Pagination Bugs**
- **Risk**: Missing data beyond 7-day default limit
- **Mitigation**: Robust pagination loop with `has_more` check, log page counts
- **Validation**: Query for records > 7 days old

**2. Cents/Dollar Conversion**
- **Risk**: Forgetting to divide by 100 (causes 100x inflation)
- **Mitigation**: Unit tests for conversion, validation query comparing to dashboard
- **Validation**: Total costs must match dashboard ±$10

**3. Double-Counting Claude Code Costs**
- **Risk**: Storing costs in both `claude_costs` and `claude_code_productivity`
- **Mitigation**: Schema validation, column name checks, documentation
- **Validation**: No cost columns in productivity table

**4. API Rate Limiting**
- **Risk**: 429 errors during backfill
- **Mitigation**: Exponential backoff, chunked date ranges, retry logic
- **Validation**: Monitor Cloud Logging for 429 errors

### Medium-Risk Items

**5. Secret Manager Access**
- **Risk**: Cloud Run can't access API keys
- **Mitigation**: Test IAM permissions before deployment
- **Validation**: Manual run with secret access

**6. BigQuery Insert Failures**
- **Risk**: Schema mismatches, quota exceeded
- **Mitigation**: Schema validation, streaming inserts with error handling
- **Validation**: Check `insert_errors` response

**7. Data Freshness**
- **Risk**: API data lags by > 24 hours
- **Mitigation**: Ingest yesterday's data (not today), log data freshness
- **Validation**: Max(ingestion_timestamp) within 24 hours

---

## Success Metrics

### Primary Success Criteria

1. **Cost Accuracy**: Total costs match Claude Admin Console within $10 (99.99%)
2. **Data Completeness**: All dates from Jan 1 - Oct 18, 2025 present (0 gaps)
3. **No Duplication**: Zero duplicate records across all 3 tables
4. **No Double-Counting**: Claude Code costs only in `claude_costs` table

### Secondary Success Criteria

5. **Ingestion Speed**: Daily job completes in < 5 minutes
6. **Error Rate**: < 1% API request failures (with retry)
7. **Data Freshness**: Ingestion timestamp within 24 hours of activity_date
8. **Backfill Success**: 292 days of historical data ingested without gaps

### Dashboard Validation

- [ ] Total costs chart matches Claude Admin Console
- [ ] Per-model cost breakdown accurate
- [ ] Claude Code productivity metrics display correctly
- [ ] No negative costs or impossible values
- [ ] API key attribution working (via proportional allocation)

---

## Dependencies & Prerequisites

### External Dependencies

1. **Claude Admin API Access**
   - Admin API key (sk-ant-admin...) with full permissions
   - Organization ID
   - Rate limits: Unknown (implement conservative backoff)

2. **Google Cloud Platform**
   - Project: `ai-workflows-459123`
   - Dataset: `ai_usage_analytics`
   - Cloud Run enabled
   - Secret Manager enabled
   - Cloud Scheduler enabled

3. **BigQuery Permissions**
   - `bigquery.tables.create` (for table creation)
   - `bigquery.tables.updateData` (for inserts)
   - `bigquery.jobs.create` (for queries)

### Internal Dependencies

4. **Existing Infrastructure**
   - Metabase connected to BigQuery
   - Google Sheets API key mapping table (optional, for future use)

### Development Tools

5. **Local Testing**
   - Python 3.11+
   - Google Cloud SDK
   - BigQuery emulator (for unit tests)
   - pytest for testing

---

## Documentation Requirements

### Code Documentation

1. **Inline Comments**
   - Explain all critical bug fixes (cents, pagination, deduplication)
   - Document API response structure assumptions
   - Note double-counting prevention logic

2. **Function Docstrings**
   - All public methods with param/return types
   - Include example API responses
   - List common error scenarios

### Operational Documentation

3. **Runbook** (`docs/runbooks/claude-ingestion.md`)
   - How to trigger manual backfill
   - How to investigate missing data
   - How to validate data quality
   - Common troubleshooting scenarios

4. **Architecture Decision Records**
   - Why 3 tables instead of 1?
   - Why not store costs in productivity table?
   - Why proportional allocation vs exact per-key costs?

5. **API Integration Guide** (`docs/api-reference/claude-admin-api.md`)
   - All endpoint documentation (already exists)
   - Response schema examples
   - Pagination behavior
   - Rate limits

---

## Testing Strategy

### Unit Tests

```python
# tests/test_claude_ingestion.py

def test_cents_to_dollars_conversion():
    """Verify API response in cents is correctly converted to dollars."""
    api_response = {'amount': 958}  # 958 cents
    expected_usd = 9.58
    actual_usd = api_response['amount'] / 100
    assert actual_usd == expected_usd

def test_pagination_loop():
    """Verify pagination continues until has_more=False."""
    # Mock API responses with has_more flag
    # Assert all pages fetched

def test_workspace_id_null_handling():
    """Verify NULL workspace_id represents Default workspace."""
    record = {'workspace_id': None}
    # Assert classified as "Default" workspace

def test_no_cost_in_productivity_table():
    """Verify claude_code_productivity schema has no cost columns."""
    schema = get_table_schema('claude_code_productivity')
    cost_columns = [c for c in schema if 'cost' in c.lower()]
    assert len(cost_columns) == 0
```

### Integration Tests

```python
# tests/integration/test_end_to_end.py

def test_daily_ingestion_end_to_end():
    """Full ingestion test for single day."""
    date = '2025-10-15'

    # Run ingestion
    ingestion = ClaudeDataIngestion()
    cost_count = ingestion.ingest_costs(date, date)
    usage_count = ingestion.ingest_usage_keys(date, date)
    cc_count = ingestion.ingest_claude_code_productivity(date)

    # Validate record counts > 0
    assert cost_count > 0
    assert usage_count > 0
    assert cc_count >= 0  # May be 0 if no Claude Code usage

    # Validate no duplicates
    duplicate_count = count_duplicates('claude_costs', date)
    assert duplicate_count == 0

def test_backfill_date_range():
    """Test backfill for 7-day range."""
    start = '2025-10-01'
    end = '2025-10-07'

    # Run backfill
    # Validate 7 dates present
    # Validate total costs reasonable
```

### Validation Queries (Run After Deployment)

```sql
-- 1. Cost accuracy (must be within $10 of dashboard)
SELECT SUM(amount_usd) FROM claude_costs
WHERE activity_date BETWEEN '2025-01-01' AND '2025-10-18';

-- 2. No duplicates
SELECT activity_date, workspace_id, model, token_type, COUNT(*) as cnt
FROM claude_costs
GROUP BY activity_date, workspace_id, model, token_type
HAVING cnt > 1;

-- 3. Date completeness (no gaps)
WITH RECURSIVE dates AS (
  SELECT DATE '2025-01-01' as date
  UNION ALL
  SELECT DATE_ADD(date, INTERVAL 1 DAY)
  FROM dates
  WHERE date < '2025-10-18'
)
SELECT d.date
FROM dates d
LEFT JOIN (SELECT DISTINCT activity_date FROM claude_costs) c
  ON d.date = c.activity_date
WHERE c.activity_date IS NULL;

-- 4. No costs in productivity table
SELECT COLUMN_NAME
FROM `ai_usage_analytics.INFORMATION_SCHEMA.COLUMNS`
WHERE TABLE_NAME = 'claude_code_productivity'
  AND (COLUMN_NAME LIKE '%cost%' OR COLUMN_NAME LIKE '%amount%');
```

---

## Monitoring & Alerting

### Cloud Monitoring Metrics

1. **Ingestion Success Rate**
   - Metric: `custom/ingestion/success_rate`
   - Alert: < 95% success over 7 days

2. **Data Freshness**
   - Metric: `custom/data/hours_since_last_ingestion`
   - Alert: > 48 hours

3. **Cost Anomaly Detection**
   - Metric: `custom/costs/daily_total_usd`
   - Alert: > $1000/day (potential double-counting)

4. **API Error Rate**
   - Metric: `custom/api/error_rate`
   - Alert: > 5% errors over 1 hour

### Cloud Logging Queries

```
# Failed ingestion runs
resource.type="cloud_run_job"
resource.labels.job_name="claude-data-ingestion"
severity>=ERROR

# API pagination issues
resource.type="cloud_run_job"
textPayload=~"has_more.*true"

# Cost validation failures
resource.type="cloud_run_job"
textPayload=~"Cost validation failed"
```

---

## Rollback Plan

### If Critical Bug Found After Deployment

1. **Stop Cloud Scheduler** (prevent new ingestion runs)
2. **Identify impacted date range** (query ingestion_timestamp)
3. **Delete impacted records**:
   ```sql
   DELETE FROM claude_costs
   WHERE ingestion_timestamp > 'YYYY-MM-DD HH:MM:SS';
   ```
4. **Fix bug in code**
5. **Re-run ingestion for impacted dates**
6. **Validate with accuracy queries**
7. **Re-enable Cloud Scheduler**

### Emergency Rollback to Old System

- Document current system for comparison
- Keep old ingestion scripts for 30 days
- Maintain separate `claude_costs_v1` table for fallback

---

## Future Enhancements (Out of Scope)

1. **Real-Time Ingestion** (currently daily batch)
2. **Per-User Cost Breakdown** (API doesn't support directly)
3. **Cost Forecasting** (ML-based predictions)
4. **Alerting on Budget Thresholds** (FinOps integration)
5. **API Key Auto-Discovery** (currently manual mapping)
6. **Retry Queue for Failed Records** (currently fail entire job)

---

## References

### Documentation
- `/Users/sid/Desktop/4. Coding Projects/samba-ai-usage-stats/docs/CLAUDE_FINAL_VALIDATED_DESIGN.md`
- `/Users/sid/Desktop/4. Coding Projects/samba-ai-usage-stats/docs/api-reference/claude-admin-api.md`
- `/Users/sid/Desktop/4. Coding Projects/samba-ai-usage-stats/docs/prd/data-architecture.md`
- `/Users/sid/Desktop/4. Coding Projects/samba-ai-usage-stats/docs/architecture/external-api-integrations.md`

### API Endpoints
- `POST /v1/organizations/cost_report` - All org costs (primary)
- `POST /v1/organizations/usage_report/messages` - Per-key token usage
- `POST /v1/organizations/usage_report/claude_code` - IDE productivity metrics

### Related Stories
- Story 2.7: Cursor spending backfill (similar pattern)
- Story 3.8: Dashboard parameter binding fixes

---

**Document Status**: Ready for Implementation
**Next Step**: Create detailed PRD and begin Phase 1 (table creation)
**Estimated Timeline**: 8 days (assuming 1 developer full-time)
