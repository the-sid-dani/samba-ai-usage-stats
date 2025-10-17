# GCP Admin Request - Storage Policy Exception

## What I Need

**Temporarily disable the storage soft delete policy for my project so I can deploy a data pipeline to Cloud Run.**

## The Problem

My project `ai-workflows-459123` is blocked by this organizational policy:
- **Policy**: `constraints/storage.softDeletePolicySeconds = 604800` (7 days)
- **Error**: `'604800' violates constraint 'constraints/storage.softDeletePolicySeconds'`

This policy prevents me from:
- Building Docker images with Cloud Build
- Pushing containers to Container Registry or Artifact Registry
- Deploying to Cloud Run

## What I'm Building

A **data analytics pipeline** that:
- Collects usage data from APIs (Cursor, Anthropic)
- Stores it in BigQuery for cost analysis
- Runs daily via Cloud Run + Cloud Scheduler

**Business Purpose**: Track AI tool usage costs across our 76+ engineers.

## What I Need You To Do

**Option 1: Temporary Exception (Preferred)**
1. Go to **IAM & Admin** → **Organization Policies**
2. Find policy: `constraints/storage.softDeletePolicySeconds`
3. **Add my project as exception**: `ai-workflows-459123`
4. Set to **"Not enforced"** for my project only
5. I'll deploy this week, then you can remove the exception

**Option 2: Temporary Disable**
1. Same policy: `constraints/storage.softDeletePolicySeconds`
2. Set to **"Not enforced"** organization-wide
3. I deploy (takes 1 hour)
4. You re-enable it immediately after

**Option 3: Grant Different Permissions**
If policy can't be changed, grant my service account these roles:
- `roles/storage.objectAdmin`
- `roles/artifactregistry.admin`
- `roles/cloudbuild.builds.builder`

## Timeline

**This Week**: Deploy pipeline
**Next Week**: Remove exception/restore policy

## Contact

Slack me if you need clarification. This is blocking our finance team from getting AI cost analytics.

---

**Bottom Line**: I need to push Docker containers to deploy a data pipeline. The 7-day storage retention policy is preventing this. Need temporary exception for project `ai-workflows-459123`.