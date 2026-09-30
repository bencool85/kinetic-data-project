-- Internal logic of the funnel. Returns a row for any month that breaks it:
-- delivered = sends - bounces, and opens <= delivered, clicks <= opens,
-- unsubscribes <= delivered, every rate between 0 and 1.
select message_month_id, sends, bounces, delivered, opens, clicks, unsubscribes
from {{ ref('mart_messaging_monthly') }}
where delivered != sends - bounces
   or opens > delivered
   or clicks > opens
   or unsubscribes > delivered
   or coalesce(open_rate_fraction, 0) not between 0 and 1
   or coalesce(click_rate_fraction, 0) not between 0 and 1
   or coalesce(click_to_open_rate_fraction, 0) not between 0 and 1
   or coalesce(unsubscribe_rate_fraction, 0) not between 0 and 1
   or coalesce(bounce_rate_fraction, 0) not between 0 and 1
