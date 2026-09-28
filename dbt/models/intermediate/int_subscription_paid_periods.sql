-- Resolves when each subscription actually became a *paying* subscription,
-- not just when the Stripe-shaped object was created. This is the same
-- logic used throughout the project (originally worked out for the
-- MotherDuck Dive's CEO tab) and is defined exactly once here so every
-- downstream mart agrees with it:
--
--   * No trial at all (trial_start is null)         -> paid from start_date
--   * Canceled during the trial, before it converted -> never actually paid
--     (paid_start stays null; this subscription contributes to trial
--     funnel metrics but never to MRR/active-subscriber counts)
--   * Trial ran its course (or is still running)     -> paid from trial_end

with subscriptions as (
    select * from {{ ref('stg_kinetic__subscriptions') }}
)

select
    subscription_id,
    customer_id,
    plan_id,
    billing_interval,
    subscription_status,
    canceled_at,
    case
        when trial_start is null then start_date
        when canceled_at is not null and canceled_at <= trial_end then null
        else trial_end
    end as paid_start_date
from subscriptions
