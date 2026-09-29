-- One lookup table that answers "which customer is this?" for every
-- identifier we can trace back to a customer account. Downstream models join
-- to it instead of each inventing their own matching rules.
--
-- Two kinds of identifier:
--   * anonymous_id -- the web visitor ID. identity_map records the moment an
--     anonymous visitor signed up or logged in, so we know who they were.
--     Decision (Ben, 2026-09-29): BACK-FILL. A visitor's earlier anonymous
--     sessions count as that customer's too (340 web sessions today), so the
--     path to signup is visible. Sessions keep their own "was anonymous at
--     the time" flag; this table only says who it turned out to be.
--   * email -- the address on a customer account (lowercased, trimmed).
--     Decision (Ben, 2026-09-29): MATCH ON EMAIL. A guest checkout or a
--     Braze guest email that uses an account's address belongs to that
--     customer, whether the guest order came before signup (10 today) or
--     after (18 today). match_method says how each link was made.
--
-- Deleted accounts (is_deleted, 11 today) are left out entirely: we don't
-- attach new activity to someone who asked to be removed. No current
-- identity_map rows or guest emails point at a deleted account, so this
-- changes nothing today; it's a guard for the future.
--
-- Grain: one row per identifier (identifier_key = type:value). Each
-- identifier maps to exactly one customer; a customer can have several
-- identifiers (e.g. an email plus a web ID from each device).

with customers as (
    select * from {{ ref('stg_kinetic__customers') }}
    where not is_deleted
),

identity_map as (
    select * from {{ ref('stg_kinetic__identity_map') }}
),

anonymous_ids as (
    select
        'anonymous_id' as identifier_type,
        identity_map.anonymous_id as identifier_value,
        identity_map.customer_id,
        'identity_map_' || identity_map.resolution_type as match_method,
        identity_map.resolved_at as linked_at
    from identity_map
    inner join customers
        on identity_map.customer_id = customers.customer_id
),

emails as (
    select
        'email' as identifier_type,
        lower(trim(email)) as identifier_value,
        customer_id,
        'account_email' as match_method,
        customer_created_at as linked_at
    from customers
    where email is not null
),

unioned as (
    select * from anonymous_ids
    union all
    select * from emails
)

select
    identifier_type || ':' || identifier_value as identifier_key,
    identifier_type,
    identifier_value,
    customer_id,
    match_method,
    linked_at
from unioned
