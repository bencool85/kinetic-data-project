-- The CAC mart's spend must equal all paid media spend (every dollar, every
-- platform). Returns a row if not.
select a.mart_spend, b.daily_spend
from (select sum(paid_spend_usd) as mart_spend from {{ ref('mart_acquisition_efficiency_monthly') }}) a
cross join (select sum(spend_usd) as daily_spend from {{ ref('int_paid_media_daily') }}) b
where abs(a.mart_spend - b.daily_spend) > 1.0
