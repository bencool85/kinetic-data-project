-- No event lost or duplicated by the union or the joins: total rows must
-- equal email events + push events. Returns a row only if not.
select a.unified_n, b.source_n
from (select count(*) as unified_n from {{ ref('int_messaging_events') }}) a
cross join (
    select
        (select count(*) from {{ ref('stg_kinetic__braze_email_events') }})
        + (select count(*) from {{ ref('stg_kinetic__braze_push_events') }}) as source_n
) b
where a.unified_n <> b.source_n
