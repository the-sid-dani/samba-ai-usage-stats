# Incident Response Playbook
**AI Usage Analytics Dashboard - Production Operations**

## Quick Reference

| Severity | Response Time | Escalation | Communication |
|----------|---------------|------------|---------------|
| P0 - Critical | 5 minutes | Immediate | All stakeholders |
| P1 - High | 15 minutes | 30 minutes | Engineering + Finance |
| P2 - Medium | 1 hour | 4 hours | Engineering team |
| P3 - Low | Next business day | As needed | Engineering team |

**Emergency Contacts:**
- Engineering On-Call: `engineering-oncall@samba.tv`
- Security Team: `security@samba.tv`
- Finance Team: `finance@samba.tv`
- System Administrator: `sysadmin@samba.tv`

---

## Incident Classification Framework

### P0 - Critical (Complete System Outage)
**Characteristics:**
- Complete pipeline failure for >2 hours
- Financial data corruption or loss
- Security breach with data exposure
- All monitoring dashboards unavailable

**Response Requirements:**
- **Response Time:** 5 minutes
- **Incident Commander:** Engineering Lead
- **Communication:** Immediate notification to all stakeholders
- **War Room:** Required for incidents >1 hour

### P1 - High (Significant Service Degradation)
**Characteristics:**
- Partial pipeline failure affecting >50% of data
- Monitoring system failure
- API authentication failures across multiple services
- Data quality validation failures >20%

**Response Requirements:**
- **Response Time:** 15 minutes
- **Escalation:** 30 minutes if not contained
- **Communication:** Engineering team + Finance team notification
- **Review:** Post-incident review required

### P2 - Medium (Limited Impact)
**Characteristics:**
- Single API service degradation
- Performance issues not affecting core functionality
- Non-critical monitoring alerts
- Data quality issues 5-20% range

**Response Requirements:**
- **Response Time:** 1 hour
- **Escalation:** 4 hours if not resolved
- **Communication:** Engineering team only
- **Review:** Weekly review cycle

---

## Incident Response Procedures

### Initial Response (First 5 Minutes)

1. **Acknowledge Alert**
   ```bash
   # Check system health dashboard
   https://metabase.samba.tv/dashboard/system-health

   # Verify monitoring status
   gcloud logging read "resource.type=cloud_function" --limit=10
   ```

2. **Assess Impact**
   - Check overall system health score
   - Identify affected components
   - Estimate user/financial impact
   - Determine severity level

3. **Initial Communication**
   ```markdown
   Subject: [INCIDENT-${SEVERITY}] ${BRIEF_DESCRIPTION}

   Incident ID: INC-${TIMESTAMP}
   Severity: ${P0/P1/P2/P3}
   Status: Investigating
   Impact: ${DESCRIPTION}
   ETA: ${INITIAL_ESTIMATE}

   Updates will follow every 30 minutes.
   ```

### Investigation Procedures

#### Data Pipeline Failures
```bash
# 1. Check pipeline execution logs
gcloud logging read "resource.type=cloud_function AND jsonPayload.operation=run_daily_job" --limit=5

# 2. Verify API connectivity
curl -H "x-api-key: ${ANTHROPIC_KEY}" https://api.anthropic.com/v1/usage
curl -H "Authorization: Basic ${CURSOR_KEY}" https://api.cursor.sh/v1/usage

# 3. Check BigQuery status
bq query --use_legacy_sql=false 'SELECT COUNT(*) FROM `ai-workflows-459123.ai_usage_prod.fct_usage_daily` WHERE DATE(usage_date) = CURRENT_DATE()'

# 4. Review circuit breaker status
# Access system health dashboard for circuit breaker states
```

#### Monitoring System Failures
```bash
# 1. Check Cloud Monitoring status
gcloud alpha monitoring policies list

# 2. Verify alert policy status
gcloud alpha monitoring channels list

# 3. Test metric ingestion
# Execute health check endpoint manually
```

#### Security Incidents
```bash
# 1. Check audit logs for unauthorized access
gcloud logging read "protoPayload.methodName=google.iam.admin.v1.IAMService.CreateServiceAccount" --limit=10

# 2. Verify secret access patterns
gcloud logging read "jsonPayload.event_type=secret_access" --limit=20

# 3. Review API key rotation status
# Check compliance dashboard for rotation schedule
```

### Recovery Procedures

#### Automated Recovery Activation
```python
# Use recovery manager for automated workflows
from src.orchestration.recovery_manager import recovery_manager

# Initiate API outage recovery
recovery_op = recovery_manager.initiate_recovery(
    scenario=FailureScenario.API_OUTAGE,
    component="anthropic",
    failure_context={"detected_at": datetime.now()}
)

# Monitor recovery progress
status = recovery_manager.get_recovery_status_report()
```

