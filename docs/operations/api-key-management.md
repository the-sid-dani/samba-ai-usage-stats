# API Key Management Procedures

## 🔑 Overview
Comprehensive procedures for managing API keys across Cursor, Anthropic, and Google Sheets integrations.

## 🛡️ Security Principles
1. **Principle of Least Privilege**: Keys have minimal required permissions
2. **Regular Rotation**: Monthly rotation schedule
3. **Secure Storage**: All keys stored in Google Secret Manager
4. **Access Logging**: All key usage is logged and monitored
5. **Immediate Revocation**: Compromised keys deactivated within 1 hour

---

## 📋 API Key Inventory

### Current Keys (Template)

| Platform | Key Name | Purpose | Owner | Rotation Date | Status |
|----------|----------|---------|-------|---------------|--------|
| Cursor | cursor-prod-2024-09 | Production pipeline | Data Eng | 2024-10-01 | Active |
| Anthropic | anthropic-prod-sept | Production pipeline | Data Eng | 2024-10-01 | Active |
| Google Sheets | sheets-service-2024 | User attribution | Data Eng | 2024-12-01 | Active |

### Key Permissions Required

#### Cursor API Key
- **Scope**: Team usage data read-only
- **Endpoints**: `/teams/daily-usage-data`
- **Rate Limits**: 100 requests/hour
- **Data Access**: samba.tv organization only

#### Anthropic API Key
- **Scope**: Organization usage and cost reports
- **Endpoints**: `/organizations/usage_report/messages`, `/organizations/cost_report`
- **Rate Limits**: 50 requests/hour
- **Data Access**: Organization-level aggregated data only

#### Google Sheets Service Account
- **Scope**: Read-only access to API key mapping spreadsheet
- **Permissions**: `https://www.googleapis.com/auth/spreadsheets.readonly`
- **Access**: Single spreadsheet ID only

---

## 🔄 Monthly Rotation Procedures

### Week 4 of Month: Preparation

1. **Generate New Keys**:

   **Cursor API**:
   ```bash
   # Login to Cursor Admin Portal
   # Navigate to API Keys section
   # Click "Generate New Key"
   # Copy key and save securely
   ```

   **Anthropic API**:
   ```bash
   # Login to Anthropic Console
   # Go to Organization → API Keys
   # Create new key with "Usage Reports" scope
   # Copy key and save securely
   ```

2. **Test New Keys**:
   ```bash
   # Test Cursor API
   curl -X POST https://api.cursor.com/teams/daily-usage-data \
     -u "new-cursor-key:" \
     -H "Content-Type: application/json" \
     -d '{"startDate": 1640995200000, "endDate": 1641081600000}'

   # Test Anthropic API
   curl -X GET https://api.anthropic.com/v1/organizations/usage_report/messages \
     -H "x-api-key: new-anthropic-key" \
     -H "anthropic-version: 2023-06-01"
   ```

### Week 1 of Next Month: Deployment

1. **Update Secret Manager**:
   ```bash
   # Update Cursor key
   echo "new-cursor-api-key" | gcloud secrets versions add cursor-api-key --data-file=-

   # Update Anthropic key
   echo "new-anthropic-api-key" | gcloud secrets versions add anthropic-api-key --data-file=-
   ```

2. **Verify Pipeline Health**:
   ```bash
   # Check pipeline status
   curl -X GET https://your-service-url/health

   # Run test execution
   curl -X POST https://your-service-url/run-daily-job \
     -H "Content-Type: application/json" \
     -d '{"mode": "dry_run", "days": 1}'
   ```

3. **Monitor for 48 Hours**:
   - Check pipeline execution logs
   - Verify data ingestion continues normally
   - Monitor error rates

### Week 1 of Next Month: Cleanup

1. **Deactivate Old Keys**:
   - Cursor Admin Portal → Deactivate old key
   - Anthropic Console → Delete old key
   - Update key inventory documentation

2. **Update Documentation**:
   - Record rotation date
   - Update key names in inventory
   - Note any issues encountered

---

## 🚨 Emergency Key Rotation

### Suspected Compromise

**Immediate Actions (Within 1 Hour)**:

1. **Revoke Compromised Keys**:
   ```bash
   # Immediately disable in platforms
   # Cursor: Admin Portal → API Keys → Revoke
   # Anthropic: Console → API Keys → Delete
   ```

2. **Generate Emergency Keys**:
   ```bash
   # Follow rapid generation process
   # Skip normal testing procedures if critical
   ```

3. **Deploy Emergency Keys**:
   ```bash
   # Update Secret Manager immediately
   echo "emergency-cursor-key" | gcloud secrets versions add cursor-api-key --data-file=-
   echo "emergency-anthropic-key" | gcloud secrets versions add anthropic-api-key --data-file=-
   ```

4. **Validate and Monitor**:
   - Run immediate health check
   - Monitor next pipeline execution
   - Check for unauthorized access in logs

### Post-Incident Actions

1. **Security Review**:
   - Investigate how key was compromised
   - Review access logs for unauthorized usage
   - Update security procedures if needed

2. **Cost Impact Assessment**:
   - Check for abnormal usage during compromise period
   - Calculate any excess costs incurred
   - Report to finance and security teams

---

## 📊 Google Sheets API Key Mapping

### Spreadsheet Structure

