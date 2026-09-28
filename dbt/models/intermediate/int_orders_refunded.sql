-- One row per order that has at least one *succeeded* refund, with the
-- total refunded amount and refund count. Only successful refunds count --
-- a refund that was requested but failed/pending shouldn't reduce reported
-- revenue. Left-joined against this everywhere else, so an order with no
-- refund simply doesn't appear here rather than showing a zero row.

with refunds as (
    select * from {{ ref('stg_kinetic__refunds') }}
    where refund_status = 'succeeded'
)

select
    order_id,
    sum(amount_usd) as refunded_amount_usd,
    count(*) as refund_count
from refunds
group by 1
