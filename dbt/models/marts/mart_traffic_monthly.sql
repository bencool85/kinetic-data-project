-- Web and app traffic by where the visit came from and where it landed, by month.
-- Answers the CMO questions "how much traffic do we get, from which source, and
-- where does it land?" for the owned web site and app, which the paid-media marts
-- cannot (they stop at the ad click).
--
-- Built on int_sessions_unified (web analytics + app analytics, one row per session,
-- 49,895 sessions). traffic_source is worked out as:
--   app                 every app-analytics session (ios, android, in-app web).
--                       App sessions carry no UTM tags, landing page or referrer.
--   meta, google_search, tiktok, youtube, dv360, snap
--                       web sessions whose utm_source names that ad platform
--                       (utm_medium 'paid'; the referrer domain agrees 1:1)
--   email               web sessions tagged utm_source = email (13 in total)
--   untagged_web        web sessions with no UTM tag (direct, organic or untracked:
--                       the data cannot tell them apart)
-- landing_page is the first page of a web session ('not_applicable' for app).
--
-- Measures are additive counts and sums; ratios are computed from the monthly SUMS:
--   known_share_fraction     known_sessions / sessions (0.53 = 53%)
--   avg_session_seconds      total_duration_seconds / sessions
-- known_sessions are sessions tied to a customer account, either at the time or
-- back-filled after the visitor signed up or logged in (340 sessions); anonymous
-- web visitors are most of web traffic, so never read this as a count of people.
--
-- Hand-checked 2026-09-30 against the live intermediate model: 49,895 sessions
-- (web 30,285 = mobile 16,510 + desktop 12,115 + tablet 1,660; app 19,610),
-- 26,426 known + 23,469 anonymous, total duration 46,049,491 seconds, no null or
-- zero durations, first session 2023-08-03, last 2026-07-30, nothing after.
-- Paid sources: meta 5,851, google_search 4,823, tiktok 4,513, youtube 2,260,
-- dv360 1,957, snap 1,547 (20,951); email 13; untagged web 9,321.
--
-- Caveat that must travel with these numbers: utm_source and utm_campaign are URL
-- tags, not ad-platform campaign IDs. A session tagged meta is a visit that arrived
-- through a Meta-tagged link; it is NOT a sale or a subscriber, and no key links
-- a session to an ad, order or subscriber here. Do not attribute revenue to these
-- sources. Time series ends at the data (data_through on every row).
-- Grain: one row per month x traffic_source x landing_page (traffic_month_id, unique).

with sessions as (
    select * from {{ ref('int_sessions_unified') }}
),

classified as (
    select
        date_trunc('month', started_at)::date as month_start,
        case
            when source_system = 'app' then 'app'
            when utm_source is not null then utm_source
            else 'untagged_web'
        end as traffic_source,
        coalesce(landing_page, 'not_applicable') as landing_page,
        customer_resolution,
        duration_seconds,
        started_at::date as session_date
    from sessions
)

select
    strftime(month_start, '%Y-%m') || '|' || traffic_source || '|' || landing_page as traffic_month_id,
    month_start,
    strftime(month_start, '%Y-%m') as year_month,
    traffic_source,
    landing_page,
    count(*) as sessions,
    sum(case when customer_resolution in ('known_at_time', 'backfilled') then 1 else 0 end) as known_sessions,
    sum(case when customer_resolution = 'anonymous' then 1 else 0 end) as anonymous_sessions,
    sum(duration_seconds) as total_duration_seconds,
    round(sum(case when customer_resolution in ('known_at_time', 'backfilled') then 1 else 0 end) * 1.0
          / nullif(count(*), 0), 4) as known_share_fraction,
    round(sum(duration_seconds) * 1.0 / nullif(count(*), 0), 1) as avg_session_seconds,
    max(max(session_date)) over () as data_through
from classified
group by 1, 2, 3, 4, 5
order by month_start, traffic_source, landing_page
