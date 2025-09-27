# Deployment Architecture

## Deployment Strategy

**Data Pipeline Deployment:**
- **Platform:** Google Cloud Run (serverless containers)
- **Build Command:** `docker build -t gcr.io/ai-workflows-459123/ai-usage-ingestion .`
- **Deployment Method:** Automated via GitHub Actions with Cloud Build
- **Scheduling:** Cloud Scheduler triggers daily at 6 AM PT

**BigQuery Deployment:**
- **Schema Management:** SQL scripts applied via migration pipeline
- **View Updates:** Automated refresh during deployment
- **Data Retention:** Automatic partition lifecycle management

## CI/CD Pipeline
```yaml
# .github/workflows/deploy.yaml
name: Deploy AI Usage Pipeline

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Run tests
        run: |
          pip install -r requirements.txt
          pytest tests/unit/

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup gcloud
        uses: google-github-actions/setup-gcloud@v1
        with:
          project_id: ai-workflows-459123
          service_account_key: ${{ secrets.GCP_SA_KEY }}

      - name: Build and push image
        run: |
          docker build -t gcr.io/ai-workflows-459123/ai-usage-ingestion .
          docker push gcr.io/ai-workflows-459123/ai-usage-ingestion

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy ai-usage-pipeline \
            --image gcr.io/ai-workflows-459123/ai-usage-ingestion \
            --platform managed \
            --region us-central1 \
            --no-allow-unauthenticated
```

## Environments
| Environment | Purpose | BigQuery Dataset | Cloud Run Service |
|-------------|---------|------------------|-------------------|
| Development | Local testing | `ai_usage_dev` | Local container |
| Staging | Pre-production validation | `ai_usage_staging` | `ai-usage-pipeline-staging` |
| Production | Live data processing | `ai_usage` | `ai-usage-pipeline` |

---
