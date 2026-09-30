-- Internal logic. Returns a row for any month/source/landing page where
-- known + anonymous sessions do not equal sessions, or a rate is outside 0-1.
select traffic_month_id, sessions, known_sessions, anonymous_sessions, known_share_fraction
from {{ ref('mart_traffic_monthly') }}
where known_sessions + anonymous_sessions != sessions
   or known_share_fraction not between 0 and 1
   or avg_session_seconds < 0
