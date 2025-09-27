# Testing Strategy

## Testing Pyramid
```
        E2E Tests (5%)
       /            \
   Integration Tests (25%)
   /                    \
Unit Tests (70%)      Data Quality Tests
```

## Test Organization

### Unit Tests Structure
```
tests/unit/
├── test_anthropic_client.py          # API client logic
├── test_cursor_client.py             # API client logic
├── test_transformer.py               # Data transformation
├── test_validator.py                 # Data quality logic
└── test_attribution.py               # User attribution logic
```

### Integration Tests Structure
```
tests/integration/
├── test_bigquery_operations.py       # Database operations
├── test_sheets_integration.py        # Google Sheets API
├── test_pipeline_flow.py             # End-to-end workflow
└── test_error_scenarios.py           # Failure handling
```

### Test Examples

#### Unit Test Example
```python
# tests/unit/test_anthropic_client.py
import pytest
from unittest.mock import Mock, patch
from src.ingestion.anthropic_client import AnthropicClient

class TestAnthropicClient:
    def test_fetch_daily_usage_success(self):
        client = AnthropicClient()

        with patch('requests.get') as mock_get:
            mock_get.return_value.json.return_value = {
                "data": [{"api_key_id": "test", "usage": 100}]
            }

            result = client.fetch_daily_usage("2025-09-26")

            assert result["data"][0]["api_key_id"] == "test"
            assert mock_get.called
```

#### Integration Test Example
```python
# tests/integration/test_bigquery_operations.py
import pytest
from src.storage.bigquery_client import BigQueryClient

class TestBigQueryOperations:
    def test_insert_usage_data(self):
        client = BigQueryClient(dataset="ai_usage_test")

        test_data = [
            {"usage_date": "2025-09-26", "platform": "cursor", "user_email": "test@example.com"}
        ]

        result = client.insert_usage_facts(test_data)

        assert result.errors == []
        # Verify data was inserted
        rows = client.query_table("fct_usage_daily", "usage_date = '2025-09-26'")
        assert len(rows) == 1
```

---
