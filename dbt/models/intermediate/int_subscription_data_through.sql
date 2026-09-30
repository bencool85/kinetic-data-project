-- One row, one date: the last day the subscription/invoice data covers.
-- Every subscription-based time series (MRR, subscriber movement, ...)
-- stops at this date instead of running on to today, because months after
-- the data ends would be invented (nobody is recorded as canceling, trials
-- look like paying subscribers). It used to be written out inside
-- mart_mrr_monthly; it lives here so two marts cannot drift apart.
-- Decision (Ben, 2026-09-29): series end where the data ends.

select
    greatest(
        (select max(subscription_created_at) from {{ ref('stg_kinetic__subscriptions') }}),
        (select max(canceled_at) from {{ ref('stg_kinetic__subscriptions') }}),
        (select max(invoice_created_at) from {{ ref('stg_kinetic__invoices') }}),
        (select max(paid_at) from {{ ref('stg_kinetic__invoices') }})
    )::date as data_through
