-- One row per order, with the money broken out once so every mart reads
-- the same numbers:
--   gross_usd    order subtotal BEFORE any discount
--   discount_usd subscriber discount + discount code (28 orders use both)
--   paid_usd     what the customer was charged (= raw total_amount;
--                a test checks gross - discount = paid on every order)
--   refund_usd   succeeded refunds only (from int_orders_refunded), 0 if none
--   net_usd      paid - refund
--
-- Judgment calls (Ben, 2026-09-30):
--   * "Gross" means the pre-discount subtotal. 
--     mart_storefront_revenue_monthly now reads this model and calls the
--     paid amount paid_revenue_usd, so "gross" has one meaning.
--   * net_usd is NOT floored at zero. A refund larger than the amount paid
--     is a data problem, and a test fails loudly if it ever happens (none
--     today: 116 orders are fully refunded, none over-refunded).
--   * Refunds come out of the discounted price, so a discount is never
--     refunded separately.
--
-- Customer: is_guest_order stays true for anyone who checked out as a
-- guest (raw customer_id is null), even if we later resolve them.
-- customer_id is the order's own account, or for guests the account whose
-- email matches the guest email (via int_customer_identity; 28 of 1,257
-- guest orders match today). customer_resolution says which it was.
-- Guest orders with no matching account keep a null customer_id.
--
-- Grain: one row per order_id. int_customer_identity has one row per
-- identifier_key, so the email join cannot fan out; order_id is tested unique.

with orders as (
    select * from {{ ref('stg_kinetic__orders') }}
),

refunded as (
    select * from {{ ref('int_orders_refunded') }}
),

guest_identity as (
    select
        identifier_value as email,
        customer_id
    from {{ ref('int_customer_identity') }}
    where identifier_type = 'email'
)

select
    o.order_id,
    o.order_date,
    o.order_type,
    round(o.subtotal_usd, 2) as gross_usd,
    round(
        coalesce(o.subscriber_discount_usd, 0) + coalesce(o.discount_code_usd, 0), 2
    ) as discount_usd,
    round(o.total_amount_usd, 2) as paid_usd,
    round(coalesce(r.refunded_amount_usd, 0), 2) as refund_usd,
    round(o.total_amount_usd - coalesce(r.refunded_amount_usd, 0), 2) as net_usd,
    o.is_guest_order,
    coalesce(o.customer_id, gi.customer_id) as customer_id,
    case
        when o.customer_id is not null then 'account'
        when gi.customer_id is not null then 'guest_email_match'
        else 'unresolved'
    end as customer_resolution
from orders o
left join refunded r
    on o.order_id = r.order_id
left join guest_identity gi
    on o.customer_id is null
    and gi.email = lower(trim(o.guest_email))
