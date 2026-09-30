-- A session cannot end before it starts. Returns offending sessions.
select session_id, started_at, ended_at
from {{ ref('int_sessions_unified') }}
where ended_at < started_at
