-- ============================================================================
-- Kinetic — starter analysis queries against the `kinetic` MotherDuck database
-- ============================================================================
-- Run these in the MotherDuck SQL editor (app.motherduck.com) or via the
-- duckdb Python client once connected with `USE kinetic;`.
--
-- Every query below is commented to explain not just WHAT it does, but WHY
-- it's built that way -- several of these questions don't have a single
-- obvious join path in this schema, so the comments call out the modeling
-- choice made and any real limitation of the underlying data.
-- ============================================================================


-- ----------------------------------------------------------------------------
-- 1. Monthly paid media spend, broken out by partner
-- ----------------------------------------------------------------------------
-- Each of the 6 ad platform tables stores spend in a different unit (Meta in
-- plain dollars, the other 5 in "micros" -- millionths of a dollar, the real
-- API convention those platforms use). This UNIONs all 6 into one normalized
-- dollar-amount series, then rolls each platform's daily rows up to months.
WITH platform_spend AS (
    SELECT date_trunc('month', date) AS month, 'meta' AS partner, spend AS spend_usd
    FROM meta_ad_insights_daily

    UNION ALL

    SELECT date_trunc('month', date), 'google_search', cost_micros / 1000000.0
    FROM google_search_performance_daily

    UNION ALL

    SELECT date_trunc('month', date), 'youtube', cost_micros / 1000000.0
    FROM youtube_performance_daily

    UNION ALL

    SELECT date_trunc('month', date), 'dv360', cost_micros / 1000000.0
    FROM dv360_performance_daily

    UNION ALL

    SELECT date_trunc('month', date), 'snap', spend_micro / 1000000.0
    FROM snap_stats_daily

    UNION ALL

    SELECT date_trunc('month', date), 'tiktok', spend_micro / 1000000.0
    FROM tiktok_reports_daily
)
SELECT
    month,
    partner,
    ROUND(SUM(spend_usd), 2) AS spend_usd
FROM platform_spend
GROUP BY month, partner
ORDER BY month, partner;


-- ----------------------------------------------------------------------------
-- 2. Directly attributed revenue, monthly, broken down by paid vs. owned
-- ----------------------------------------------------------------------------
-- This dataset was deliberately built with NO user-level join between ad
-- platforms and internal data (see docs/schema_reference.md) -- the only
-- attribution path is UTM tags on web_sessions. That creates a real
-- methodology split between the two revenue types:
--
--   * Storefront orders (merch/course) CAN be tied to the exact browsing
--     session that produced them: web_events has a 'purchase' row carrying
--     both the order_id and the session_id, so we can walk
--     order -> purchase event -> session -> utm_source. This is a true
--     session-level, "last-click-on-the-converting-visit" attribution.
--
--   * Subscription billing (invoices) has NO session/order_id to join
--     through -- a renewal invoice isn't "born" from a browsing session the
--     way a storefront purchase is. The closest defensible proxy is
--     customers.signup_source, the customer's own true first-touch
--     acquisition channel, applied to every paid invoice for that customer
--     (the first bill AND every renewal alike). That's a first-touch model,
--     not last-click -- a real difference from the storefront side, flagged
--     here rather than quietly glossed over.
--
-- A small number of storefront orders (17 out of 3,650, ~0.5%) have no
-- matching purchase event at all -- rather than silently lump those into
-- "owned", they get their own 'untracked' bucket so you can see the gap.
WITH order_channel AS (
    SELECT
        o.order_id                        AS revenue_id,
        'storefront'                      AS revenue_type,
        date_trunc('month', o.created_at) AS month,
        o.total_amount                    AS revenue,
        ws.utm_source                     AS utm_source,
        (we.session_id IS NOT NULL)       AS has_tracked_session
    FROM orders o
    LEFT JOIN web_events we
        ON we.order_id = o.order_id AND we.event_type = 'purchase'
    LEFT JOIN web_sessions ws
        ON ws.session_id = we.session_id
),
subscription_channel AS (
    SELECT
        i.invoice_id                      AS revenue_id,
        'subscription'                    AS revenue_type,
        date_trunc('month', i.paid_at)    AS month,
        i.amount_due                      AS revenue,
        c.signup_source                   AS utm_source,
        TRUE                              AS has_tracked_session
    FROM invoices i
    JOIN customers c ON c.customer_id = i.customer_id
    WHERE i.status = 'paid'
),
combined AS (
    SELECT * FROM order_channel
    UNION ALL
    SELECT * FROM subscription_channel
),
classified AS (
    SELECT
        month,
        revenue_type,
        revenue,
        CASE
            WHEN NOT has_tracked_session THEN 'untracked'
            WHEN utm_source IN ('meta', 'google_search', 'youtube', 'dv360', 'snap', 'tiktok') THEN 'paid'
            ELSE 'owned'  -- email/push, organic_direct, or no UTM on a real session (organic/direct traffic)
        END AS channel_group
    FROM combined
)
SELECT
    month,
    channel_group,
    ROUND(SUM(revenue), 2) AS revenue_usd
FROM classified
GROUP BY month, channel_group
ORDER BY month, channel_group;


