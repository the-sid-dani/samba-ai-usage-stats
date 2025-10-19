-- AI Cost Dashboard: Efficiency Alert Card (cache hit rate)
WITH params AS (
  SELECT
    COALESCE({{date_range.start}}, DATE '2025-10-01') AS start_date,
    COALESCE({{date_range.end}}, DATE '2025-12-31') AS end_date
)
SELECT
  ROUND(
    SAFE_DIVIDE(
      SUM(cache_read_input_tokens),
      NULLIF(SUM(uncached_input_tokens) + SUM(cache_read_input_tokens), 0)
    ) * 100,
    2
  ) AS cache_hit_rate_pct,
  SUM(cache_read_input_tokens) AS cache_read_tokens,
  SUM(uncached_input_tokens) AS uncached_input_tokens
FROM params p
JOIN `ai_usage_analytics.claude_usage_report` u
  ON u.activity_date BETWEEN p.start_date AND p.end_date;
