# Database Schema

## BigQuery Dataset Configuration
- **Dataset Name:** `ai_usage`
- **Location:** `US` (multi-region for availability)
- **Default Table Expiration:** None (2+ year retention requirement)
- **Encryption:** Google-managed keys

## Raw Data Tables (Ingestion Layer)

### raw_anthropic_usage
```sql
CREATE TABLE `ai_usage.raw_anthropic_usage` (
  ingest_date DATE NOT NULL,
  fetched_at TIMESTAMP NOT NULL,
  api_key_id STRING NOT NULL,
  workspace_id STRING NOT NULL,
  model STRING NOT NULL,
  uncached_input_tokens INT64,
  output_tokens INT64,
  cache_read_input_tokens INT64,
  cache_creation_tokens INT64,
  service_tier STRING,
  context_window STRING,
  starting_at TIMESTAMP NOT NULL,
  ending_at TIMESTAMP NOT NULL
)
PARTITION BY ingest_date
CLUSTER BY api_key_id, model;
```

### raw_cursor_usage
```sql
CREATE TABLE `ai_usage.raw_cursor_usage` (
  ingest_date DATE NOT NULL,
  fetched_at TIMESTAMP NOT NULL,
  email STRING NOT NULL,
  usage_date DATE NOT NULL,
  total_lines_added INT64,
  accepted_lines_added INT64,
  total_accepts INT64,
  total_rejects INT64,
  subscription_included_reqs INT64,
  usage_based_reqs INT64,
  most_used_model STRING,
  client_version STRING
)
PARTITION BY ingest_date
CLUSTER BY email, usage_date;
```

## Curated Data Tables (Analytics Layer)

### dim_users
```sql
CREATE TABLE `ai_usage.dim_users` (
  user_id STRING NOT NULL,
  email STRING NOT NULL,
  first_name STRING,
  last_name STRING,
  department STRING,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);
```

### fct_usage_daily
```sql
CREATE TABLE `ai_usage.fct_usage_daily` (
  usage_date DATE NOT NULL,
  platform STRING NOT NULL,
  user_email STRING NOT NULL,
  api_key_id STRING,
  model STRING NOT NULL,
  input_tokens INT64 DEFAULT 0,
  output_tokens INT64 DEFAULT 0,
  requests INT64 DEFAULT 0,
  sessions INT64 DEFAULT 0,
  loc_added INT64 DEFAULT 0,
  loc_accepted INT64 DEFAULT 0,
  acceptance_rate NUMERIC(5,4) DEFAULT 0,
  processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY usage_date
CLUSTER BY platform, user_email;
```

### fct_cost_daily
```sql
CREATE TABLE `ai_usage.fct_cost_daily` (
  cost_date DATE NOT NULL,
  platform STRING NOT NULL,
  workspace_id STRING,
  api_key_id STRING,
  user_email STRING,
  cost_usd NUMERIC(10,4) NOT NULL,
  cost_type STRING DEFAULT 'usage',
  model STRING,
  processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY cost_date
CLUSTER BY platform, user_email;
```

---
