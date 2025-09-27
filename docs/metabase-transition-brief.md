# Project Brief: Metabase Transition Plan

**Project:** Samba AI Usage Stats Dashboard
**Change Type:** Technical Architecture Update
**Date:** September 26, 2025
**Status:** Ready for Implementation

---

## Executive Summary

Transition from planned Looker Studio to **free self-hosted Metabase on GCP Compute Engine** for the AI usage analytics dashboard. This change maintains all PRD requirements while reducing costs, improving API capabilities, and accelerating deployment timeline from weeks to days.

**Core Value:** Same functionality, $0 licensing cost, API-driven dashboard management, faster time-to-market.

---

## What's Changing

### From: Looker Studio Approach
- Looker Studio dashboards (limited API)
- Manual configuration via UI
- Potential licensing costs
- Limited customization options

### To: Free Metabase Approach
- Self-hosted Metabase on single GCP VM
- Full REST API for "dashboards-as-code"
- $0 licensing cost (free version)
- Complete programmatic control

### What Stays the Same
✅ **All 6 dashboard types from PRD**
✅ **BigQuery data pipeline unchanged**
✅ **Export capabilities (CSV, XLSX, JSON, PNG)**
✅ **Timeline and delivery commitments**
✅ **Core functionality requirements**

---

## Technical Solution

**Architecture:** Single GCP Compute Engine VM (e2-medium, ~$25/month)
```
VM Components:
├── Metabase (Docker container)
├── PostgreSQL (metadata storage)
├── BigQuery connection (service account)
└── Monitoring & backup scripts
```

**Deployment Method:** Docker Compose for easy management
**Data Source:** BigQuery (no changes required)
**Access:** Web-based dashboards on port 3000

---

## Implementation Plan

### Week 1: Infrastructure
- [ ] GCP VM provisioning and Docker setup
- [ ] PostgreSQL configuration
- [ ] Metabase installation and testing

### Week 2: Integration
- [ ] BigQuery service account and connection
- [ ] First dashboard prototype (Finance Executive)
- [ ] API workflow validation

### Week 3-4: Dashboard Development
- [ ] Build all 6 dashboard types per PRD
- [ ] Export functionality configuration
- [ ] User management setup

### Week 5: Production Readiness
- [ ] Performance optimization
- [ ] Backup/monitoring implementation
- [ ] Documentation and team handoff

**Total Timeline:** 5 weeks (same as original Looker plan)

---

## Benefits vs Trade-offs

### ✅ **Gains**
- **Cost:** $0/month vs potential Looker licensing
- **API Control:** Full programmatic dashboard management
- **Speed:** Faster deployment (days vs weeks)
- **Flexibility:** Complete customization capability

### ⚠️ **Trade-offs**
- **User Management:** Manual (no RBAC in free version)
- **Maintenance:** VM management responsibility
- **Alerting:** Custom implementation needed
- **Support:** Community-based vs enterprise support

---

## Risk Mitigation

| **Risk** | **Impact** | **Mitigation** |
|----------|------------|----------------|
| VM downtime | Medium | Automated backups, monitoring scripts |
| Performance issues | Low | Proper VM sizing, query optimization |
| User management complexity | Low | Clear procedures, documentation |
| Learning curve | Low | Proof-of-concept validation |

---

## Success Criteria

**Technical Success:**
- [ ] All 6 dashboards operational within 5 weeks
- [ ] BigQuery query performance <5 seconds
- [ ] 99.5% uptime achievement
- [ ] Export functionality working

**Business Success:**
- [ ] Finance team independent access
- [ ] 80% reduction in manual reporting time
- [ ] Cost anomaly detection operational
- [ ] Zero licensing costs achieved

---

## Resource Requirements

**Infrastructure:** ~$25/month GCP VM costs
**Development Time:** 5 weeks (unchanged from original plan)
**Skills Needed:** Docker, GCP administration, Metabase API
**Team Impact:** Minimal - same development resources

---

## Decision Rationale

**Why This Change:**
1. **Cost Efficiency:** Eliminates potential licensing fees
2. **Technical Capability:** API-first approach enables automation
3. **Implementation Speed:** Simpler deployment model
4. **Future Flexibility:** Easy scaling and migration paths

**Why Now:**
- Before significant Looker development begins
- Minimal impact on existing BigQuery pipeline
- Maintains all delivery commitments

---

## Next Immediate Actions

1. **[ ] Stakeholder approval** for architecture change
2. **[ ] GCP resource provisioning** (VM, service accounts)
3. **[ ] Docker environment setup** on target VM
4. **[ ] BigQuery connectivity testing** with sample data
5. **[ ] First dashboard prototype** for validation

**Ready to proceed with Metabase implementation?**

---

**Document Owner:** Mary (Business Analyst)
**Technical Lead:** [To be assigned]
**Stakeholders:** Finance team (Jaya), Engineering team
**Next Review:** Post-prototype validation