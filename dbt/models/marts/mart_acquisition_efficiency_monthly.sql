-- Blended customer acquisition cost (CAC) by month: all paid media spend
-- divided by first-time paying subscribers. This answers the CEO/CFO
-- stories about CAC and payback WITHOUT pretending an ad caused a specific
-- subscriber (there is no key linking an ad or campaign to a session or
-- order, so channel-level CAC would be invented). One number for the whole
-- business per month instead.
--
--   paid_spend_usd            all six platforms, from int_paid_media_daily
--   first_time_subscribers    from mart_subscriber_movement_monthly (the one
--                             definition of "started paying"); returning
--                             win-backs are excluded because ads are not
--                             what brought them back
--   blended_cac_usd           spend / first_time_subscribers; null in a month
--                             with no new subscribers (not 0, not infinity)
--   cumulative_blended_cac_usd  spend to date / subscribers to date; monthly
--                             CAC is very noisy with ~5 signups a month, so
--                             read the cumulative line for the trend
--
-- Judgment calls and caveats (must travel with the number):
--   * "Blended" = ALL paid spend over ALL new payers, including people who
--     would have found Kinetic without ads (organic, referral, email). It
--     overstates the true cost of an ad-driven subscriber and cannot rank
--     channels.
--   * No lag: spend and new payers are matched in the same calendar month,
--     although a trial takes 7 days to convert and people sign up before they
--     pay. Small counts make single months swing (about $5k to $30k today).
--   * Spend is total advertising cost only: no salaries, tools or creative.
--   * This dataset's spend is large relative to its subscriber revenue
--     (about $8.8k per subscriber overall vs about $2.1k of MRR in total), so
--     the level is a synthetic-data artifact; do not present it as a
--     benchmark. Use it for shape and method.
--
-- Hand-validated 2026-09-30 against live views: 36 months (2023-08 to
-- 2026-07); total spend $1,531,706.93 over 174 first-time subscribers =
-- $8,802.91; 2026-07 = $9,874.68 over 4; one month has no first-time
-- subscribers (CAC null).
--
-- Grain: one row per month (year_month, tested unique). Series ends at the
-- data (data_through on every row), never current_date.

with spend as (
    select
        date_trunc('month', report_date)::date as month_start,
        sum(spend_usd) as paid_spend_usd
    from {{ ref('int_paid_media_daily') }}
    group by 1
),

subs as (
    select month_start, first_time_subscribers, data_through
    from {{ ref('mart_subscriber_movement_monthly') }}
),

joined as (
    select
        spend.month_start,
        strftime(spend.month_start, '%Y-%m') as year_month,
        round(spend.paid_spend_usd, 2) as paid_spend_usd,
        coalesce(subs.first_time_subscribers, 0) as first_time_subscribers,
        spend.paid_spend_usd as raw_spend,
        (select max(data_through) from subs) as data_through
    from spend
    left join subs on spend.month_start = subs.month_start
)

select
    month_start,
    year_month,
    paid_spend_usd,
    first_time_subscribers,
    round(raw_spend / nullif(first_time_subscribers, 0), 2) as blended_cac_usd,
    round(
        sum(raw_spend) over (order by month_start)
        / nullif(sum(first_time_subscribers) over (order by month_start), 0), 2
    ) as cumulative_blended_cac_usd,
    data_through
from joined
order by month_start
