-- Rolling up to platform-day must not lose or double-count spend: the model's
-- total must equal the six source totals (Google Search = ad-group table
-- only), to the cent. Returns a row only if not.
select a.model_spend, b.source_spend
from (select sum(spend_usd) as model_spend from {{ ref('int_paid_media_daily') }}) a
cross join (
    select
        (select sum(spend_usd) from {{ ref('stg_kinetic__meta_ad_insights_daily') }})
        + (select sum(cost_usd) from {{ ref('stg_kinetic__google_search_performance_daily') }})
        + (select sum(cost_usd) from {{ ref('stg_kinetic__youtube_performance_daily') }})
        + (select sum(cost_usd) from {{ ref('stg_kinetic__dv360_performance_daily') }})
        + (select sum(spend_usd) from {{ ref('stg_kinetic__snap_stats_daily') }})
        + (select sum(spend_usd) from {{ ref('stg_kinetic__tiktok_reports_daily') }}) as source_spend
) b
where abs(a.model_spend - b.source_spend) > 0.01
