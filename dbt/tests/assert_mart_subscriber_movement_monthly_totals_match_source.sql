-- Nothing lost or invented: over all months, new subscribers must equal the
-- paid subscriptions that started on or before the data end, and churned
-- must equal the paid subscriptions that were canceled. Returns a row if not.
with paid as (
    select * from {{ ref('int_subscription_paid_periods') }}
    where paid_start_date is not null
),
bounds as (
    select data_through from {{ ref('int_subscription_data_through') }}
),
mart as (
    select
        sum(new_paying_subscribers) as new_n,
        sum(churned_subscribers) as churn_n
    from {{ ref('mart_subscriber_movement_monthly') }}
),
src as (
    select
        count(*) filter (where paid_start_date <= (select data_through from bounds)) as new_n,
        count(*) filter (where canceled_at is not null) as churn_n
    from paid
)
select mart.new_n, src.new_n as src_new_n, mart.churn_n, src.churn_n as src_churn_n
from mart cross join src
where mart.new_n <> src.new_n or mart.churn_n <> src.churn_n
