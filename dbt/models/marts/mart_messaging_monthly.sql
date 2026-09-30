-- Owned-channel messaging (Braze email and push) by channel, campaign type and
-- month: how many messages went out, how many reached a device or inbox, and
-- what people did with them. Answers the CMO question "how are our owned
-- channels performing?" that the paid-media marts cannot.
--
-- Built on int_messaging_events (one row per send, open, click, bounce or
-- unsubscribe). Each message is followed from its send to whatever happened
-- to it, so a month means "messages SENT in that month and what became of
-- them", not "events that happened in that month". Opens and clicks arrive
-- within 2 days of the send, so they land in (or just after) the send month.
--
-- Definitions (Ben's call; assumed 2026-09-30, needs his OK):
--   delivered                  sends - bounces (there is no delivered event)
--   bounce_rate_fraction       bounces / sends
--   open_rate_fraction         opens / delivered
--   click_rate_fraction        clicks / delivered
--   click_to_open_rate_fraction clicks / opens
--   unsubscribe_rate_fraction  unsubscribes / delivered
-- Ratios are computed from the monthly SUMS and are null (not 0) when the
-- denominator is 0. Fractions: 0.35 means 35%.
--
-- Facts hand-checked 2026-09-30 against the live intermediate model: every
-- event has a send; a send has at most one open, click, bounce or
-- unsubscribe; nothing is opened on a bounced send; every click follows an
-- open; everything happens within 2 days of the send. Email 18,187 sends /
-- 6,328 opens / 1,341 clicks / 357 bounces / 122 unsubscribes; push 7,851 /
-- 1,590 / 220 / 205 / 31 (26,038 sends in total).
--
-- Caveats that must travel with these numbers: an "open" is a tracked
-- event (email opens are inflated by privacy features in real life, and this
-- dataset defines its own), so compare channels and months, not to outside
-- benchmarks. The unit is messages, not people. Seven opens are stamped 31 Jul
-- to 1 Aug 2026 (after the data's last date) on sends from 29-30 Jul; they are
-- counted in July because they belong to July sends, and no August row exists.
-- The latest month is cut off at the data's end, so its counts are smaller.
-- Time series ends at the data (data_through on every row).
-- Grain: one row per channel x campaign_type x month (message_month_id, unique).

with events as (
    select * from {{ ref('int_messaging_events') }}
),

sends as (
    select
        send_id,
        channel,
        campaign_type,
        date_trunc('month', occurred_at)::date as month_start,
        occurred_at::date as sent_date
    from events
    where event_name = 'send'
),

outcomes as (
    select
        send_id,
        max(case when event_name = 'open' then 1 else 0 end) as opened,
        max(case when event_name = 'click' then 1 else 0 end) as clicked,
        max(case when event_name = 'bounce' then 1 else 0 end) as bounced,
        max(case when event_name = 'unsubscribe' then 1 else 0 end) as unsubscribed
    from events
    where event_name in ('open', 'click', 'bounce', 'unsubscribe')
    group by 1
),

per_send as (
    select
        s.*,
        coalesce(o.opened, 0) as opened,
        coalesce(o.clicked, 0) as clicked,
        coalesce(o.bounced, 0) as bounced,
        coalesce(o.unsubscribed, 0) as unsubscribed
    from sends s
    left join outcomes o using (send_id)
)

select
    channel || '|' || campaign_type || '|' || strftime(month_start, '%Y-%m') as message_month_id,
    channel,
    campaign_type,
    month_start,
    strftime(month_start, '%Y-%m') as year_month,
    count(*) as sends,
    sum(bounced) as bounces,
    count(*) - sum(bounced) as delivered,
    sum(opened) as opens,
    sum(clicked) as clicks,
    sum(unsubscribed) as unsubscribes,
    round(sum(bounced) * 1.0 / nullif(count(*), 0), 4) as bounce_rate_fraction,
    round(sum(opened) * 1.0 / nullif(count(*) - sum(bounced), 0), 4) as open_rate_fraction,
    round(sum(clicked) * 1.0 / nullif(count(*) - sum(bounced), 0), 4) as click_rate_fraction,
    round(sum(clicked) * 1.0 / nullif(sum(opened), 0), 4) as click_to_open_rate_fraction,
    round(sum(unsubscribed) * 1.0 / nullif(count(*) - sum(bounced), 0), 4) as unsubscribe_rate_fraction,
    max(max(sent_date)) over () as data_through
from per_send
group by 1, 2, 3, 4, 5
order by month_start, channel, campaign_type
