# Service Accounts - Complete Reference

**Project**: `ai-workflows-459123`
**All service accounts** used across the entire project.

---

## 📋 All Service Accounts (12 Total)

| # | Service Account | Display Name | Purpose |
|---|----------------|--------------|---------|
| 1 | `ai-usage-pipeline@ai-workflows-459123.iam.gserviceaccount.com` | AI Usage Analytics Pipeline | **Cloud Run jobs** (Claude + Cursor ingestion) |
| 2 | `ai-usage-scheduler@ai-workflows-459123.iam.gserviceaccount.com` | AI Usage Analytics Scheduler | **Cloud Scheduler** (triggers jobs) |
| 3 | `deployer-sa@ai-workflows-459123.iam.gserviceaccount.com` | Deployer SA | **Admin operations** (impersonation for deployments) |
| 4 | `metabase-bq-reader@ai-workflows-459123.iam.gserviceaccount.com` | Metabase BigQuery Reader | **Metabase→BigQuery** connection |
| 5 | `metabase-vm@ai-workflows-459123.iam.gserviceaccount.com` | Metabase VM | **GCE VM** running Metabase |
| 6 | `mcp-bigquery-reader@ai-workflows-459123.iam.gserviceaccount.com` | MCP BigQuery Reader | **MCP server** (Claude Code queries) |
| 7 | `mcp-sheets-service@ai-workflows-459123.iam.gserviceaccount.com` | MCP Sheets Service | **MCP server** (Google Sheets access) |
| 8 | `claude-drive-loader@ai-workflows-459123.iam.gserviceaccount.com` | Claude Drive Loader | **Google Drive** ingestion (if used) |
| 9 | `audience-manager-mcp@ai-workflows-459123.iam.gserviceaccount.com` | Samba AI | **Audience Manager** MCP |
| 10 | `onyxbot@ai-workflows-459123.iam.gserviceaccount.com` | OnyxBot | **Bot automation** |
| 11 | `ai-workflows-459123@appspot.gserviceaccount.com` | App Engine Default | **App Engine** (if used) |
| 12 | `201626763325-compute@developer.gserviceaccount.com` | Compute Engine Default | **GCE default** |

---

## 🎯 Usage by Component

### 1. Data Ingestion Pipelines

#### Claude Ingestion
**Cloud Run Job**: `claude-data-ingestion`
```yaml
Service Account: ai-usage-pipeline@ai-workflows-459123.iam.gserviceaccount.com
Roles:
  - secretmanager.secretAccessor (anthropic-admin-api-key)
  - bigquery.dataEditor (ai_usage_analytics dataset)
  - bigquery.jobUser
```

**Cloud Scheduler**: `claude-daily-ingestion`
```yaml
Service Account: ai-usage-scheduler@ai-workflows-459123.iam.gserviceaccount.com
Roles:
  - run.invoker (to trigger Cloud Run job)
```

#### Cursor Ingestion
**Cloud Run Job**: `cursor-daily-ingest`
```yaml
Service Account: ai-usage-pipeline@ai-workflows-459123.iam.gserviceaccount.com (SAME as Claude!)
Roles:
  - secretmanager.secretAccessor (cursor-api-key)
  - bigquery.dataEditor (ai_usage_analytics dataset)
  - bigquery.jobUser
```

**Cloud Scheduler**: `cursor-daily-ingestion` (when created)
```yaml
Service Account: ai-usage-scheduler@ai-workflows-459123.iam.gserviceaccount.com (SAME as Claude!)
Roles:
  - run.invoker
```

---

### 2. Metabase (Analytics Dashboard)

#### Metabase VM
**GCE Instance**: `metabase-vm`
```yaml
Service Account: metabase-vm@ai-workflows-459123.iam.gserviceaccount.com
Roles:
  - secretmanager.secretAccessor
  - compute.instanceAdmin
```

#### BigQuery Connection
**Metabase Database Connection**
```yaml
Service Account: metabase-bq-reader@ai-workflows-459123.iam.gserviceaccount.com
Roles:
  - bigquery.dataViewer (ai_usage_analytics dataset)
  - bigquery.jobUser
```

---

### 3. MCP Servers (Claude Code Integration)

