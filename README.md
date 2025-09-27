# AI Usage Analytics Dashboard

Multi-platform AI usage and cost analytics system integrating Claude.ai, Claude Code, Claude API, and Cursor with BigQuery data warehouse and Looker dashboards.

## Development Environment Setup

### Prerequisites

- Python 3.11+ ✓
- Google Cloud CLI (installation required)
- Docker (for deployment)

### Local Setup

1. **Clone and Setup Python Environment** ✓
   ```bash
   cd samba-ai-usage-stats
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Install Google Cloud CLI** (Required)
   ```bash
   # macOS
   brew install google-cloud-sdk

   # Or download from: https://cloud.google.com/sdk/docs/install
   ```

3. **Authenticate with Google Cloud**
   ```bash
   gcloud auth login
   gcloud config set project ai-workflows-459123
   gcloud auth application-default login
   ```

4. **Create Development BigQuery Dataset**
   ```bash
   bq mk --dataset ai-workflows-459123:ai_usage_dev
   ```

5. **Configure Environment Variables**
   ```bash
   cp .env.example .env
   # Edit .env with your specific values
   ```

6. **Store API Keys in Secret Manager**
   ```bash
   # Store Anthropic API key
   echo -n "your-anthropic-api-key" | gcloud secrets create anthropic-admin-api-key --data-file=-

   # Store Cursor API key
   echo -n "your-cursor-api-key" | gcloud secrets create cursor-api-key --data-file=-
   ```

7. **Verify Setup**
   ```bash
   python scripts/verify_setup.py
   ```

### Project Structure

```
src/
├── ingestion/          # API clients for data extraction
├── processing/         # Data transformation and validation
├── storage/           # BigQuery interaction layer
├── shared/            # Common utilities and configuration
└── orchestration/     # Workflow coordination

sql/
├── tables/           # Table creation scripts
├── views/            # Analytics views for dashboards
└── migrations/       # Schema migration scripts

tests/
├── unit/             # Unit tests
├── integration/      # Integration tests
└── e2e/              # End-to-end tests

infrastructure/       # Deployment configurations
scripts/             # Development and deployment scripts
```

## Next Steps

1. Configure Google Cloud project access
2. Set up BigQuery development dataset
3. Store API credentials in Secret Manager
4. Begin Phase 1 implementation tasks

## Architecture

See `docs/architecture.md` for detailed technical architecture and implementation guidelines.