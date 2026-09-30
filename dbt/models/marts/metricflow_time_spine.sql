-- One row per calendar day: the "time spine" MetricFlow (the semantic layer
-- engine) requires. It is a plain calendar, no business data. MetricFlow
-- joins to it when a metric needs every date present (cumulative metrics,
-- period offsets, filling empty months).
--
-- Like every series in this project it stops at the last day the data
-- covers (data_through, worked out from the data), never today's date.
-- It starts 2023-01-01, the same start mart_mrr_monthly uses.

select
    unnest(generate_series(
        date '2023-01-01',
        (select data_through from {{ ref('int_subscription_data_through') }}),
        interval 1 day
    ))::date as date_day
