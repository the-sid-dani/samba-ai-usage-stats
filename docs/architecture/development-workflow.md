# Development Workflow

## Local Development Setup

### Prerequisites
```bash
# Install required tools
python3.11 -m pip install --upgrade pip
pip install -r requirements.txt

# Install Google Cloud CLI
curl https://sdk.cloud.google.com | bash
gcloud auth login
gcloud config set project ai-workflows-459123

# Docker for containerization
docker --version  # Ensure Docker installed
```

### Initial Setup
```bash
# Clone and setup repository
git clone https://github.com/ai-workflows-459123/samba-ai-usage-stats.git
cd samba-ai-usage-stats

# Setup virtual environment
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your local configuration

# Setup BigQuery dataset (development)
./scripts/setup_local_env.sh
```

### Development Commands
```bash
# Start local development (mock mode)
python src/main.py --mode=development --mock-apis=true

# Run with real APIs (requires credentials)
python src/main.py --mode=development

# Run data pipeline for specific date
python src/main.py --date=2025-09-26

# Run tests
./scripts/run_tests.sh

# Run specific test suite
pytest tests/unit/
pytest tests/integration/ --slow
```

## Environment Configuration

### Required Environment Variables
```bash
# Backend (.env)
GOOGLE_CLOUD_PROJECT=ai-workflows-459123
BIGQUERY_DATASET=ai_usage_dev
ANTHROPIC_ADMIN_KEY_SECRET=projects/ai-workflows-459123/secrets/anthropic-admin-key
CURSOR_API_KEY_SECRET=projects/ai-workflows-459123/secrets/cursor-api-key
GOOGLE_SHEETS_ID=your-sheets-id-here
LOG_LEVEL=INFO
ENVIRONMENT=development

# Shared
PROJECT_ID=ai-workflows-459123
REGION=us-central1
```

---
