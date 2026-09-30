-- Rolling sends and their outcomes up to months must keep every event.
-- Returns a row for any channel where the mart total differs from the events.
with mart as (
    select channel, sum(sends) as sends, sum(opens) as opens, sum(clicks) as clicks,
           sum(bounces) as bounces, sum(unsubscribes) as unsubscribes
    from {{ ref('mart_messaging_monthly') }}
    group by 1
),
src as (
    select channel,
           sum(case when event_name = 'send' then 1 else 0 end) as sends,
           sum(case when event_name = 'open' then 1 else 0 end) as opens,
           sum(case when event_name = 'click' then 1 else 0 end) as clicks,
           sum(case when event_name = 'bounce' then 1 else 0 end) as bounces,
           sum(case when event_name = 'unsubscribe' then 1 else 0 end) as unsubscribes
    from {{ ref('int_messaging_events') }}
    group by 1
)
select m.channel, m.sends, s.sends as src_sends, m.opens, s.opens as src_opens
from mart m
join src s using (channel)
where m.sends != s.sends or m.opens != s.opens or m.clicks != s.clicks
   or m.bounces != s.bounces or m.unsubscribes != s.unsubscribes
