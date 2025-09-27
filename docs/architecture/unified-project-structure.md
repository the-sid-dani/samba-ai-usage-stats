# Unified Project Structure

```plaintext
samba-ai-usage-stats/
├── .github/                           # CI/CD workflows
│   └── workflows/
│       ├── ci.yaml                    # Testing and validation
│       └── deploy.yaml                # Cloud Run deployment
├── src/                               # Python application code
│   ├── ingestion/                     # API client modules
│   │   ├── __init__.py
│   │   ├── anthropic_client.py        # Anthropic API integration
│   │   ├── cursor_client.py           # Cursor API integration
│   │   └── sheets_client.py           # Google Sheets connector
│   ├── processing/                    # Data transformation logic
│   │   ├── __init__.py
│   │   ├── transformer.py             # Raw data normalization
│   │   ├── validator.py               # Data quality checks
│   │   └── attribution.py            # User attribution logic
│   ├── storage/                       # BigQuery interaction
│   │   ├── __init__.py
│   │   ├── bigquery_client.py         # BigQuery operations
│   │   └── schema_manager.py          # Table creation/updates
│   ├── shared/                        # Common utilities
│   │   ├── __init__.py
│   │   ├── config.py                  # Configuration management
│   │   ├── logging_setup.py           # Structured logging
│   │   ├── models.py                  # Data models/types
│   │   └── utils.py                   # Helper functions
│   ├── orchestration/                 # Workflow coordination
│   │   ├── __init__.py
│   │   ├── daily_job.py               # Main pipeline orchestrator
│   │   └── health_check.py            # Health monitoring
│   └── main.py                        # Cloud Run entry point
├── sql/                               # BigQuery schema definitions
│   ├── tables/                        # Table creation scripts
│   │   ├── raw_tables.sql
│   │   ├── curated_tables.sql
│   │   └── dimension_tables.sql
│   ├── views/                         # Analytics views
│   │   ├── monthly_finance.sql
│   │   ├── productivity_metrics.sql
│   │   └── cost_allocation.sql
│   └── migrations/                    # Schema migration scripts
│       └── 001_initial_schema.sql
├── tests/                             # Test suite
│   ├── unit/                          # Unit tests
│   │   ├── test_anthropic_client.py
│   │   ├── test_cursor_client.py
│   │   └── test_transformer.py
│   ├── integration/                   # Integration tests
│   │   ├── test_bigquery_ops.py
│   │   └── test_end_to_end.py
│   ├── fixtures/                      # Test data
│   │   ├── sample_anthropic_response.json
│   │   └── sample_cursor_response.json
│   └── conftest.py                    # pytest configuration
├── infrastructure/                    # Deployment configurations
│   ├── cloud_run/
│   │   ├── service.yaml               # Cloud Run service definition
│   │   └── job.yaml                   # Cloud Run job definition
│   ├── bigquery/
│   │   ├── dataset.yaml               # Dataset configuration
│   │   └── permissions.yaml           # IAM permissions
│   └── terraform/                     # Optional IaC (if needed)
│       ├── main.tf
│       └── variables.tf
├── scripts/                           # Utility scripts
│   ├── setup_local_env.sh             # Local development setup
│   ├── deploy.sh                      # Deployment helper
│   ├── run_tests.sh                   # Test execution
│   └── backfill_data.py               # Historical data loading
├── docs/                              # Documentation
│   ├── prd.md                         # Product requirements
│   ├── architecture.md                # This document
│   ├── api_integration.md             # API documentation
│   └── runbook.md                     # Operations guide
├── .env.example                       # Environment variables template
├── .gitignore                         # Git exclusions
├── .dockerignore                      # Docker exclusions
├── Dockerfile                         # Container definition
├── requirements.txt                   # Python dependencies
├── pytest.ini                        # Test configuration
├── pyproject.toml                     # Python project metadata
└── README.md                          # Project overview
```

**Key Organizational Principles:**
- **Separation by function**: Ingestion, processing, storage, orchestration clearly separated
- **Shared utilities**: Common code in `/shared` prevents duplication
- **SQL as code**: Version-controlled schema definitions and views
- **Infrastructure as code**: Deployment configurations tracked in git
- **Test organization**: Unit, integration, and fixtures clearly organized

---
