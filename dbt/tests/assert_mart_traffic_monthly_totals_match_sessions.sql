-- Rolling sessions up to months must keep every session and every second.
-- Returns a row if the mart total differs from int_sessions_unified.
select a.mart_sessions, b.src_sessions, a.mart_seconds, b.src_seconds
from (select sum(sessions) as mart_sessions, sum(total_duration_seconds) as mart_seconds
      from {{ ref('mart_traffic_monthly') }}) a
cross join (select count(*) as src_sessions, sum(duration_seconds) as src_seconds
            from {{ ref('int_sessions_unified') }}) b
where a.mart_sessions != b.src_sessions or a.mart_seconds != b.src_seconds
