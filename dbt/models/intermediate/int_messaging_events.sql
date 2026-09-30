-- Every Braze email and push event in ONE shape, so an engagement mart can
-- count "opens" or "clicks" across channels without two separate queries.
--
-- Two sources, one shape (channel column tells them apart):
--   * braze_email_events (channel = 'email') -- carries email_address;
--     device_id / platform are null.
--   * braze_push_events (channel = 'push') -- carries device_id / platform;
--     email_address is null.
-- Event IDs never collide across the two (checked: 0 overlap).
--
-- Customer resolution (same idea as int_orders_net / int_sessions_unified):
--   * Braze's own customer_id is kept when present (customer_resolution =
--     'braze_customer_id').
--   * Email events with no customer_id (2,187 today, all from guest
--     checkouts such as Order Confirmation emails) are matched by email
--     address through int_customer_identity (44 events today resolve to an
--     account; 'email_match'). The rest stay null ('unresolved').
--   * Braze's id always wins if the two ever disagree (0 conflicts today).
--   * Push events always carry a customer_id, so they are always
--     'braze_customer_id'.
-- Deleted accounts: int_customer_identity leaves them out, so nothing is
-- newly attached to them (no Braze event points at one today).
--
-- Judgment calls:
--   * Nothing is dropped or de-duplicated: a "send" is one row and so is
--     each open/click. Counting unique opens/clicks (per send_id) is the
--     mart's job, because "open rate" has to say which definition it uses.
--   * Opens are not reliable engagement (mail-client pre-fetching inflates
--     them in real life); this synthetic data has no such flag, so we only
--     record what Braze recorded.
--   * event_name is the short lowercase name from staging
--     (send/open/click/bounce/unsubscribe).
--   * Time series note: the source data ends 2026-07-30 but 7 email events
--     (replies to late sends) are stamped up to 2026-08-01. They are kept as
--     recorded; marts that group by month should end at the data's own last
--     date, never current_date.
--
-- Grain: one row per event_id (tested unique).

with email_events as (
    select * from {{ ref('stg_kinetic__braze_email_events') }}
),

push_events as (
    select * from {{ ref('stg_kinetic__braze_push_events') }}
),

email_campaigns as (
    select * from {{ ref('stg_kinetic__braze_email_campaigns') }}
),

push_campaigns as (
    select * from {{ ref('stg_kinetic__braze_push_campaigns') }}
),

email_identity as (
    select identifier_value as email_address, customer_id
    from {{ ref('int_customer_identity') }}
    where identifier_type = 'email'
),

email_shaped as (
    select
        email_events.event_id,
        'email' as channel,
        email_events.send_id,
        email_events.campaign_id,
        email_campaigns.campaign_name,
        email_campaigns.campaign_type,
        email_events.event_name,
        email_events.occurred_at,
        coalesce(email_events.customer_id, email_identity.customer_id) as customer_id,
        case
            when email_events.customer_id is not null then 'braze_customer_id'
            when email_identity.customer_id is not null then 'email_match'
            else 'unresolved'
        end as customer_resolution,
        lower(trim(email_events.email_address)) as email_address,
        cast(null as varchar) as device_id,
        cast(null as varchar) as platform
    from email_events
    left join email_campaigns
        on email_events.campaign_id = email_campaigns.campaign_id
    left join email_identity
        on lower(trim(email_events.email_address)) = email_identity.email_address
),

push_shaped as (
    select
        push_events.event_id,
        'push' as channel,
        push_events.send_id,
        push_events.campaign_id,
        push_campaigns.campaign_name,
        push_campaigns.campaign_type,
        push_events.event_name,
        push_events.occurred_at,
        push_events.customer_id,
        'braze_customer_id' as customer_resolution,
        cast(null as varchar) as email_address,
        push_events.device_id,
        push_events.platform
    from push_events
    left join push_campaigns
        on push_events.campaign_id = push_campaigns.campaign_id
)

select * from email_shaped
union all
select * from push_shaped
