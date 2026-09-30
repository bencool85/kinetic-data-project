-- One row per ad platform per day, with spend, impressions, clicks and
-- conversions all in the same units, so a mart can compare or add up
-- platforms without knowing each platform's quirks.
--
-- Each platform reports at a different level (Meta/Snap/TikTok per ad,
-- Google/YouTube per ad group, DV360 per line item per exchange per
-- environment). Here everything is summed up to platform + day.
--
-- Units: staging already turned micros into dollars (_usd columns). Meta's
-- spend arrives as plain dollars in the raw table (verified: raw sum =
-- staged sum), so no conversion is applied. Do not re-divide anything here.
--
-- Judgment calls:
--   * "Conversion" = ONE standard purchase-type outcome per platform:
--       - meta: the 'purchase' action_type only (Meta reports several
--         actions per ad per day: link_click, add_to_cart, initiate_checkout,
--         video_view ... adding them would count one shopper many times).
--         Days with no purchase rows count as 0 conversions.
--       - google_search, youtube, dv360, snap, tiktok: these tables have a
--         single `conversions` column (the platform's own primary
--         conversion, fractional because credit is split) -- used as is.
--     All of these are the platform's OWN attributed counts, not
--     site-verified orders: summing them across platforms will overcount
--     (the same buyer can be claimed by several platforms), and they must
--     never be compared one-to-one with Kinetic orders.
--   * clicks: Snap's "swipes" are used as its clicks (its equivalent).
--   * conversions_value_usd: the platforms' own reported value. Meta's
--     table has no value column, so it is null for Meta (null, not 0, so a
--     ROAS built on it cannot silently look like zero return).
--   * Google Search: only the ad-group table is used. It is the keyword
--     table rolled up (verified: same total spend); adding both would
--     double-count spend.
--   * Days where a platform has no row are NOT filled with zeros: today all
--     six platforms have every day from 2023-08-01 to 2026-07-30 (1,095
--     each), and a test guards it stays that way.
--   * Time series ends where the data ends (2026-07-30); nothing runs to
--     today's date.
--
-- Grain: one row per platform_day_id (platform | date), tested unique.

with meta_insights as (
    select
        report_date,
        sum(spend_usd) as spend_usd,
        sum(impressions) as impressions,
        sum(clicks) as clicks
    from {{ ref('stg_kinetic__meta_ad_insights_daily') }}
    group by report_date
),

meta_purchases as (
    select
        report_date,
        sum(action_count) as conversions
    from {{ ref('stg_kinetic__meta_ad_actions_daily') }}
    where action_type = 'purchase'
    group by report_date
),

meta as (
    select
        'meta' as platform,
        meta_insights.report_date,
        meta_insights.spend_usd,
        meta_insights.impressions,
        meta_insights.clicks,
        cast(coalesce(meta_purchases.conversions, 0) as double) as conversions,
        cast(null as double) as conversions_value_usd
    from meta_insights
    left join meta_purchases
        on meta_insights.report_date = meta_purchases.report_date
),

google_search as (
    select
        'google_search' as platform,
        report_date,
        sum(cost_usd) as spend_usd,
        sum(impressions) as impressions,
        sum(clicks) as clicks,
        sum(conversions) as conversions,
        sum(conversions_value_usd) as conversions_value_usd
    from {{ ref('stg_kinetic__google_search_performance_daily') }}
    group by report_date
),

youtube as (
    select
        'youtube' as platform,
        report_date,
        sum(cost_usd) as spend_usd,
        sum(impressions) as impressions,
        sum(clicks) as clicks,
        sum(conversions) as conversions,
        sum(conversions_value_usd) as conversions_value_usd
    from {{ ref('stg_kinetic__youtube_performance_daily') }}
    group by report_date
),

dv360 as (
    select
        'dv360' as platform,
        report_date,
        sum(cost_usd) as spend_usd,
        sum(impressions) as impressions,
        sum(clicks) as clicks,
        sum(conversions) as conversions,
        sum(conversions_value_usd) as conversions_value_usd
    from {{ ref('stg_kinetic__dv360_performance_daily') }}
    group by report_date
),

snap as (
    select
        'snap' as platform,
        report_date,
        sum(spend_usd) as spend_usd,
        sum(impressions) as impressions,
        sum(swipes) as clicks,
        sum(conversions) as conversions,
        sum(conversions_value_usd) as conversions_value_usd
    from {{ ref('stg_kinetic__snap_stats_daily') }}
    group by report_date
),

tiktok as (
    select
        'tiktok' as platform,
        report_date,
        sum(spend_usd) as spend_usd,
        sum(impressions) as impressions,
        sum(clicks) as clicks,
        sum(conversions) as conversions,
        sum(conversions_value_usd) as conversions_value_usd
    from {{ ref('stg_kinetic__tiktok_reports_daily') }}
    group by report_date
),

unioned as (
    select * from meta
    union all select * from google_search
    union all select * from youtube
    union all select * from dv360
    union all select * from snap
    union all select * from tiktok
)

select
    platform || '|' || strftime(report_date, '%Y-%m-%d') as platform_day_id,
    platform,
    report_date,
    spend_usd,
    impressions,
    clicks,
    conversions,
    conversions_value_usd
from unioned
