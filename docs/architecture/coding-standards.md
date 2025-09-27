# Coding Standards

## Critical Data Pipeline Rules

- **Error Handling:** All external API calls must use try-catch with exponential backoff retry logic
- **Data Validation:** Never insert data to BigQuery without schema validation - use validate_schema() before all inserts
- **Configuration Access:** Access secrets only through config.get_secret(), never os.environ directly
- **Logging Format:** All logs must use structured JSON format with request_id for traceability
- **Date Handling:** Always use UTC timestamps, convert timezone-aware dates at ingestion boundary
- **Batch Processing:** Use 1000-record batches for BigQuery inserts to optimize performance and cost

## Naming Conventions
| Element | Convention | Example |
|---------|------------|---------|
| Python Files | snake_case | `anthropic_client.py` |
| Python Classes | PascalCase | `DataTransformer` |
| Python Functions | snake_case | `fetch_daily_usage()` |
| BigQuery Tables | snake_case with prefix | `fct_usage_daily` |
| BigQuery Views | snake_case with vw_ prefix | `vw_monthly_finance` |
| Environment Variables | UPPER_SNAKE_CASE | `BIGQUERY_DATASET` |

---
