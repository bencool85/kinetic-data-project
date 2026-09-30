-- Every platform should have one row for every day between its first and
-- last date (no silent gaps that would understate spend). Returns platforms
-- whose row count differs from their date span.
select platform, count(*) as n_days, datediff('day', min(report_date), max(report_date)) + 1 as span_days
from {{ ref('int_paid_media_daily') }}
group by platform
having count(*) <> datediff('day', min(report_date), max(report_date)) + 1
