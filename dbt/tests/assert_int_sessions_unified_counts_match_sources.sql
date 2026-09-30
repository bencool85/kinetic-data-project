-- No session lost or duplicated by the union or the identity join: total
-- rows must equal web sessions + app sessions. Returns a row only if not.
select a.unified_n, b.source_n
from (select count(*) as unified_n from {{ ref('int_sessions_unified') }}) a
cross join (
    select
        (select count(*) from {{ ref('stg_kinetic__web_sessions') }})
        + (select count(*) from {{ ref('stg_kinetic__app_sessions') }}) as source_n
) b
where a.unified_n <> b.source_n
