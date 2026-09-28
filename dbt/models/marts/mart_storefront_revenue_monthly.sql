-- Canonical non-subscription (course + merch) storefront revenue by month:
-- gross revenue, AOV, guest-checkout share, discount-usage share, and
-- refund rate (both by order count and by dollar amount). "Net revenue"
-- is gross minus successfully refunded amounts -- it is NOT a true gross
-- margin figure (this dataset has no COGS data; see the net-margin-proxy
-- caveat already documented on the MotherDuck Dive's CFO tab).
--
-- Validated against a hand-run equivalent query directly on the live
-- kinetic database on 2026-09-28 (see CHANGELOG.md) -- e.g. 2026-07 showed
-- 246 orders, $13,843.71 gross revenue, $56.28 AOV, 13.0% guest orders,
-- 19.5% with a discount applied, 4.5% of orders refunded.

with orders as (
    select * from {{ ref('stg_kinetic__orders') }}
),

refunded as (
    select * from {{ ref('int_orders_refunded') }}
)

select
    date_trunc('month', o.order_date) as month_start,
    strftime(o.order_date, '%Y-%m') as year_month,
    count(*) as order_count,
    round(sum(o.total_amount_usd), 2) as gross_revenue_usd,
    round(sum(o.total_amount_usd) / count(*), 2) as aov_usd,
    round(100.0 * sum(case when o.is_guest_order then 1 else 0 end) / count(*), 1)
        as guest_order_pct,
    round(100.0 * sum(case when o.has_discount then 1 else 0 end) / count(*), 1)
        as discount_used_pct,
    round(100.0 * count(r.order_id) / count(*), 1) as refunded_order_pct,
    round(coalesce(sum(r.refunded_amount_usd), 0), 2) as refunded_amount_usd,
    round(sum(o.total_amount_usd) - coalesce(sum(r.refunded_amount_usd), 0), 2)
        as net_revenue_usd
from orders o
left join refunded r on r.order_id = o.order_id
group by 1, 2
order by 1
