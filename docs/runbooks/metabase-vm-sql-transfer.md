# Metabase VM — Copying SQL Assets

You’ll see the `Permission denied (publickey)` error if you run `rsync` or `scp` *from the VM itself*. The command in the main runbook is meant to be executed from your laptop (or Cloud Shell) where the repo lives. The VM tries to SSH back into itself but doesn’t have the right key, so the transfer fails.

Use one of the options below depending on where you are running the command.

## Option A — From your laptop (preferred)
1. Open a terminal on the machine that has this repo (`sql/dashboard/ai_cost/`).
2. Run the `rsync` command there (replace `<user>` and `<vm-host>`):
   ```bash
   rsync -av "sql/dashboard/ai_cost/" <user>@<vm-host>:/tmp/metabase-assets/sql/dashboard/ai_cost/
   ```
3. Accept the host fingerprint once. The files will land on the VM under `/tmp/metabase-assets/sql/dashboard/ai_cost/`.

## Option B — From the VM (no local copy available)
If you’re SSH’d into `root@metabase-vm` and don’t have the repo on that machine:

1. Create the target directory (idempotent):
   ```bash
   install -d -m 0755 /tmp/metabase-assets/sql/dashboard/ai_cost
   ```
2. Paste each SQL file manually using heredocs. Example for the first KPI query:
   ```bash
   tee /tmp/metabase-assets/sql/dashboard/ai_cost/01_kpi_total_cost.sql > /dev/null <<'SQL'
   -- AI Cost Dashboard KPI: Q4 Total Cost (returns overall + provider breakdown)
   WITH params AS (
     SELECT
       COALESCE({{date_range.start}}, DATE '2025-10-01') AS start_date,
       COALESCE({{date_range.end}}, DATE '2025-12-31') AS end_date
   ),
   filtered AS (
     SELECT c.*
     FROM params p
     JOIN `ai_usage_analytics.vw_combined_daily_costs` c
       ON c.cost_date BETWEEN p.start_date AND p.end_date
   )
   SELECT
     ROUND(SUM(amount_usd), 2) AS total_cost_usd,
     ROUND(SUM(IF(provider = 'claude_api', amount_usd, 0)), 2) AS claude_api_cost_usd,
     ROUND(SUM(IF(provider = 'claude_code', amount_usd, 0)), 2) AS claude_code_cost_usd,
     ROUND(SUM(IF(provider = 'cursor', amount_usd, 0)), 2) AS cursor_cost_usd
   FROM filtered;
   SQL
   ```
3. Repeat for any other SQL files you want to include (e.g., `02_kpi_daily_average.sql`, etc.). You can copy the contents directly from the repo’s `sql/dashboard/ai_cost/` folder.

## Option C — Clone the repo on the VM
If the VM has outbound internet access:
1. From `root@metabase-vm`, clone your repo (HTTPS):
   ```bash
   git clone https://github.com/the-sid-dani/samba-ai-usage-stats.git /opt/metabase/assets-repo
   ```
2. Copy the SQL directory internally:
   ```bash
   rsync -av /opt/metabase/assets-repo/sql/dashboard/ai_cost/ /tmp/metabase-assets/sql/dashboard/ai_cost/
   ```
3. Optional: remove the repo clone after copy if you don’t need it.

---
Choose the option that fits your setup. Once the SQL files are in place on the VM, continue with the runbook steps to run `create_dashboards.py`.