| Column | Field | Purpose | Example |
|--------|-------|---------|---------|
| A | api_key_name | Unique identifier | anthropic_prod_key_123 |
| B | user_email | User attribution | john.doe@company.com |
| C | description | Key purpose | Production Claude API - John Doe |
| D | platform | Platform identifier | anthropic |

### Adding New Users

1. **Access Spreadsheet**:
   - Open "API Key Mapping" Google Sheet
   - Use service account with read access

2. **Add New Row**:
   ```
   api_key_name: [platform]_[purpose]_[identifier]
   user_email: firstname.lastname@company.com
   description: [Platform] [Environment] - [User Name]
   platform: anthropic|cursor
   ```

3. **Validation**:
   - Ensure email format is consistent
   - Verify platform value matches expected values
   - Check for duplicate entries

4. **Pipeline Update**:
   - Changes are picked up within 24 hours
   - No manual pipeline restart required
   - Monitor attribution coverage after update

### Updating Existing Mappings

1. **Find User Row**: Search by email or API key name
2. **Update Fields**: Modify as needed
3. **Validate Changes**: Ensure data integrity
4. **Monitor Impact**: Check attribution metrics next day

### Removing Users

1. **Mark as Inactive**: Change description to include "(INACTIVE)"
2. **Preserve History**: Don't delete rows immediately
3. **Archive After 90 Days**: Move to separate sheet or delete

---

## 🔍 Monitoring Key Usage

### Daily Checks

1. **Attribution Coverage**:
   - Target: >90% of cost data attributed to users
   - Check: Cost Allocation Dashboard → Attribution Coverage metric
   - Action: Update mappings if <90%

2. **API Error Rates**:
   - Target: <5% error rate
   - Check: Pipeline logs for API failures
   - Action: Investigate if >5%

### Weekly Reviews

1. **New API Keys Detected**:
   - Review unmapped keys in dashboard
   - Add mappings for new keys
   - Investigate unauthorized keys

2. **User Activity Changes**:
   - Identify new high-usage users
   - Review cost efficiency trends
   - Update budget forecasts

### Monthly Audits

1. **Key Inventory Review**:
   - Verify all active keys are mapped
   - Remove mappings for deactivated keys
   - Update key descriptions and purposes

2. **Security Assessment**:
   - Review key access patterns
   - Identify unused or suspicious keys
   - Plan rotation schedule for next month

---

## 🛠️ Troubleshooting API Key Issues

### Key Authentication Failures

**Symptoms**:
- Pipeline logs show 401/403 errors
- Missing data for specific platform
- Dashboard shows "No data available"

**Diagnosis**:
```bash
# Check key validity
curl -X GET https://api.anthropic.com/v1/organizations/usage_report/messages \
  -H "x-api-key: your-key" \
  -H "anthropic-version: 2023-06-01"

# Expected: 200 response with data
# If 401: Key is invalid or expired
# If 403: Key lacks required permissions
```

**Solutions**:
1. Verify key is correctly stored in Secret Manager
2. Check key permissions in platform admin portal
3. Generate new key if current key is invalid
4. Update Secret Manager with new key

### Attribution Issues

**Symptoms**:
- Users showing as "Unknown" in dashboards
- Low attribution coverage (<90%)
- Cost data without user assignment

**Diagnosis**:
1. Check Google Sheets mapping completeness
2. Verify email format consistency
3. Look for new unmapped API keys

**Solutions**:
1. Add missing user mappings to Google Sheets
2. Standardize email formats across platforms
3. Run manual attribution update if needed

### Rate Limiting Issues

**Symptoms**:
- Pipeline timeouts
- 429 (Too Many Requests) errors
- Incomplete data ingestion

**Diagnosis**:
1. Review API call frequency in logs
2. Check platform rate limit documentation
3. Analyze retry logic effectiveness

**Solutions**:
1. Implement exponential backoff (already in place)
2. Reduce concurrent API calls
3. Contact platform support for quota increases

---

## 📈 Key Performance Indicators

### Operational KPIs

| Metric | Target | Measurement | Frequency |
|--------|--------|-------------|-----------|
| Key Rotation Compliance | 100% | Monthly rotations completed on time | Monthly |
| Attribution Coverage | >90% | Percentage of costs attributed to users | Daily |
| API Error Rate | <5% | Failed API calls / Total calls | Daily |
| Security Incidents | 0 | Compromised or leaked keys | Monthly |

### Business KPIs

| Metric | Target | Measurement | Frequency |
|--------|--------|-------------|-----------|
| Cost Prediction Accuracy | ±10% | Forecast vs actual monthly costs | Monthly |
| User Onboarding Time | <24 hours | Time to appear in dashboards | Per user |
| Data Freshness | <24 hours | Time since last successful pipeline run | Daily |
| Dashboard Availability | >99% | Uptime of Looker Studio dashboards | Monthly |

---

## 🔄 Annual Procedures

### Q1: Security Audit
- Review all API key permissions
- Audit user access patterns
- Update security procedures
- Penetration testing (if required)

### Q2: Performance Optimization
- Analyze dashboard query performance
- Optimize BigQuery views if needed
- Review cost allocation accuracy
- Update business logic if required

### Q3: Cost Analysis
- Annual cost trend analysis
- Budget vs actual variance review
- ROI assessment and optimization
- Platform cost-benefit analysis

### Q4: System Modernization
- Evaluate new platform integrations
- Update to latest API versions
- Review and update documentation
- Plan next year's improvements