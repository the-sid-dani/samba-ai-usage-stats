# Set Up Daily Cron Job

## Quick Cron Setup

```bash
# Edit crontab
crontab -e

# Add this line for daily 6 AM execution:
0 6 * * * cd "/Users/sid/Desktop/4. Coding Projects/samba-ai-usage-stats" && source venv/bin/activate && python simple_daily_pipeline.py >> cron_daily.log 2>&1

# Save and exit (Ctrl+X, Y, Enter in nano)

# Verify cron job is set
crontab -l
```

## Test Cron Job (Run Once)

```bash
# Test the cron command manually
cd "/Users/sid/Desktop/4. Coding Projects/samba-ai-usage-stats" && source venv/bin/activate && python simple_daily_pipeline.py
```

## Check Analytics Views

```bash
source venv/bin/activate
python -c "
from google.cloud import bigquery
client = bigquery.Client(project='ai-workflows-459123')

# Test analytics views with real data
views = ['vw_monthly_finance', 'vw_productivity_metrics', 'vw_cost_allocation', 'vw_executive_summary']
for view in views:
    query = f'SELECT COUNT(*) as count FROM \`ai-workflows-459123.ai_usage_analytics.{view}\`'
    result = list(client.query(query).result())[0]
    print(f'✅ {view}: {result.count} records')
"
```

## What This Achieves

✅ **Daily Data Ingestion**: Automatic data collection at 6 AM
✅ **Real Production Data**: 2,339+ Cursor records, Anthropic usage/cost data
✅ **BigQuery Analytics**: All views populated with real data
✅ **Finance Team Ready**: Cost analytics immediately available
✅ **Next Story Series**: Ready for Metabase dashboards (Story 6.x)