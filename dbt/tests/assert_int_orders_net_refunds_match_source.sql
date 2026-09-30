-- Total refunds here must equal total succeeded refunds in
-- int_orders_refunded (no refund lost or double counted by the join).
-- Returns a row only if the totals differ.
select a.total_here, b.total_source
from (select round(sum(refund_usd), 2) as total_here from {{ ref('int_orders_net') }}) a
cross join (select round(sum(refunded_amount_usd), 2) as total_source from {{ ref('int_orders_refunded') }}) b
where abs(a.total_here - b.total_source) > 0.005