-- ----------------------------------------------------------------------------
-- 3. Total active subscribers, broken out by month
-- ----------------------------------------------------------------------------
-- "Active subscriber" here means someone who actually converted from trial
-- to PAID billing -- not just someone currently in a free trial. A
-- subscription that was canceled DURING its trial (canceled_at <=
-- trial_end) never became a paying subscriber at all and is excluded
-- entirely, regardless of what the `status` column happens to say.
--
-- A subscription counts as active in a given month if its paid billing had
-- already started by that month's end, and it hadn't been canceled before
-- that month began.
WITH months AS (
    SELECT UNNEST(generate_series(DATE '2023-08-01', DATE '2026-07-01', INTERVAL 1 MONTH)) AS month_start
),
sub_paid_period AS (
    SELECT
        subscription_id,
        CASE
            WHEN trial_start IS NULL THEN start_date                          -- no trial: paid from day one
            WHEN canceled_at IS NOT NULL AND canceled_at <= trial_end THEN NULL  -- canceled during trial: never converted
            ELSE trial_end                                                    -- converted: paid billing starts at trial_end
        END AS paid_start,
        canceled_at
    FROM subscriptions
)
SELECT
    m.month_start                             AS month,
    COUNT(DISTINCT s.subscription_id)         AS active_subscribers
FROM months m
LEFT JOIN sub_paid_period s
    ON s.paid_start IS NOT NULL
    AND s.paid_start <= (m.month_start + INTERVAL 1 MONTH - INTERVAL 1 DAY)
    AND (s.canceled_at IS NULL OR s.canceled_at > m.month_start)
GROUP BY m.month_start
ORDER BY m.month_start;


-- ----------------------------------------------------------------------------
-- 4. Total non-subscription revenue, broken out by month
-- ----------------------------------------------------------------------------
-- "Non-subscription" = storefront revenue (merch + course orders) --
-- subscription billing lives entirely in invoices.csv and is intentionally
-- excluded here. Includes a merch-vs-course split as a bonus, since it's a
-- free extra column off the same query.
SELECT
    date_trunc('month', created_at)                                  AS month,
    ROUND(SUM(total_amount), 2)                                      AS non_subscription_revenue_usd,
    ROUND(SUM(total_amount) FILTER (WHERE order_type = 'merch'), 2)  AS merch_revenue_usd,
    ROUND(SUM(total_amount) FILTER (WHERE order_type = 'course'), 2) AS course_revenue_usd,
    COUNT(*)                                                         AS order_count
FROM orders
GROUP BY month
ORDER BY month;


-- ----------------------------------------------------------------------------
-- 5. Average churn rate by month
-- ----------------------------------------------------------------------------
-- Standard SaaS definition: (subscribers who canceled during the month) /
-- (subscribers who were already active AT THE START of the month). Reuses
-- the same "actually converted" logic as query 3 -- trial-cancels don't
-- count as churn, since they were never paying subscribers to begin with.
WITH months AS (
    SELECT UNNEST(generate_series(DATE '2023-08-01', DATE '2026-07-01', INTERVAL 1 MONTH)) AS month_start
),
sub_paid_period AS (
    SELECT
        subscription_id,
        CASE
            WHEN trial_start IS NULL THEN start_date
            WHEN canceled_at IS NOT NULL AND canceled_at <= trial_end THEN NULL
            ELSE trial_end
        END AS paid_start,
        canceled_at
    FROM subscriptions
),
active_at_month_start AS (
    SELECT
        m.month_start,
        COUNT(DISTINCT s.subscription_id) AS active_subscribers
    FROM months m
    LEFT JOIN sub_paid_period s
        ON s.paid_start IS NOT NULL
        AND s.paid_start < m.month_start
        AND (s.canceled_at IS NULL OR s.canceled_at >= m.month_start)
    GROUP BY m.month_start
),
churned_in_month AS (
    SELECT
        date_trunc('month', canceled_at)  AS month_start,
        COUNT(DISTINCT subscription_id)   AS churned_subscribers
    FROM sub_paid_period
    WHERE paid_start IS NOT NULL  -- only counts people who had actually converted to paid
      AND canceled_at IS NOT NULL
    GROUP BY month_start
)
SELECT
    a.month_start                                        AS month,
    a.active_subscribers                                 AS active_at_start_of_month,
    COALESCE(c.churned_subscribers, 0)                   AS churned_this_month,
    ROUND(COALESCE(c.churned_subscribers, 0) * 100.0 / NULLIF(a.active_subscribers, 0), 2) AS churn_rate_pct
FROM active_at_month_start a
LEFT JOIN churned_in_month c ON c.month_start = a.month_start
ORDER BY a.month_start;


-- ----------------------------------------------------------------------------
-- 6. Highest grossing products, broken out by year
-- ----------------------------------------------------------------------------
-- Top 5 products per calendar year by line-item revenue. QUALIFY lets us
-- filter on a window function (RANK) without wrapping the query in an
-- extra subquery -- a DuckDB/MotherDuck convenience not every SQL engine
-- supports. Change `rank_in_year <= 5` to see more/fewer per year.
WITH product_year_revenue AS (
    SELECT
        p.product_id,
        p.name,
        p.category,
        date_part('year', o.created_at) AS year,
        SUM(oli.line_total)             AS revenue_usd
    FROM order_line_items oli
    JOIN orders o    ON o.order_id = oli.order_id
    JOIN products p  ON p.product_id = oli.product_id
    GROUP BY p.product_id, p.name, p.category, year
)
SELECT
    year,
    name,
    category,
    ROUND(revenue_usd, 2)                                              AS revenue_usd,
    RANK() OVER (PARTITION BY year ORDER BY revenue_usd DESC)          AS rank_in_year
FROM product_year_revenue
QUALIFY rank_in_year <= 5
ORDER BY year, rank_in_year;
