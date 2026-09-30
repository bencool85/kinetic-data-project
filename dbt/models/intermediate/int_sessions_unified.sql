-- One row per session, web and app together, with the customer resolved
-- once so every engagement mart counts "sessions per customer" the same way.
--
-- Two sources, one shape:
--   * web_sessions (source_system = 'web') -- anonymous until the visitor
--     signs up or logs in. Carries UTM/landing-page columns.
--   * app_sessions (source_system = 'app') -- always tied to a customer.
--     Carries device_id; the UTM/landing-page columns are null.
-- Session IDs are prefixed web_sess_ / app_sess_, so they never collide.
--
-- Judgment calls (Ben, 2026-09-30):
--   * BACK-FILL with no time limit (earlier decision, confirmed): a web
--     session with no customer takes the customer its anonymous_id later
--     turned out to be, via int_customer_identity. Today that is 340
--     sessions from 263 visitors, all 0-14 days before signup/login. No
--     window is applied; revisit if real data ever shows shared devices.
--   * customer_resolution keeps the "was anonymous at the time" fact:
--     known_at_time / backfilled / anonymous.
--   * App sessions with platform = 'web' (4,994, logged-in web devices) are
--     KEPT as their own sessions. Only 28 overlap in time with a web
--     session, so they look like different sessions, not duplicates.
--     source_system + platform tell them apart from web-analytics sessions.
--   * A customer_id recorded on the session itself is kept as recorded. The
--     "exclude deleted accounts" rule lives in int_customer_identity, so it
--     only affects back-filled sessions (no session points at a deleted
--     account today).
--
-- Grain: one row per session_id (tested unique).

with web as (
    select * from {{ ref('stg_kinetic__web_sessions') }}
),

app as (
    select * from {{ ref('stg_kinetic__app_sessions') }}
),

anonymous_identity as (
    select
        identifier_value as anonymous_id,
        customer_id
    from {{ ref('int_customer_identity') }}
    where identifier_type = 'anonymous_id'
),

web_unified as (
    select
        w.session_id,
        'web' as source_system,
        'web' as platform,
        w.started_at,
        w.ended_at,
        coalesce(w.customer_id, ai.customer_id) as customer_id,
        case
            when w.customer_id is not null then 'known_at_time'
            when ai.customer_id is not null then 'backfilled'
            else 'anonymous'
        end as customer_resolution,
        w.anonymous_id,
        cast(null as varchar) as device_id,
        w.utm_source,
        w.utm_medium,
        w.utm_campaign,
        w.landing_page,
        w.referrer_domain,
        w.device_category
    from web w
    left join anonymous_identity ai
        on w.customer_id is null
        and ai.anonymous_id = w.anonymous_id
),

app_unified as (
    select
        a.session_id,
        'app' as source_system,
        a.platform,
        a.started_at,
        a.ended_at,
        a.customer_id,
        'known_at_time' as customer_resolution,
        cast(null as varchar) as anonymous_id,
        a.device_id,
        cast(null as varchar) as utm_source,
        cast(null as varchar) as utm_medium,
        cast(null as varchar) as utm_campaign,
        cast(null as varchar) as landing_page,
        cast(null as varchar) as referrer_domain,
        cast(null as varchar) as device_category
    from app a
),

unioned as (
    select * from web_unified
    union all
    select * from app_unified
)

select
    session_id,
    source_system,
    platform,
    started_at,
    ended_at,
    date_diff('second', started_at, ended_at) as duration_seconds,
    customer_id,
    customer_resolution,
    anonymous_id,
    device_id,
    utm_source,
    utm_medium,
    utm_campaign,
    landing_page,
    referrer_domain,
    device_category
from unioned