#### Manual Recovery Steps

1. **Circuit Breaker Reset**
   ```python
   from src.shared.circuit_breaker import circuit_breaker_manager

   # Check circuit status
   status = circuit_breaker_manager.get_all_statuses()

   # Reset specific circuit
   circuit_breaker_manager.reset_circuit_breaker("anthropic_api")
   ```

2. **Pipeline Restart**
   ```bash
   # Trigger manual pipeline execution
   gcloud run services update ai-usage-pipeline --region=us-central1

   # Monitor execution
   gcloud logging tail "resource.type=cloud_run_revision"
   ```

3. **Service Restoration**
   ```bash
   # Restart Cloud Run service
   gcloud run deploy ai-usage-analytics \
     --source . \
     --region us-central1 \
     --allow-unauthenticated=false
   ```

---

## Communication Procedures

### Stakeholder Notification Templates

#### P0/P1 Critical Incident
```markdown
🚨 CRITICAL INCIDENT NOTIFICATION

Incident: [INC-${ID}] ${DESCRIPTION}
Severity: ${LEVEL}
Start Time: ${TIMESTAMP}
Status: ${INVESTIGATING/IDENTIFIED/RESOLVING/RESOLVED}

IMPACT:
- Affected Services: ${SERVICES}
- User Impact: ${DESCRIPTION}
- Financial Impact: ${ESTIMATE}

CURRENT ACTIONS:
- ${ACTION_1}
- ${ACTION_2}

ETA TO RESOLUTION: ${ESTIMATE}
Next Update: ${TIME}

Incident Commander: ${NAME}
War Room: ${ZOOM_LINK}
```

#### Resolution Notification
```markdown
✅ INCIDENT RESOLVED

Incident: [INC-${ID}] ${DESCRIPTION}
Resolution Time: ${TIMESTAMP}
Total Duration: ${MINUTES} minutes

RESOLUTION SUMMARY:
- Root Cause: ${CAUSE}
- Fix Applied: ${SOLUTION}
- Validation: ${VERIFICATION}

FOLLOW-UP ACTIONS:
- Post-incident review scheduled for ${DATE}
- Monitoring enhancements: ${IMPROVEMENTS}

Questions? Contact: ${INCIDENT_COMMANDER}
```

### Escalation Matrix

| Time Since Detection | Action Required |
|---------------------|-----------------|
| 0-5 minutes | Initial response and assessment |
| 5-15 minutes | Technical investigation begins |
| 15-30 minutes | Management notification (P0/P1) |
| 30-60 minutes | War room activation (P0) |
| 1-2 hours | Executive notification (P0) |
| 2+ hours | External communication planning |

---

## Post-Incident Procedures

### Immediate Actions (Within 24 Hours)
1. **Incident Timeline Documentation**
   - Complete incident record in operational metrics
   - Document all actions taken and decisions made
   - Record actual vs estimated resolution time

2. **Initial Impact Assessment**
   - Calculate financial impact of outage
   - Assess data integrity and completeness
   - Document user experience impact

### Post-Incident Review (Within 72 Hours)
1. **Root Cause Analysis**
   - Technical failure analysis
   - Process failure identification
   - Contributing factor assessment

2. **Improvement Actions**
   - Technical debt identification
   - Process improvement recommendations
   - Monitoring enhancement suggestions

3. **Knowledge Sharing**
   - Update troubleshooting documentation
   - Share lessons learned with team
   - Update training materials if needed

### Operational Excellence Tracking
```sql
-- Query operational metrics for review
SELECT
  incident_id,
  severity_level,
  mttr_minutes,
  root_cause_category,
  resolution_time
FROM operational_metrics
WHERE DATE(detection_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
ORDER BY detection_time DESC;
```

---

## Key Operational Contacts

| Role | Primary | Secondary | Phone |
|------|---------|-----------|--------|
| Engineering Lead | engineering-lead@samba.tv | alt-eng@samba.tv | +1-XXX-XXX-XXXX |
| System Administrator | sysadmin@samba.tv | backup-admin@samba.tv | +1-XXX-XXX-XXXX |
| Security Team | security@samba.tv | sec-oncall@samba.tv | +1-XXX-XXX-XXXX |
| Finance Team | finance@samba.tv | finance-backup@samba.tv | +1-XXX-XXX-XXXX |

**Emergency Escalation:** Call Engineering Lead directly for P0 incidents

---

*Last Updated: September 27, 2025*
*Version: 2.0 (Production Hardening Update)*