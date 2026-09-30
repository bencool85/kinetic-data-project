-- Canonical MRR + active-subscriber-count definition. Annual plans are
-- normalized to their monthly-equivalent value (price / 12) so mixed
-- monthly/annual billing doesn't distort MRR.
--
-- Validated against a hand-run equivalent query directly on the live
-- kinetic database on 2026-09-28 (see CHANGELOG.md) -- e.g. 2026-07 showed
-- 90 active subscribers / ~$2,133 MRR.

-- The month series stops at the last month the data actually covers,
-- worked out from the data itself, not today's date. Decision (Ben,
-- 2026-09-29): before this fix the series ran to current_date, so months
-- after the data ended (Aug-Sep 2026) assumed nobody canceled and counted
-- still-trialing subscriptions as paying -- MRR looked like it rose to
-- $2,357.82 on no evidence. data_through is the latest subscription or
-- invoice record; it's also returned on every row so readers know how
-- current the number is.

with data_bounds as (
    select data_through from {{ ref('int_subscription_data_through') }}
),

months as (
    select unnest(generate_series(
        date '2023-01-01',
        (select date_trunc('month', data_through) from data_bounds),
        interval 1 month
    )) as month_start
),

paid_periods as (
    select * from {{ ref('int_subscription_paid_periods') }}
),

plans as (
    select * from {{ ref('stg_kinetic__subscription_plans') }}
),

active_by_month as (
    select
        m.month_start,
        p.subscription_id,
        p.plan_id,
        pl.billing_interval,
        case
            when pl.billing_interval = 'year' then pl.plan_price_usd / 12.0
            else pl.plan_price_usd
        end as monthly_equivalent_usd
    from months m
    join paid_periods p
        on p.paid_start_date is not null
        and p.paid_start_date <= m.month_start
        and (p.canceled_at is null or p.canceled_at > m.month_start)
    join plans pl on pl.plan_id = p.plan_id
)

select
    month_start,
    strftime(month_start, '%Y-%m') as year_month,
    count(distinct subscription_id) as active_subscribers,
    round(sum(monthly_equivalent_usd), 2) as mrr_usd,
    round(sum(monthly_equivalent_usd) * 12, 2) as arr_usd,
    (select data_through from data_bounds) as data_through
from active_by_month
group by 1, 2
order by 1