#### BigQuery MCP
```yaml
Service Account: mcp-bigquery-reader@ai-workflows-459123.iam.gserviceaccount.com
Roles:
  - bigquery.dataViewer
  - bigquery.jobUser
Purpose: Allow Claude Code to query BigQuery via MCP
```

#### Sheets MCP
```yaml
Service Account: mcp-sheets-service@ai-workflows-459123.iam.gserviceaccount.com
Roles:
  - sheets.reader (or broader)
Purpose: Allow Claude Code to access Google Sheets via MCP
```

---

### 4. Admin & Deployment

#### Deployer SA (Admin Operations)
```yaml
Service Account: deployer-sa@ai-workflows-459123.iam.gserviceaccount.com
Roles:
  - Owner (or broad permissions for infrastructure provisioning)
Usage:
  - Impersonation for gcloud commands
  - Terraform deployments
  - Infrastructure changes

Commands:
  gcloud ... --impersonate-service-account=deployer-sa@ai-workflows-459123.iam.gserviceaccount.com
  gcloud auth application-default login --impersonate-service-account=deployer-sa@...
```

---

## 🔑 Secrets & Service Accounts Mapping

| Secret Name | Service Account with Access | Purpose |
|-------------|----------------------------|---------|
| `anthropic-admin-api-key` | `ai-usage-pipeline` | Claude API access |
| `cursor-api-key` | `ai-usage-pipeline` | Cursor API access |
| `sheets-service-account-key` | `ai-usage-pipeline` | Google Sheets access |
| `metabase-bigquery-service-account` | `metabase-vm` | Metabase BQ connection |
| `metabase-bigquery-project` | `metabase-vm` | BQ project ID |
| `metabase-bigquery-dataset` | `metabase-vm` | BQ dataset name |

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA INGESTION LAYER                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Cloud Scheduler                                            │
│  ├─ claude-daily-ingestion                                  │
│  │  └─ SA: ai-usage-scheduler                               │
│  │     └─ Triggers →                                        │
│  │        Cloud Run Job: claude-data-ingestion              │
│  │        └─ SA: ai-usage-pipeline                          │
│  │           ├─ Reads: anthropic-admin-api-key (Secret Mgr) │
│  │           └─ Writes: claude_costs, claude_usage_keys,    │
│  │                      claude_code_productivity (BigQuery) │
│  │                                                           │
│  └─ cursor-daily-ingestion (same pattern)                   │
│     └─ SA: ai-usage-scheduler                               │
│        └─ Triggers →                                         │
│           Cloud Run Job: cursor-daily-ingest                │
│           └─ SA: ai-usage-pipeline (SHARED!)                │
│              ├─ Reads: cursor-api-key (Secret Mgr)          │
│              └─ Writes: cursor_daily_metrics (BigQuery)     │
│                                                              │
└──────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   ANALYTICS/QUERY LAYER                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Metabase (GCE VM)                                          │
│  ├─ VM SA: metabase-vm                                      │
│  │  └─ Reads: metabase-* secrets from Secret Manager       │
│  │                                                           │
│  └─ BigQuery Connection                                     │
│     └─ SA: metabase-bq-reader                               │
│        └─ Reads: ai_usage_analytics.* (BigQuery)            │
│                                                              │
│  MCP Servers (Claude Code)                                  │
│  ├─ BigQuery MCP                                            │
│  │  └─ SA: mcp-bigquery-reader                              │
│  │     └─ Reads: ai_usage_analytics.* (BigQuery)            │
│  │                                                           │
│  └─ Sheets MCP                                              │
│     └─ SA: mcp-sheets-service                               │
│        └─ Reads: Google Sheets                              │
│                                                              │
└──────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  ADMIN/DEPLOYMENT LAYER                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  deployer-sa                                                │
│  └─ Used for: Infrastructure provisioning, deployments      │
│     └─ Access: Owner-level (broad permissions)             │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 💡 Key Design Decisions

### Why SHARED Pipeline SA?

Both **Claude** and **Cursor** ingestion use the **SAME** service account:
```
ai-usage-pipeline@ai-workflows-459123.iam.gserviceaccount.com
```

**Why?**
- ✅ Same purpose (data ingestion)
- ✅ Same permissions needed (Secret Manager + BigQuery)
- ✅ Easier management (one SA to maintain)
- ✅ Follows principle of "group by function, not by source"

