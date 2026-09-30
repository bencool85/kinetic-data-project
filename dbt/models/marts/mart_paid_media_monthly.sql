-- Paid media performance by platform by month: spend, reach, clicks, and
-- the platforms' own conversions, with the usual efficiency ratios. This
-- answers the Performance Marketing story "which platform is efficient, and
-- is it getting better or worse?" and gives the CMO one spend number per
-- platform per month.
--
-- Built on int_paid_media_daily, so units are already dollars and each
-- platform's conversion is already the single agreed purchase-type action.
-- Ratios are computed from the monthly SUMS (total spend / total clicks),
-- not by averaging daily ratios, so a big day counts for more than a tiny one.
--   ctr_fraction           clicks / impressions (0.045 = 4.5%, a fraction)
--   cpc_usd                spend / clicks
--   cost_per_conversion_usd spend / platform-reported conversions
--   reported_roas          platform-reported conversion value / spend
--                          (null for Meta: it reports no conversion value)
-- Every ratio is null (not 0) when its denominator is 0.
--
-- Caveat that must travel with every number: conversions and their value are
-- what each PLATFORM claims. There is no key linking an ad to a Kinetic order,
-- platforms overlap (one buyer can be claimed by several), and Meta's is a
-- different action definition from the others. Never add conversions across
-- platforms as if they were sales, and never call reported_roas "true ROAS".
-- Fractional conversions are normal (credit is split).
--
-- Hand-validated 2026-09-30 by inlining int_paid_media_daily against the
-- live staging views: 216 rows = 6 platforms x 36 months (2023-08 to
-- 2026-07), total spend $1,531,706.95, no month with zero spend; Google
-- Search 2026-07 = $8,224.52 spend, 2.35 reported ROAS (also matches a
-- direct query of its source table).
--
-- Time series ends at the data (2026-07-30, on every row as data_through).
-- Grain: one row per platform per month (platform_month_id, tested unique).

with daily as (
    select * from {{ ref('int_paid_media_daily') }}
)

select
    platform || '|' || strftime(date_trunc('month', report_date), '%Y-%m') as platform_month_id,
    platform,
    date_trunc('month', report_date)::date as month_start,
    strftime(report_date, '%Y-%m') as year_month,
    round(sum(spend_usd), 2) as spend_usd,
    sum(impressions) as impressions,
    sum(clicks) as clicks,
    round(sum(conversions), 2) as conversions,
    round(sum(conversions_value_usd), 2) as conversions_value_usd,
    round(sum(clicks) * 1.0 / nullif(sum(impressions), 0), 4) as ctr_fraction,
    round(sum(spend_usd) / nullif(sum(clicks), 0), 2) as cpc_usd,
    round(sum(spend_usd) / nullif(sum(conversions), 0), 2) as cost_per_conversion_usd,
    round(sum(conversions_value_usd) / nullif(sum(spend_usd), 0), 2) as reported_roas,
    max(max(report_date)) over () as data_through
from daily
group by 1, 2, 3, 4
order by month_start, platform
