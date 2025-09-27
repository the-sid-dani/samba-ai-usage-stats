# Components

## Data Ingestion Components

### Anthropic API Client
**Responsibility:** Fetch usage and cost data from Anthropic Claude APIs with robust error handling and retry logic

**Key Interfaces:**
- `fetch_daily_usage(date: str) -> Dict` - Get usage data for specific date
- `fetch_daily_costs(date: str) -> Dict` - Get cost breakdown for date range
- `validate_response(data: Dict) -> bool` - Schema validation before processing

**Dependencies:** Secret Manager (API keys), Cloud Logging (error tracking)

**Technology Stack:** Python requests library, exponential backoff, JSON schema validation

### Cursor API Client
**Responsibility:** Extract team usage data including developer productivity metrics and code acceptance rates

**Key Interfaces:**
- `fetch_team_usage(start_date: str, end_date: str) -> List[Dict]` - Team usage data with date range
- `normalize_timestamps(data: List[Dict]) -> List[Dict]` - Convert Unix timestamps to ISO format
- `validate_email_attribution(data: List[Dict]) -> List[Dict]` - Ensure email format consistency

**Dependencies:** Secret Manager (API keys), Cloud Logging (audit trail)

**Technology Stack:** Python requests, date/time utilities, email validation

## Data Processing Components

### Data Transformation Engine
**Responsibility:** Normalize raw API data into consistent fact table format across all platforms

**Key Interfaces:**
- `transform_anthropic_usage(raw_data: Dict) -> List[Dict]` - Usage fact normalization
- `transform_cursor_metrics(raw_data: List[Dict]) -> List[Dict]` - Productivity metric processing
- `apply_user_attribution(facts: List[Dict], mappings: List[Dict]) -> List[Dict]` - Cost allocation logic

**Dependencies:** dim_api_keys, dim_users tables for lookups

**Technology Stack:** Python pandas for data manipulation, custom transformation logic

## Data Storage Components

### BigQuery Data Warehouse
**Responsibility:** Scalable analytics storage with partitioned tables optimized for time-series analysis

**Key Interfaces:**
- `load_raw_data(table: str, data: List[Dict])` - Bulk insert with partition management
- `refresh_curated_views()` - Update aggregated reporting views
- `execute_quality_checks() -> Dict` - Run automated data quality queries

**Dependencies:** Google Cloud IAM for access control, Cloud Logging for audit

**Technology Stack:** BigQuery Python client, SQL for view definitions, partitioning/clustering optimization

---
