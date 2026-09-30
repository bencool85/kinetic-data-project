-- gross - discount must equal paid on every order, and net must equal
-- paid - refund. Returns orders that don't reconcile (to the cent).
select order_id, gross_usd, discount_usd, paid_usd, refund_usd, net_usd
from {{ ref('int_orders_net') }}
where abs(gross_usd - discount_usd - paid_usd) > 0.005
   or abs(paid_usd - refund_usd - net_usd) > 0.005
