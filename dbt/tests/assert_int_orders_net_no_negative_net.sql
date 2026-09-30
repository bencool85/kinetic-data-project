-- net_usd is deliberately not floored at zero; a refund above the amount
-- paid means bad data, so fail loudly. Returns offending orders.
select order_id, paid_usd, refund_usd, net_usd
from {{ ref('int_orders_net') }}
where net_usd < 0
