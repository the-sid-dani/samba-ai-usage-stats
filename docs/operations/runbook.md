# AI Usage Analytics - Operations Runbook

## 🎯 Purpose
This runbook provides step-by-step procedures for operating, monitoring, and troubleshooting the AI Usage Analytics Dashboard system.

## 👥 Audience
- **Primary**: Finance Team (Jaya)
- **Secondary**: Data Engineering Team
- **Emergency**: System Administrators

---

## 📊 Daily Operations

### Morning Health Check (9 AM Daily)

1. **Check Pipeline Status**
   ```bash
   # View yesterday's pipeline execution
   gcloud logs read 'resource.type=cloud_run_revision AND jsonPayload.message:"Pipeline execution completed"' \
     --since="24h" --limit=5 --project=your-project-id
   ```

2. **Verify Data Freshness**
   - Open Looker Studio Executive Dashboard
   - Check "Last Data Refresh" indicator
   - **Expected**: <24 hours old
   - **Action if stale**: See [Data Pipeline Troubleshooting](#data-pipeline-troubleshooting)

3. **Review Cost Alerts**
   - Check email for cost variance alerts (>20% increase)
   - Review monthly spend trends in Finance Dashboard
   - **Action if high costs**: See [Cost Management](#cost-management)

### Weekly Review (Monday 10 AM)

1. **Data Quality Assessment**
   - Review Attribution Coverage metrics
   - Check for missing user mappings
   - Validate platform data completeness

2. **Performance Review**
   - Dashboard load times (<5 seconds target)
   - Pipeline execution time (<10 minutes target)
   - API error rates (<5% threshold)

---

## 🚨 Alert Response Procedures

### Critical Alerts (Immediate Response Required)

#### Pipeline Failure Alert
**Trigger**: Pipeline fails for 2+ consecutive days

**Response Steps**:
1. Check Cloud Run service status
2. Review error logs
3. Verify API key validity
4. Contact Data Engineering if unresolved within 2 hours

#### Data Freshness Alert
**Trigger**: No new data for >48 hours

**Response Steps**:
1. Check external API status (Cursor, Anthropic)
2. Verify service account permissions
3. Manually trigger pipeline if APIs are healthy

#### Cost Spike Alert
**Trigger**: Monthly costs increase >50% from previous month

**Response Steps**:
1. Review user activity in Cost Allocation Dashboard
2. Check for new high-usage API keys
3. Investigate potential API abuse
4. Escalate to management if costs >$10,000/month

### Warning Alerts (4-hour Response Window)

#### Attribution Coverage Low
**Trigger**: <80% user attribution for new data

**Response Steps**:
1. Update Google Sheets API key mapping
2. Add missing user email mappings
3. Re-run pipeline for affected dates

#### Query Performance Degraded
**Trigger**: Dashboard queries >10 seconds

**Response Steps**:
1. Check BigQuery slot usage
2. Review query patterns in monitoring
3. Consider view optimizations

---

## 🔧 Troubleshooting Guides

### Data Pipeline Troubleshooting

#### Symptom: Pipeline Not Running
**Diagnosis Steps**:
1. Check Cloud Scheduler status:
   ```bash
   gcloud scheduler jobs describe daily-usage-analytics --location=us-central1
   ```
2. Verify Cloud Run service is deployed
3. Check service account permissions

**Common Fixes**:
- Restart Cloud Scheduler job
- Redeploy Cloud Run service
- Verify IAM roles are correct

#### Symptom: Partial Data Missing
**Diagnosis Steps**:
1. Check specific API client logs
2. Verify API key validity
3. Review rate limiting logs

**Common Fixes**:
- Rotate expired API keys
- Adjust retry logic parameters
- Contact API provider for quota increases

#### Symptom: Data Quality Issues
**Diagnosis Steps**:
1. Run data validation queries
2. Check user attribution coverage
3. Review transformation error logs

**Common Fixes**:
- Update Google Sheets user mappings
- Fix email format inconsistencies
- Re-run pipeline for specific date ranges

### Dashboard Troubleshooting

#### Symptom: Dashboard Won't Load
**Diagnosis Steps**:
1. Check BigQuery view permissions
2. Verify Looker Studio data source connection
3. Test view queries directly in BigQuery

**Common Fixes**:
- Refresh Looker Studio data source
- Re-authenticate BigQuery connection
- Recreate views if schema changed

#### Symptom: Incorrect Data in Dashboard
**Diagnosis Steps**:
1. Compare dashboard data with raw BigQuery tables
2. Check view logic for calculation errors
3. Verify date range filters

**Common Fixes**:
- Refresh dashboard data
- Update view definitions if business logic changed
- Clear Looker Studio cache

---

## 🔑 API Key Management

### Monthly API Key Rotation

1. **Generate New Keys**:
   - Cursor: Admin Panel → API Keys → Generate New
   - Anthropic: Console → Organization → API Keys → Create

2. **Update Secret Manager**:
   ```bash
   # Update Cursor API key
   echo "new-cursor-key" | gcloud secrets versions add cursor-api-key --data-file=-

   # Update Anthropic API key
   echo "new-anthropic-key" | gcloud secrets versions add anthropic-api-key --data-file=-
   ```

3. **Test New Keys**:
   ```bash
   # Test pipeline with new keys
   curl -X POST https://your-service-url/health
   ```

4. **Deactivate Old Keys**:
   - Wait 24 hours after successful testing
   - Deactivate old keys in respective admin panels

### Google Sheets User Mapping Management

1. **Add New User**:
   - Open API Key Mapping spreadsheet
   - Add row: [api_key_name, user_email, description, platform]
   - Pipeline will pick up changes within 24 hours

2. **Update Existing Mapping**:
   - Edit existing row in spreadsheet
   - Verify email format is correct
   - Monitor attribution coverage after update

---

## 📈 Monitoring and Alerting

### Key Metrics to Monitor

#### System Health
- **Pipeline Success Rate**: >95%
- **Data Freshness**: <24 hours
- **API Error Rate**: <5%
- **Query Performance**: <5 seconds

#### Business Metrics
- **Monthly Cost Trends**: Track month-over-month changes
- **User Adoption**: Active users per platform
- **Productivity Metrics**: Lines accepted, acceptance rates
- **Attribution Coverage**: >90% target

### Monitoring Dashboards

1. **Executive Dashboard** (Finance Team)
   - Monthly cost summaries
   - Growth trends and forecasts
   - ROI metrics

2. **Operations Dashboard** (Engineering Team)
   - Pipeline health status
   - Data quality metrics
   - Performance indicators

3. **Cost Allocation Dashboard** (Team Leads)
   - User-level cost breakdowns
   - Team productivity metrics
   - Efficiency comparisons

---

## 🆘 Emergency Procedures

### Data Loss or Corruption
**Severity**: Critical

**Immediate Actions**:
1. Stop all data pipelines
2. Identify scope of data impact
3. Restore from BigQuery backups if needed
4. Contact Data Engineering team immediately

### Security Incident
**Severity**: Critical

**Immediate Actions**:
1. Rotate all API keys immediately
2. Review access logs for suspicious activity
3. Disable compromised service accounts
4. Contact Security team

### Cost Anomaly (>$5,000 unexpected)
**Severity**: High

**Immediate Actions**:
1. Review Cost Allocation Dashboard for source
2. Check for API abuse or runaway processes
3. Temporarily disable high-cost API keys if needed
4. Escalate to Finance and Engineering leadership

---

## 🔄 Maintenance Schedule

### Daily (Automated)
- Pipeline execution at 6 AM PST
- Health checks every 30 seconds
- Error log aggregation

### Weekly (Manual - Monday 10 AM)
- Review data quality metrics
- Check attribution coverage
- Validate dashboard performance
- Review cost trends

### Monthly (Manual - 1st of month)
- API key rotation
- User access review
- Performance optimization review
- Cost budget vs actual analysis

### Quarterly (Manual)
- Disaster recovery testing
- Security audit
- Dependency updates
- User training refresh

---

## 📞 Escalation Paths

### Tier 1: Finance Team Self-Service
**Scope**: Dashboard usage, report generation, data interpretation
**Contact**: Internal team resources, this runbook

### Tier 2: Data Engineering Support
**Scope**: Data quality issues, pipeline problems, new user onboarding
**Contact**: data-engineering@company.com
**SLA**: 4 hours response, 24 hours resolution

### Tier 3: Platform Engineering
**Scope**: Infrastructure issues, security incidents, major system failures
**Contact**: platform-team@company.com
**SLA**: 1 hour response, 8 hours resolution

### Emergency Escalation
**Scope**: Security breaches, data loss, critical business impact
**Contact**:
- Director of Engineering: engineering-director@company.com
- CTO: cto@company.com
**SLA**: Immediate response required

---

## 📚 Additional Resources

- [User Guide](./user-guide.md) - Dashboard navigation and report generation
- [API Key Management](./api-key-management.md) - Detailed key rotation procedures
- [Troubleshooting Guide](./troubleshooting.md) - Extended troubleshooting scenarios
- [Backup and Recovery](./backup-recovery.md) - Disaster recovery procedures
- [Architecture Overview](../architecture/) - Technical system documentation