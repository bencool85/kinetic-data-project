-- Canonical non-subscription (course + merch) storefront revenue by month:
-- gross before discount, discounts, revenue actually paid, AOV,
-- guest-checkout share, discount-usage share, and refund rate (both by
-- order count and by dollar amount). "Net revenue" is paid minus
-- successfully refunded amounts -- it is NOT a true gross margin figure
-- (this dataset has no COGS data; see the net-margin-proxy caveat already
-- documented on the MotherDuck Dive's CFO tab).
--
-- All money now comes from int_orders_net, so the discount and refund logic
-- lives in ONE place and this mart just adds it up by month. Two naming
-- fixes (overnight run, 2026-09-30; Ben to confirm):
--   * The old column "gross_revenue_usd" was really what customers PAID
--     (after discounts). It is now paid_revenue_usd. Its values are
--     unchanged (all 36 months identical when re-run against int_orders_net).
--   * "Gross" now means the same thing as in int_orders_net: the subtotal
--     BEFORE discounts (gross_before_discount_usd), with discount_usd next
--     to it so gross - discount = paid.
-- aov_usd is paid revenue / orders (unchanged).
--
-- Validated against the earlier version of this mart on 2026-09-30: same
-- 36 months, every metric identical; totals $194,283.64 gross - $4,874.85
-- discount = $189,408.79 paid, $182,861.97 net.
--
-- data_through is the latest order date in the data (2026-07-30); the mart
-- never runs past it and is not built from current_date.
--
-- Grain: one row per month (year_month, tested unique).

with orders as (
    select * from {{ ref('int_orders_net') }}
)

select
    date_trunc('month', order_date) as month_start,
    strftime(order_date, '%Y-%m') as year_month,
    count(*) as order_count,
    round(sum(gross_usd), 2) as gross_before_discount_usd,
    round(sum(discount_usd), 2) as discount_usd,
    round(sum(paid_usd), 2) as paid_revenue_usd,
    round(sum(paid_usd) / count(*), 2) as aov_usd,
    round(100.0 * sum(case when is_guest_order then 1 else 0 end) / count(*), 1)
        as guest_order_pct,
    round(100.0 * sum(case when discount_usd > 0 then 1 else 0 end) / count(*), 1)
        as discount_used_pct,
    round(100.0 * sum(case when refund_usd > 0 then 1 else 0 end) / count(*), 1)
        as refunded_order_pct,
    round(sum(refund_usd), 2) as refunded_amount_usd,
    round(sum(net_usd), 2) as net_revenue_usd,
    max(max(order_date)) over () as data_through
from orders
group by 1, 2
order by 1
