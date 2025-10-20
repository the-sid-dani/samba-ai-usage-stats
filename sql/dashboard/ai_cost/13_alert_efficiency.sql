-- AI Cost Dashboard: Efficiency Alert Card (cache hit rate)
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
FROM `ai_usage_analytics.claude_usage_report`
WHERE activity_date >= CAST({{start_date}} AS DATE)
  AND activity_date <= CAST({{end_date}} AS DATE);