**Permissions granted ONCE**, used by BOTH jobs.

### Why SHARED Scheduler SA?

Both schedulers use the **SAME** service account:
```
ai-usage-scheduler@ai-workflows-459123.iam.gserviceaccount.com
```

**Why?**
- ✅ Same purpose (trigger Cloud Run jobs)
- ✅ Same permission needed (run.invoker)
- ✅ Simpler IAM management

---

## 🔐 Permissions Matrix

| Service Account | Secret Manager | BigQuery | Cloud Run | Compute Engine | Sheets |
|----------------|----------------|----------|-----------|----------------|--------|
| `ai-usage-pipeline` | ✅ Read (API keys) | ✅ Write (analytics) | - | - | - |
| `ai-usage-scheduler` | - | - | ✅ Invoke jobs | - | - |
| `deployer-sa` | ✅ Admin | ✅ Admin | ✅ Admin | ✅ Admin | ✅ Admin |
| `metabase-bq-reader` | - | ✅ Read only | - | - | - |
| `metabase-vm` | ✅ Read (config) | - | - | ✅ VM access | - |
| `mcp-bigquery-reader` | - | ✅ Read only | - | - | - |
| `mcp-sheets-service` | - | - | - | - | ✅ Read |

---

## 📝 Quick Reference Commands

### List all service accounts
```bash
gcloud iam service-accounts list --project=ai-workflows-459123
```

### Check specific SA permissions
```bash
# Pipeline SA
gcloud projects get-iam-policy ai-workflows-459123 \
  --flatten="bindings[].members" \
  --format="table(bindings.role)" \
  --filter="bindings.members:ai-usage-pipeline@"

# Scheduler SA
gcloud projects get-iam-policy ai-workflows-459123 \
  --flatten="bindings[].members" \
  --format="table(bindings.role)" \
  --filter="bindings.members:ai-usage-scheduler@"
```

### Check Secret access
```bash
gcloud secrets get-iam-policy anthropic-admin-api-key --project=ai-workflows-459123
gcloud secrets get-iam-policy cursor-api-key --project=ai-workflows-459123
```

---

## 🎯 Service Accounts for This Project

### Primary (Most Important)

**For Data Ingestion (Both Claude + Cursor):**
- `ai-usage-pipeline@ai-workflows-459123.iam.gserviceaccount.com`
- `ai-usage-scheduler@ai-workflows-459123.iam.gserviceaccount.com`

**For Admin/Deployment:**
- `deployer-sa@ai-workflows-459123.iam.gserviceaccount.com`

**For Analytics:**
- `metabase-bq-reader@ai-workflows-459123.iam.gserviceaccount.com`

### Secondary (Supporting)

- `metabase-vm@...` - VM operations
- `mcp-bigquery-reader@...` - Claude Code MCP queries
- `mcp-sheets-service@...` - Sheets MCP access

---

## 🚀 For Your Deployments

### When deploying Claude ingestion:
```bash
# Uses these 2 service accounts:
# 1. ai-usage-pipeline (Cloud Run job runtime)
# 2. ai-usage-scheduler (Cloud Scheduler trigger)
./infrastructure/cloud_run/deploy-claude-ingestion.sh
```

### When deploying Cursor ingestion:
```bash
# Uses SAME 2 service accounts:
# 1. ai-usage-pipeline (Cloud Run job runtime)
# 2. ai-usage-scheduler (Cloud Scheduler trigger)
./infrastructure/cloud_run/deploy-cursor-ingestion.sh
```

### When running BigQuery queries:
```bash
# Uses YOUR user account (sid.dani@samba.tv) by default
bq query "SELECT * FROM ai_usage_analytics.claude_costs LIMIT 10"

# OR impersonate deployer-sa for admin operations
gcloud ... --impersonate-service-account=deployer-sa@ai-workflows-459123.iam.gserviceaccount.com
```

---

## ✅ Summary

**For this Claude/Cursor ingestion project, you only need to know about:**

1. **`ai-usage-pipeline`** - Runs the Cloud Run jobs (both Claude + Cursor)
2. **`ai-usage-scheduler`** - Triggers the jobs daily

**Everything else** (metabase-*, mcp-*, deployer-sa) is for other parts of your infrastructure.

**Both ingestion pipelines share the same 2 service accounts!** ✅
