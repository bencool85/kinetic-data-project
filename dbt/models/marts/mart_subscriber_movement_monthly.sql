-- Subscriber movement by month: how many people started paying, how many
-- stopped, and how many are paying at month end. This answers the CEO story
-- "are we adding more paying subscribers than we lose?" (net-new vs churned).
--
-- Definitions (all reuse int_subscription_paid_periods, so "started paying"
-- means the same thing as in mart_mrr_monthly):
--   new_paying_subscribers  subscriptions whose paid start date falls in the
--                           month. A trial that is canceled before it
--                           converts never paid, so it is not counted.
--   first_time / returning  split of the above: returning = the customer had
--                           an earlier paying subscription (a win-back, 25 in
--                           total today), first_time = their first ever.
--   churned_subscribers     paying subscriptions canceled in the month.
--   net_new_subscribers     new - churned.
--   active_subscribers_end  paying and not canceled on the last day of the
--                           month.
-- The identity  end = previous end + new - churned  holds exactly and is
-- tested. Small judgment call: mart_mrr_monthly counts subscribers on the
-- 1st of each month, so its number can differ from the previous month's
-- end-of-month count only when someone starts or cancels on the 1st itself
-- (8 of 35 months today; all explained by such 1st-of-month events).
--
-- Series: starts at the first month with a paying subscriber and stops at
-- the month of int_subscription_data_through (2026-07-30 today), never
-- current_date. 3 subscriptions whose trial ends in August 2026 are beyond
-- the data and are not counted anywhere. data_through is on every row.
--
-- Not included: plan mix and revenue impact (see mart_mrr_monthly); upgrades
-- and downgrades are not movements here.
--
-- Hand-validated 2026-09-30 against live data: 174 first-time + 25 returning
-- = 199 new, 101 churned, 98 active at 2026-07-31 (= 98 paid subscriptions
-- never canceled; matches the Phase 0 analysis of 98 active subscribers).
--
-- Grain: one row per month (year_month, tested unique).

with data_bounds as (
    select data_through from {{ ref('int_subscription_data_through') }}
),

paid as (
    select
        *,
        row_number() over (partition by customer_id order by paid_start_date) as paid_sequence
    from {{ ref('int_subscription_paid_periods') }}
    where paid_start_date is not null
),

months as (
    select unnest(generate_series(
        (select date_trunc('month', min(paid_start_date)) from paid),
        (select date_trunc('month', data_through) from data_bounds),
        interval 1 month
    ))::date as month_start
),

bounds as (
    select
        month_start,
        (month_start + interval 1 month - interval 1 day)::date as month_end
    from months
)

select
    b.month_start,
    strftime(b.month_start, '%Y-%m') as year_month,
    count(*) filter (
        where p.paid_start_date between b.month_start and b.month_end
    ) as new_paying_subscribers,
    count(*) filter (
        where p.paid_start_date between b.month_start and b.month_end
        and p.paid_sequence = 1
    ) as first_time_subscribers,
    count(*) filter (
        where p.paid_start_date between b.month_start and b.month_end
        and p.paid_sequence > 1
    ) as returning_subscribers,
    count(*) filter (
        where p.canceled_at between b.month_start and b.month_end
    ) as churned_subscribers,
    count(*) filter (
        where p.paid_start_date between b.month_start and b.month_end
    ) - count(*) filter (
        where p.canceled_at between b.month_start and b.month_end
    ) as net_new_subscribers,
    count(*) filter (
        where p.paid_start_date <= b.month_end
        and (p.canceled_at is null or p.canceled_at > b.month_end)
    ) as active_subscribers_end,
    (select data_through from data_bounds) as data_through
from bounds b
cross join paid p
group by 1, 2
order by 1
