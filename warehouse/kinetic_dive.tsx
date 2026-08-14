import { useDiveState, useSQLQuery } from '@motherduck/react-sql-query';
import {
	Bar,
	BarChart,
	CartesianGrid,
	Legend,
	Line,
	LineChart,
	ResponsiveContainer,
	Tooltip,
	XAxis,
	YAxis,
} from 'recharts';

export const REQUIRED_DATABASES = [
	{ type: 'database', path: 'md:kinetic', alias: 'kinetic' },
];

const PALETTE = [
	'#0777b3',
	'#bd4e35',
	'#2d7a00',
	'#e18727',
	'#638cad',
	'#adadad',
];
const TEXT = '#231f20';
const MUTED = '#6a6a6a';
const POSITIVE = '#2d7a00';
const NEGATIVE = '#bc1200';

const N = (v: unknown): number => (v == null ? 0 : Number(v));
const usd = (v: number) =>
	Math.abs(v) >= 1000000
		? `$${(v / 1000000).toFixed(1)}M`
		: Math.abs(v) >= 1000
			? `$${(v / 1000).toFixed(1)}K`
			: `$${Math.round(v)}`;
const usdFull = (v: number) => `$${Math.round(v).toLocaleString()}`;
const pct = (v: unknown) => (v == null ? '—' : `${N(v).toFixed(1)}%`);

function ChartSkeleton({ height = 240 }: { height?: number }) {
	return (
		<div
			className="animate-pulse rounded bg-gray-100"
			style={{ height }}
		/>
	);
}

function TableSkeleton() {
	return (
		<div className="animate-pulse space-y-2">
			<div className="h-4 w-3/4 rounded bg-gray-200" />
			<div className="h-4 w-1/2 rounded bg-gray-200" />
			<div className="h-4 w-2/3 rounded bg-gray-200" />
		</div>
	);
}

function ErrorNote({ error }: { error: unknown }) {
	return (
		<p className="text-sm" role="alert" style={{ color: NEGATIVE }}>
			{String(error)}
		</p>
	);
}

const CHANNEL_LABEL: Record<string, string> = {
	meta: 'Meta',
	google_search: 'Google Search',
	tiktok: 'TikTok',
	youtube: 'YouTube',
	dv360: 'DV360',
	snap: 'Snap',
	organic_direct: 'Organic / Direct',
};

// ===========================================================================
// OVERVIEW TAB — the original 6 starter queries + KPI row
// ===========================================================================

const PARTNERS = ['meta', 'google_search', 'tiktok', 'youtube', 'dv360', 'snap'];

function SpendByPartnerSection() {
	const q = useSQLQuery(`
    WITH platform_spend AS (
        SELECT date_trunc('month', date) AS month, 'meta' AS partner, spend AS spend_usd
        FROM "kinetic"."main"."meta_ad_insights_daily"
        UNION ALL
        SELECT date_trunc('month', date), 'google_search', cost_micros / 1000000.0
        FROM "kinetic"."main"."google_search_performance_daily"
        UNION ALL
        SELECT date_trunc('month', date), 'youtube', cost_micros / 1000000.0
        FROM "kinetic"."main"."youtube_performance_daily"
        UNION ALL
        SELECT date_trunc('month', date), 'dv360', cost_micros / 1000000.0
        FROM "kinetic"."main"."dv360_performance_daily"
        UNION ALL
        SELECT date_trunc('month', date), 'snap', spend_micro / 1000000.0
        FROM "kinetic"."main"."snap_stats_daily"
        UNION ALL
        SELECT date_trunc('month', date), 'tiktok', spend_micro / 1000000.0
        FROM "kinetic"."main"."tiktok_reports_daily"
    )
    SELECT strftime(month, '%Y-%m') AS month, partner, ROUND(SUM(spend_usd), 2) AS spend_usd
    FROM platform_spend
    GROUP BY month, partner
    ORDER BY month, partner
  `);

	const rows = Array.isArray(q.data) ? q.data : [];
	const byMonth: Record<string, any> = {};
	rows.forEach((r: any) => {
		const m = String(r.month);
		if (!byMonth[m]) byMonth[m] = { month: m };
		byMonth[m][String(r.partner)] = N(r.spend_usd);
	});
	const chartData = Object.values(byMonth);

	return (
		<section className="mb-8">
			<h2 className="text-lg font-semibold" style={{ color: TEXT }}>
				Monthly paid media spend by partner
			</h2>
			<p className="text-sm mb-3" style={{ color: MUTED }}>
				Aug 2023 – Jul 2026, USD
			</p>
			{q.isLoading ? (
				<ChartSkeleton />
			) : q.isError ? (
				<ErrorNote error={q.error} />
			) : (
				<ResponsiveContainer width="100%" height={260}>
					<LineChart data={chartData}>
						<CartesianGrid strokeDasharray="3 3" stroke="#eee" />
						<XAxis dataKey="month" fontSize={11} interval={2} />
						<YAxis
							tickFormatter={(v) => usd(v)}
							fontSize={11}
							width={48}
						/>
						<Tooltip formatter={(v: number) => usdFull(N(v))} />
						<Legend wrapperStyle={{ fontSize: 11 }} />
						{PARTNERS.map((p, i) => (
							<Line
								key={p}
								type="linear"
								dataKey={p}
								name={CHANNEL_LABEL[p]}
								stroke={PALETTE[i % PALETTE.length]}
								strokeWidth={2}
								dot={false}
							/>
						))}
					</LineChart>
				</ResponsiveContainer>
			)}
		</section>
	);
}

function AttributedRevenueSection() {
	const q = useSQLQuery(`
    WITH order_channel AS (
        SELECT
            o.order_id AS revenue_id,
            'storefront' AS revenue_type,
            date_trunc('month', o.created_at) AS month,
            o.total_amount AS revenue,
            ws.utm_source AS utm_source,
            (we.session_id IS NOT NULL) AS has_tracked_session
        FROM "kinetic"."main"."orders" o
        LEFT JOIN "kinetic"."main"."web_events" we
            ON we.order_id = o.order_id AND we.event_type = 'purchase'
        LEFT JOIN "kinetic"."main"."web_sessions" ws
            ON ws.session_id = we.session_id
    ),
    subscription_channel AS (
        SELECT
            i.invoice_id AS revenue_id,
            'subscription' AS revenue_type,
            date_trunc('month', i.paid_at) AS month,
            i.amount_due AS revenue,
            c.signup_source AS utm_source,
            TRUE AS has_tracked_session
        FROM "kinetic"."main"."invoices" i
        JOIN "kinetic"."main"."customers" c ON c.customer_id = i.customer_id
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
            revenue,
            CASE
                WHEN NOT has_tracked_session THEN 'untracked'
                WHEN utm_source IN ('meta', 'google_search', 'youtube', 'dv360', 'snap', 'tiktok') THEN 'paid'
                ELSE 'owned'
            END AS channel_group
        FROM combined
    )
    SELECT strftime(month, '%Y-%m') AS month, channel_group, ROUND(SUM(revenue), 2) AS revenue_usd
    FROM classified
    GROUP BY month, channel_group
    ORDER BY month, channel_group
  `);

	const rows = Array.isArray(q.data) ? q.data : [];
	const byMonth: Record<string, any> = {};
	rows.forEach((r: any) => {
		const m = String(r.month);
		if (!byMonth[m]) byMonth[m] = { month: m, paid: 0, owned: 0, untracked: 0 };
		byMonth[m][String(r.channel_group)] = N(r.revenue_usd);
	});
	const chartData = Object.values(byMonth);

	return (
		<section className="mb-8">
			<h2 className="text-lg font-semibold" style={{ color: TEXT }}>
				Directly attributed revenue: paid vs. owned channels
			</h2>
			<p className="text-sm mb-3" style={{ color: MUTED }}>
				Storefront orders attributed via session UTM (last-click); subscription
				billing via customer signup_source (first-touch). ~0.5% of storefront
				orders have no matching session and are shown as untracked.
			</p>
			{q.isLoading ? (
				<ChartSkeleton />
			) : q.isError ? (
				<ErrorNote error={q.error} />
			) : (
				<ResponsiveContainer width="100%" height={260}>
					<BarChart data={chartData}>
						<CartesianGrid strokeDasharray="3 3" stroke="#eee" />
						<XAxis dataKey="month" fontSize={11} interval={2} />
						<YAxis tickFormatter={(v) => usd(v)} fontSize={11} width={48} />
						<Tooltip formatter={(v: number) => usdFull(N(v))} />
						<Legend wrapperStyle={{ fontSize: 11 }} />
						<Bar dataKey="paid" name="Paid" stackId="rev" fill={PALETTE[0]} />
						<Bar dataKey="owned" name="Owned" stackId="rev" fill={PALETTE[2]} />
						<Bar
							dataKey="untracked"
							name="Untracked"
							stackId="rev"
							fill={PALETTE[5]}
						/>
					</BarChart>
				</ResponsiveContainer>
			)}
		</section>
	);
}

function ActiveSubscribersSection() {
	const q = useSQLQuery(`
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
        FROM "kinetic"."main"."subscriptions"
    )
    SELECT
        strftime(m.month_start, '%Y-%m') AS month,
        COUNT(DISTINCT s.subscription_id) AS active_subscribers
    FROM months m
    LEFT JOIN sub_paid_period s
        ON s.paid_start IS NOT NULL
        AND s.paid_start <= (m.month_start + INTERVAL 1 MONTH - INTERVAL 1 DAY)
        AND (s.canceled_at IS NULL OR s.canceled_at > m.month_start)
    GROUP BY m.month_start
    ORDER BY m.month_start
  `);

	const rows = Array.isArray(q.data) ? q.data : [];
	const chartData = rows.map((r: any) => ({
		month: String(r.month),
		active_subscribers: N(r.active_subscribers),
	}));
	const latest = chartData[chartData.length - 1]?.active_subscribers ?? 0;

	return (
		<section className="mb-8">
			<h2 className="text-lg font-semibold" style={{ color: TEXT }}>
				Active subscribers by month
			</h2>
			<p className="text-sm mb-3" style={{ color: MUTED }}>
				Counts only subscribers who converted from trial to paid billing
				(trial-only cancels excluded). Latest: {q.isLoading ? '…' : latest}.
			</p>
			{q.isLoading ? (
				<ChartSkeleton />
			) : q.isError ? (
				<ErrorNote error={q.error} />
			) : (
				<ResponsiveContainer width="100%" height={240}>
					<LineChart data={chartData}>
						<CartesianGrid strokeDasharray="3 3" stroke="#eee" />
						<XAxis dataKey="month" fontSize={11} interval={2} />
						<YAxis fontSize={11} width={36} />
						<Tooltip />
						<Line
							type="linear"
							dataKey="active_subscribers"
							name="Active subscribers"
							stroke={PALETTE[0]}
							strokeWidth={2}
							dot={false}
						/>
					</LineChart>
				</ResponsiveContainer>
			)}
		</section>
	);
}

function NonSubscriptionRevenueSection() {
	const q = useSQLQuery(`
    SELECT
        strftime(date_trunc('month', created_at), '%Y-%m') AS month,
        ROUND(SUM(total_amount) FILTER (WHERE order_type = 'merch'), 2) AS merch_revenue_usd,
        ROUND(SUM(total_amount) FILTER (WHERE order_type = 'course'), 2) AS course_revenue_usd
    FROM "kinetic"."main"."orders"
    GROUP BY 1
    ORDER BY 1
  `);

	const rows = Array.isArray(q.data) ? q.data : [];
	const chartData = rows.map((r: any) => ({
		month: String(r.month),
		merch: N(r.merch_revenue_usd),
		course: N(r.course_revenue_usd),
	}));

	return (
		<section className="mb-8">
			<h2 className="text-lg font-semibold" style={{ color: TEXT }}>
				Non-subscription revenue by month
			</h2>
			<p className="text-sm mb-3" style={{ color: MUTED }}>
				Storefront orders only (merch + course) — excludes subscription
				billing.
			</p>
			{q.isLoading ? (
				<ChartSkeleton />
			) : q.isError ? (
				<ErrorNote error={q.error} />
			) : (
				<ResponsiveContainer width="100%" height={240}>
					<BarChart data={chartData}>
						<CartesianGrid strokeDasharray="3 3" stroke="#eee" />
						<XAxis dataKey="month" fontSize={11} interval={2} />
						<YAxis tickFormatter={(v) => usd(v)} fontSize={11} width={48} />
						<Tooltip formatter={(v: number) => usdFull(N(v))} />
						<Legend wrapperStyle={{ fontSize: 11 }} />
						<Bar dataKey="merch" name="Merch" stackId="rev" fill={PALETTE[0]} />
						<Bar
							dataKey="course"
							name="Course"
							stackId="rev"
							fill={PALETTE[3]}
						/>
					</BarChart>
				</ResponsiveContainer>
			)}
		</section>
	);
}

function ChurnRateSection() {
	const q = useSQLQuery(`
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
        FROM "kinetic"."main"."subscriptions"
    ),
    active_at_month_start AS (
        SELECT m.month_start, COUNT(DISTINCT s.subscription_id) AS active_subscribers
        FROM months m
        LEFT JOIN sub_paid_period s
            ON s.paid_start IS NOT NULL AND s.paid_start < m.month_start
            AND (s.canceled_at IS NULL OR s.canceled_at >= m.month_start)
        GROUP BY m.month_start
    ),
    churned_in_month AS (
        SELECT date_trunc('month', canceled_at) AS month_start, COUNT(DISTINCT subscription_id) AS churned_subscribers
        FROM sub_paid_period
        WHERE paid_start IS NOT NULL AND canceled_at IS NOT NULL
        GROUP BY month_start
    )
    SELECT
        strftime(a.month_start, '%Y-%m') AS month,
        a.active_subscribers AS active_at_start_of_month,
        COALESCE(c.churned_subscribers, 0) AS churned_this_month,
        ROUND(COALESCE(c.churned_subscribers, 0) * 100.0 / NULLIF(a.active_subscribers, 0), 2) AS churn_rate_pct
    FROM active_at_month_start a
    LEFT JOIN churned_in_month c ON c.month_start = a.month_start
    ORDER BY a.month_start
  `);

	const rows = Array.isArray(q.data) ? q.data : [];
	const chartData = rows.map((r: any) => ({
		month: String(r.month),
		churn_rate_pct: r.churn_rate_pct == null ? null : N(r.churn_rate_pct),
	}));
	const valid = chartData.filter((d) => d.churn_rate_pct != null);
	const avgChurn = valid.length
		? valid.reduce((s, d) => s + (d.churn_rate_pct as number), 0) / valid.length
		: 0;

	return (
		<section className="mb-8">
			<h2 className="text-lg font-semibold" style={{ color: TEXT }}>
				Monthly churn rate
			</h2>
			<p className="text-sm mb-3" style={{ color: MUTED }}>
				Canceled-this-month ÷ active-at-start-of-month. Average across the
				window: {q.isLoading ? '…' : `${avgChurn.toFixed(1)}%`}.
			</p>
			{q.isLoading ? (
				<ChartSkeleton />
			) : q.isError ? (
				<ErrorNote error={q.error} />
			) : (
				<ResponsiveContainer width="100%" height={240}>
					<LineChart data={chartData}>
						<CartesianGrid strokeDasharray="3 3" stroke="#eee" />
						<XAxis dataKey="month" fontSize={11} interval={2} />
						<YAxis
							tickFormatter={(v) => `${v}%`}
							fontSize={11}
							width={40}
						/>
						<Tooltip formatter={(v: number) => `${N(v).toFixed(1)}%`} />
						<Line
							type="linear"
							dataKey="churn_rate_pct"
							name="Churn rate"
							stroke={PALETTE[1]}
							strokeWidth={2}
							dot={false}
							connectNulls
						/>
					</LineChart>
				</ResponsiveContainer>
			)}
		</section>
	);
}

function TopProductsSection() {
	const q = useSQLQuery(`
    WITH product_year_revenue AS (
        SELECT
            p.name,
            p.category,
            date_part('year', o.created_at) AS year,
            SUM(oli.line_total) AS revenue_usd
        FROM "kinetic"."main"."order_line_items" oli
        JOIN "kinetic"."main"."orders" o ON o.order_id = oli.order_id
        JOIN "kinetic"."main"."products" p ON p.product_id = oli.product_id
        GROUP BY p.name, p.category, year
    )
    SELECT year, name, category, ROUND(revenue_usd, 2) AS revenue_usd,
        RANK() OVER (PARTITION BY year ORDER BY revenue_usd DESC) AS rank_in_year
    FROM product_year_revenue
    QUALIFY rank_in_year <= 5
    ORDER BY year, rank_in_year
  `);

	const rows = Array.isArray(q.data) ? q.data : [];
	const years = Array.from(new Set(rows.map((r: any) => String(r.year)))).sort();

	return (
		<section className="mb-4">
			<h2 className="text-lg font-semibold" style={{ color: TEXT }}>
				Top 5 grossing products by year
			</h2>
			<p className="text-sm mb-3" style={{ color: MUTED }}>
				Ranked by order-line revenue.
			</p>
			{q.isLoading ? (
				<TableSkeleton />
			) : q.isError ? (
				<ErrorNote error={q.error} />
			) : (
				<div className="grid grid-cols-4 gap-4">
					{years.map((year) => (
						<div key={year}>
							<p className="text-sm font-semibold mb-2" style={{ color: TEXT }}>
								{year}
							</p>
							<table className="w-full text-sm">
								<tbody>
									{rows
										.filter((r: any) => String(r.year) === year)
										.map((r: any) => (
											<tr key={String(r.rank_in_year)}>
												<td
													className="py-1 pr-2"
													style={{ color: MUTED, width: 18 }}
												>
													{String(r.rank_in_year)}
												</td>
												<td className="py-1 pr-2" style={{ color: TEXT }}>
													{String(r.name)}
												</td>
												<td
													className="py-1 text-right"
													style={{ color: TEXT }}
												>
													{usd(N(r.revenue_usd))}
												</td>
											</tr>
										))}
								</tbody>
							</table>
						</div>
					))}
				</div>
			)}
		</section>
	);
}

function KpiRow() {
	const q = useSQLQuery(`
    SELECT
        (SELECT ROUND(SUM(spend), 2) FROM "kinetic"."main"."meta_ad_insights_daily") +
        (SELECT ROUND(SUM(cost_micros)/1000000.0, 2) FROM "kinetic"."main"."google_search_performance_daily") +
        (SELECT ROUND(SUM(cost_micros)/1000000.0, 2) FROM "kinetic"."main"."youtube_performance_daily") +
        (SELECT ROUND(SUM(cost_micros)/1000000.0, 2) FROM "kinetic"."main"."dv360_performance_daily") +
        (SELECT ROUND(SUM(spend_micro)/1000000.0, 2) FROM "kinetic"."main"."snap_stats_daily") +
        (SELECT ROUND(SUM(spend_micro)/1000000.0, 2) FROM "kinetic"."main"."tiktok_reports_daily")
          AS total_paid_media_spend,
        (SELECT COUNT(*) FROM "kinetic"."main"."orders") AS total_orders,
        (SELECT ROUND(SUM(total_amount), 2) FROM "kinetic"."main"."orders") AS total_storefront_revenue,
        (SELECT COUNT(*) FROM "kinetic"."main"."subscriptions" WHERE status = 'active') AS active_subs_now
  `);

	const r = Array.isArray(q.data) && q.data.length ? (q.data[0] as any) : null;
	const kpis = [
		{ label: 'Total paid media spend', value: r ? usd(N(r.total_paid_media_spend)) : null },
		{ label: 'Storefront revenue', value: r ? usd(N(r.total_storefront_revenue)) : null },
		{ label: 'Total orders', value: r ? N(r.total_orders).toLocaleString() : null },
		{ label: 'Active subscribers (now)', value: r ? N(r.active_subs_now).toLocaleString() : null },
	];

	return (
		<div className="grid grid-cols-4 gap-8 mb-8">
			{kpis.map((k) => (
				<div key={k.label}>
					{q.isLoading || k.value == null ? (
						<div className="h-12 w-24 bg-gray-200 animate-pulse rounded" />
					) : (
						<p className="text-4xl font-bold" style={{ color: TEXT }}>
							{k.value}
						</p>
					)}
					<p className="text-sm mt-2" style={{ color: MUTED }}>
						{k.label}
					</p>
				</div>
			))}
		</div>
	);
}

function OverviewTab() {
	return (
		<div>
			<KpiRow />
			<SpendByPartnerSection />
			<AttributedRevenueSection />
			<ActiveSubscribersSection />
			<NonSubscriptionRevenueSection />
			<ChurnRateSection />
			<TopProductsSection />
		</div>
	);
}

// ===========================================================================
// CEO TAB
// ===========================================================================

const MONTHLY_SPEND_CTE = `
    monthly_spend AS (
        SELECT date_trunc('month', d) AS month, SUM(spend) AS total_spend FROM (
            SELECT date AS d, spend FROM "kinetic"."main"."meta_ad_insights_daily"
            UNION ALL SELECT date, cost_micros/1000000.0 FROM "kinetic"."main"."google_search_performance_daily"
            UNION ALL SELECT date, cost_micros/1000000.0 FROM "kinetic"."main"."youtube_performance_daily"
            UNION ALL SELECT date, cost_micros/1000000.0 FROM "kinetic"."main"."dv360_performance_daily"
            UNION ALL SELECT date, spend_micro/1000000.0 FROM "kinetic"."main"."snap_stats_daily"
            UNION ALL SELECT date, spend_micro/1000000.0 FROM "kinetic"."main"."tiktok_reports_daily"
        ) x GROUP BY 1
    )`;

// CEO story 1: revenue growth, net-new vs. churned subscribers, CAC payback trend
function RevenueGrowthSection() {
	const q = useSQLQuery(`
    WITH months AS (
        SELECT UNNEST(generate_series(DATE '2023-08-01', DATE '2026-07-01', INTERVAL 1 MONTH)) AS month_start
    ),
    ${MONTHLY_SPEND_CTE},
    sub_paid_period AS (
        SELECT subscription_id, customer_id, plan_id,
            CASE WHEN trial_start IS NULL THEN start_date
                 WHEN canceled_at IS NOT NULL AND canceled_at <= trial_end THEN NULL
                 ELSE trial_end END AS paid_start,
            canceled_at
        FROM "kinetic"."main"."subscriptions"
    ),
    new_conv AS (
        SELECT p.subscription_id, p.customer_id, date_trunc('month', p.paid_start) AS month,
            CASE WHEN sp.billing_interval = 'year' THEN sp.price / 12.0 ELSE sp.price END AS monthly_price
        FROM sub_paid_period p JOIN "kinetic"."main"."subscription_plans" sp ON sp.plan_id = p.plan_id
        WHERE p.paid_start IS NOT NULL
    ),
    monthly_new AS (
        SELECT month, COUNT(DISTINCT customer_id) AS new_customers, AVG(monthly_price) AS arpu_monthly
        FROM new_conv GROUP BY 1
    ),
    churned AS (
        SELECT date_trunc('month', canceled_at) AS month, COUNT(DISTINCT subscription_id) AS churned_customers
        FROM sub_paid_period WHERE paid_start IS NOT NULL AND canceled_at IS NOT NULL GROUP BY 1
    ),
    revenue AS (
        SELECT month, SUM(rev) AS total_revenue FROM (
            SELECT date_trunc('month', paid_at) AS month, amount_due AS rev FROM "kinetic"."main"."invoices" WHERE status = 'paid'
            UNION ALL SELECT date_trunc('month', created_at), total_amount FROM "kinetic"."main"."orders"
        ) x GROUP BY 1
    )
    SELECT
        strftime(m.month_start, '%Y-%m') AS month,
        ROUND(COALESCE(r.total_revenue, 0), 2) AS total_revenue,
        ROUND(100.0 * (COALESCE(r.total_revenue, 0) - LAG(COALESCE(r.total_revenue, 0)) OVER (ORDER BY m.month_start))
            / NULLIF(LAG(COALESCE(r.total_revenue, 0)) OVER (ORDER BY m.month_start), 0), 2) AS mom_growth_pct,
        COALESCE(mn.new_customers, 0) AS new_paying_customers,
        COALESCE(ch.churned_customers, 0) AS churned_customers,
        ROUND(ms.total_spend / NULLIF(mn.new_customers, 0), 2) AS cac_usd,
        ROUND(mn.arpu_monthly, 2) AS arpu_monthly_usd,
        ROUND((ms.total_spend / NULLIF(mn.new_customers, 0)) / NULLIF(mn.arpu_monthly, 0), 2) AS cac_payback_months
    FROM months m
    LEFT JOIN revenue r ON r.month = m.month_start
    LEFT JOIN monthly_new mn ON mn.month = m.month_start
    LEFT JOIN churned ch ON ch.month = m.month_start
    LEFT JOIN monthly_spend ms ON ms.month = m.month_start
    ORDER BY m.month_start
  `);

	const rows = Array.isArray(q.data) ? q.data : [];
	const chartData = rows.map((r: any) => ({
		month: String(r.month),
		new_customers: N(r.new_paying_customers),
		churned_customers: N(r.churned_customers),
		cac_payback_months: r.cac_payback_months == null ? null : N(r.cac_payback_months),
	}));
	const last = rows[rows.length - 1] as any;
	const revenueGrowth = last ? pct(last.mom_growth_pct) : '—';
	const revenueGrowthPositive = last && N(last.mom_growth_pct) >= 0;

	return (
		<section className="mb-8">
			<h2 className="text-lg font-semibold" style={{ color: TEXT }}>
				Revenue growth, net-new vs. churned subscribers, CAC payback
			</h2>
			<p className="text-sm mb-3" style={{ color: MUTED }}>
				CAC uses total company-wide paid media spend ÷ net-new converted
				subscribers that month (a blended figure, not channel-specific).
				Payback = CAC ÷ ARPU of that month's new subscribers. Early months
				have very small subscriber counts, so CAC swings widely — treat the
				first two quarters as noisy.
			</p>
			<div className="mb-4">
				{q.isLoading ? (
					<div className="h-10 w-32 bg-gray-200 animate-pulse rounded" />
				) : (
					<p
						className="text-3xl font-bold"
						style={{ color: revenueGrowthPositive ? POSITIVE : NEGATIVE }}
					>
						{revenueGrowth}
					</p>
				)}
				<p className="text-sm mt-1" style={{ color: MUTED }}>
					Latest month revenue growth, month-over-month
				</p>
			</div>
			{q.isLoading ? (
				<ChartSkeleton height={200} />
			) : q.isError ? (
				<ErrorNote error={q.error} />
			) : (
				<>
					<p className="text-sm font-medium mb-1" style={{ color: TEXT }}>
						Net-new vs. churned paying subscribers
					</p>
					<ResponsiveContainer width="100%" height={200}>
						<BarChart data={chartData}>
							<CartesianGrid strokeDasharray="3 3" stroke="#eee" />
							<XAxis dataKey="month" fontSize={11} interval={2} />
							<YAxis fontSize={11} width={32} />
							<Tooltip />
							<Legend wrapperStyle={{ fontSize: 11 }} />
							<Bar dataKey="new_customers" name="New" fill={PALETTE[2]} />
							<Bar dataKey="churned_customers" name="Churned" fill={PALETTE[1]} />
						</BarChart>
					</ResponsiveContainer>

					<p className="text-sm font-medium mb-1 mt-4" style={{ color: TEXT }}>
						CAC payback period
					</p>
					<ResponsiveContainer width="100%" height={200}>
						<LineChart data={chartData}>
							<CartesianGrid strokeDasharray="3 3" stroke="#eee" />
							<XAxis dataKey="month" fontSize={11} interval={2} />
							<YAxis
								tickFormatter={(v) => `${v}mo`}
								fontSize={11}
								width={40}
							/>
							<Tooltip formatter={(v: number) => `${N(v).toFixed(1)} months`} />
							<Line
								type="linear"
								dataKey="cac_payback_months"
								name="CAC payback (months)"
								stroke={PALETTE[0]}
								strokeWidth={2}
								dot={false}
								connectNulls
							/>
						</LineChart>
					</ResponsiveContainer>
				</>
			)}
		</section>
	);
}

// CEO story 2: revenue mix across subscription / course / merch
function RevenueMixSection() {
	const q = useSQLQuery(`
    WITH months AS (
        SELECT UNNEST(generate_series(DATE '2023-08-01', DATE '2026-07-01', INTERVAL 1 MONTH)) AS month_start
    ),
    rev AS (
        SELECT date_trunc('month', paid_at) AS month, 'subscription' AS line, amount_due AS amt
        FROM "kinetic"."main"."invoices" WHERE status = 'paid'
        UNION ALL
        SELECT date_trunc('month', created_at), order_type, total_amount FROM "kinetic"."main"."orders"
    )
    SELECT strftime(m.month_start, '%Y-%m') AS month,
        ROUND(COALESCE(SUM(r.amt) FILTER (WHERE r.line = 'subscription'), 0), 2) AS subscription_revenue,
        ROUND(COALESCE(SUM(r.amt) FILTER (WHERE r.line = 'merch'), 0), 2) AS merch_revenue,
        ROUND(COALESCE(SUM(r.amt) FILTER (WHERE r.line = 'course'), 0), 2) AS course_revenue
    FROM months m LEFT JOIN rev r ON r.month = m.month_start
    GROUP BY m.month_start ORDER BY m.month_start
  `);

	const rows = Array.isArray(q.data) ? q.data : [];
	const chartData = rows.map((r: any) => ({
		month: String(r.month),
		subscription: N(r.subscription_revenue),
		merch: N(r.merch_revenue),
		course: N(r.course_revenue),
	}));

	return (
		<section className="mb-8">
			<h2 className="text-lg font-semibold" style={{ color: TEXT }}>
				Revenue mix: subscription vs. course vs. merch
			</h2>
			<p className="text-sm mb-3" style={{ color: MUTED }}>
				How dependent the business is on recurring subscription revenue vs.
				one-time storefront sales, by month.
			</p>
			{q.isLoading ? (
				<ChartSkeleton />
			) : q.isError ? (
				<ErrorNote error={q.error} />
			) : (
				<ResponsiveContainer width="100%" height={260}>
					<BarChart data={chartData}>
						<CartesianGrid strokeDasharray="3 3" stroke="#eee" />
						<XAxis dataKey="month" fontSize={11} interval={2} />
						<YAxis tickFormatter={(v) => usd(v)} fontSize={11} width={48} />
						<Tooltip formatter={(v: number) => usdFull(N(v))} />
						<Legend wrapperStyle={{ fontSize: 11 }} />
						<Bar dataKey="subscription" name="Subscription" stackId="rev" fill={PALETTE[0]} />
						<Bar dataKey="merch" name="Merch" stackId="rev" fill={PALETTE[3]} />
						<Bar dataKey="course" name="Course" stackId="rev" fill={PALETTE[2]} />
					</BarChart>
				</ResponsiveContainer>
			)}
		</section>
	);
}

function CeoTab() {
	return (
		<div>
			<RevenueGrowthSection />
			<RevenueMixSection />
		</div>
	);
}

// ===========================================================================
// CMO TAB
// ===========================================================================

// CMO story 1: acquisition funnel (sessions -> trial starts -> paid conversions) by channel
function FunnelByChannelSection() {
	const q = useSQLQuery(`
    WITH sessions_by_channel AS (
        SELECT utm_source AS channel, COUNT(DISTINCT session_id) AS sessions
        FROM "kinetic"."main"."web_sessions"
        WHERE utm_source IN ('meta','google_search','youtube','dv360','snap','tiktok')
        GROUP BY 1
    ),
    trials_by_channel AS (
        SELECT c.signup_source AS channel, COUNT(DISTINCT s.subscription_id) AS trials_started
        FROM "kinetic"."main"."subscriptions" s JOIN "kinetic"."main"."customers" c ON c.customer_id = s.customer_id
        WHERE s.trial_start IS NOT NULL GROUP BY 1
    ),
    converted_by_channel AS (
        SELECT c.signup_source AS channel, COUNT(DISTINCT s.subscription_id) AS trials_converted
        FROM "kinetic"."main"."subscriptions" s JOIN "kinetic"."main"."customers" c ON c.customer_id = s.customer_id
        WHERE s.trial_start IS NOT NULL AND s.start_date = s.trial_end GROUP BY 1
    ),
    channels AS (
        SELECT channel FROM sessions_by_channel
        UNION SELECT channel FROM trials_by_channel
        UNION SELECT channel FROM converted_by_channel
    )
    SELECT ch.channel,
        COALESCE(sc.sessions, 0) AS sessions,
        COALESCE(tc.trials_started, 0) AS trials_started,
        COALESCE(cc.trials_converted, 0) AS trials_converted,
        ROUND(100.0 * COALESCE(cc.trials_converted, 0) / NULLIF(tc.trials_started, 0), 1) AS trial_conversion_rate_pct
    FROM channels ch
    LEFT JOIN sessions_by_channel sc ON sc.channel = ch.channel
    LEFT JOIN trials_by_channel tc ON tc.channel = ch.channel
    LEFT JOIN converted_by_channel cc ON cc.channel = ch.channel
    ORDER BY sessions DESC NULLS LAST
  `);

	const rows = Array.isArray(q.data) ? q.data : [];

	return (
		<section className="mb-8">
			<h2 className="text-lg font-semibold" style={{ color: TEXT }}>
				Acquisition funnel by channel: sessions → trial starts → conversions
			</h2>
			<p className="text-sm mb-3" style={{ color: MUTED }}>
				Sessions use the visit's own UTM tag (last-touch); trial starts and
				conversions use the customer's signup_source (first-touch) — the same
				split documented on the Overview tab. "Organic / Direct" has no paid
				session count by definition. All-time totals, not monthly.
			</p>
			{q.isLoading ? (
				<TableSkeleton />
			) : q.isError ? (
				<ErrorNote error={q.error} />
			) : (
				<table className="w-full text-sm">
					<thead>
						<tr style={{ color: MUTED }}>
							<th className="text-left py-1 font-medium">Channel</th>
							<th className="text-right py-1 font-medium">Sessions</th>
							<th className="text-right py-1 font-medium">Trial starts</th>
							<th className="text-right py-1 font-medium">Conversions</th>
							<th className="text-right py-1 font-medium">Trial→paid rate</th>
						</tr>
					</thead>
					<tbody>
						{rows.map((r: any) => (
							<tr key={String(r.channel)}>
								<td className="py-1" style={{ color: TEXT }}>
									{CHANNEL_LABEL[String(r.channel)] ?? String(r.channel)}
								</td>
								<td className="py-1 text-right" style={{ color: TEXT }}>
									{N(r.sessions).toLocaleString()}
								</td>
								<td className="py-1 text-right" style={{ color: TEXT }}>
									{N(r.trials_started).toLocaleString()}
								</td>
								<td className="py-1 text-right" style={{ color: TEXT }}>
									{N(r.trials_converted).toLocaleString()}
								</td>
								<td className="py-1 text-right" style={{ color: TEXT }}>
									{pct(r.trial_conversion_rate_pct)}
								</td>
							</tr>
						))}
					</tbody>
				</table>
			)}
		</section>
	);
}

// CMO story 2: retention & app engagement by original acquisition channel
function RetentionByChannelSection() {
	const q = useSQLQuery(`
    SELECT c.signup_source AS channel,
        COUNT(*) AS customers,
        ROUND(100.0 * SUM(CASE WHEN EXISTS(
            SELECT 1 FROM "kinetic"."main"."subscriptions" s
            WHERE s.customer_id = c.customer_id AND s.status = 'active'
        ) THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_active_subscriber,
        ROUND(AVG((SELECT COUNT(*) FROM "kinetic"."main"."app_sessions" a WHERE a.customer_id = c.customer_id)), 1) AS avg_app_sessions,
        ROUND(AVG((SELECT COUNT(*) FROM "kinetic"."main"."orders" o WHERE o.customer_id = c.customer_id)), 2) AS avg_orders
    FROM "kinetic"."main"."customers" c
    WHERE c.is_deleted = false
    GROUP BY 1
    ORDER BY pct_active_subscriber DESC
  `);

	const rows = Array.isArray(q.data) ? q.data : [];

	return (
		<section className="mb-4">
			<h2 className="text-lg font-semibold" style={{ color: TEXT }}>
				Retention &amp; app engagement by acquisition channel
			</h2>
			<p className="text-sm mb-3" style={{ color: MUTED }}>
				A channel with a higher upfront CAC can still be worth the spend if
				its customers stay active longer and use the app more.
			</p>
			{q.isLoading ? (
				<TableSkeleton />
			) : q.isError ? (
				<ErrorNote error={q.error} />
			) : (
				<table className="w-full text-sm">
					<thead>
						<tr style={{ color: MUTED }}>
							<th className="text-left py-1 font-medium">Channel</th>
							<th className="text-right py-1 font-medium">Customers</th>
							<th className="text-right py-1 font-medium">% active subscriber</th>
							<th className="text-right py-1 font-medium">Avg. app sessions</th>
							<th className="text-right py-1 font-medium">Avg. orders</th>
						</tr>
					</thead>
					<tbody>
						{rows.map((r: any) => (
							<tr key={String(r.channel)}>
								<td className="py-1" style={{ color: TEXT }}>
									{CHANNEL_LABEL[String(r.channel)] ?? String(r.channel)}
								</td>
								<td className="py-1 text-right" style={{ color: TEXT }}>
									{N(r.customers).toLocaleString()}
								</td>
								<td className="py-1 text-right" style={{ color: TEXT }}>
									{pct(r.pct_active_subscriber)}
								</td>
								<td className="py-1 text-right" style={{ color: TEXT }}>
									{N(r.avg_app_sessions).toFixed(1)}
								</td>
								<td className="py-1 text-right" style={{ color: TEXT }}>
									{N(r.avg_orders).toFixed(2)}
								</td>
							</tr>
						))}
					</tbody>
				</table>
			)}
		</section>
	);
}

function CmoTab() {
	return (
		<div>
			<FunnelByChannelSection />
			<RetentionByChannelSection />
		</div>
	);
}

// ===========================================================================
// CFO TAB
// ===========================================================================

// CFO story 1: CAC and LTV:CAC by monthly cohort
function CohortCacLtvSection() {
	const q = useSQLQuery(`
    WITH months AS (
        SELECT UNNEST(generate_series(DATE '2023-08-01', DATE '2026-07-01', INTERVAL 1 MONTH)) AS month_start
    ),
    ${MONTHLY_SPEND_CTE},
    sub_paid_period AS (
        SELECT subscription_id, customer_id,
            CASE WHEN trial_start IS NULL THEN start_date
                 WHEN canceled_at IS NOT NULL AND canceled_at <= trial_end THEN NULL
                 ELSE trial_end END AS paid_start
        FROM "kinetic"."main"."subscriptions"
    ),
    customer_cohort AS (
        SELECT customer_id, MIN(paid_start) AS first_paid_start
        FROM sub_paid_period WHERE paid_start IS NOT NULL GROUP BY 1
    ),
    customer_ltv AS (
        SELECT c.customer_id,
            COALESCE((SELECT SUM(amount_due) FROM "kinetic"."main"."invoices" i WHERE i.customer_id = c.customer_id AND i.status = 'paid'), 0)
            + COALESCE((SELECT SUM(total_amount) FROM "kinetic"."main"."orders" o WHERE o.customer_id = c.customer_id), 0) AS ltv
        FROM "kinetic"."main"."customers" c
    ),
    cohort_summary AS (
        SELECT date_trunc('month', cc.first_paid_start) AS cohort_month,
            COUNT(DISTINCT cc.customer_id) AS new_customers,
            AVG(ltv.ltv) AS avg_ltv
        FROM customer_cohort cc JOIN customer_ltv ltv ON ltv.customer_id = cc.customer_id
        GROUP BY 1
    )
    SELECT strftime(m.month_start, '%Y-%m') AS month,
        COALESCE(cs.new_customers, 0) AS new_customers,
        ROUND(cs.avg_ltv, 2) AS avg_ltv_usd,
        ROUND(ms.total_spend / NULLIF(cs.new_customers, 0), 2) AS cac_usd,
        ROUND(cs.avg_ltv / NULLIF(ms.total_spend / NULLIF(cs.new_customers, 0), 0), 2) AS ltv_cac_ratio
    FROM months m
    LEFT JOIN cohort_summary cs ON cs.cohort_month = m.month_start
    LEFT JOIN monthly_spend ms ON ms.month = m.month_start
    ORDER BY m.month_start
  `);

	const rows = Array.isArray(q.data) ? q.data : [];
	const chartData = rows.map((r: any) => ({
		month: String(r.month),
		cac_usd: r.cac_usd == null ? null : N(r.cac_usd),
		ltv_cac_ratio: r.ltv_cac_ratio == null ? null : N(r.ltv_cac_ratio),
	}));

	return (
		<section className="mb-8">
			<h2 className="text-lg font-semibold" style={{ color: TEXT }}>
				CAC and LTV:CAC by acquisition cohort
			</h2>
			<p className="text-sm mb-3" style={{ color: MUTED }}>
				Cohort = the month a customer's subscription first converted to paid.
				LTV = lifetime subscription + storefront revenue booked to date, so
				later cohorts are inherently understated (less time to accumulate
				revenue) — read the trend, not the absolute level of recent months.
				Blended CAC (total company spend ÷ new paying customers that month),
				not channel-specific. Early cohorts are tiny (1–5 customers) and
				noisy.
			</p>
			{q.isLoading ? (
				<ChartSkeleton height={200} />
			) : q.isError ? (
				<ErrorNote error={q.error} />
			) : (
				<>
					<p className="text-sm font-medium mb-1" style={{ color: TEXT }}>
						CAC by cohort month
					</p>
					<ResponsiveContainer width="100%" height={200}>
						<BarChart data={chartData}>
							<CartesianGrid strokeDasharray="3 3" stroke="#eee" />
							<XAxis dataKey="month" fontSize={11} interval={2} />
							<YAxis tickFormatter={(v) => usd(v)} fontSize={11} width={48} />
							<Tooltip formatter={(v: number) => usdFull(N(v))} />
							<Bar dataKey="cac_usd" name="CAC" fill={PALETTE[0]} />
						</BarChart>
					</ResponsiveContainer>

					<p className="text-sm font-medium mb-1 mt-4" style={{ color: TEXT }}>
						LTV:CAC ratio by cohort month
					</p>
					<ResponsiveContainer width="100%" height={200}>
						<LineChart data={chartData}>
							<CartesianGrid strokeDasharray="3 3" stroke="#eee" />
							<XAxis dataKey="month" fontSize={11} interval={2} />
							<YAxis fontSize={11} width={32} />
							<Tooltip formatter={(v: number) => `${N(v).toFixed(2)}×`} />
							<Line
								type="linear"
								dataKey="ltv_cac_ratio"
								name="LTV:CAC"
								stroke={PALETTE[4]}
								strokeWidth={2}
								dot={false}
								connectNulls
							/>
						</LineChart>
					</ResponsiveContainer>
				</>
			)}
		</section>
	);
}

// CFO story 2: discount code cost + failed-payment recovery, alongside a net-margin proxy
function MarginDiscountSection() {
	const trend = useSQLQuery(`
    WITH months AS (
        SELECT UNNEST(generate_series(DATE '2023-08-01', DATE '2026-07-01', INTERVAL 1 MONTH)) AS month_start
    ),
    gross AS (
        SELECT month, SUM(g) AS gross_revenue FROM (
            SELECT date_trunc('month', paid_at) AS month, amount_due AS g FROM "kinetic"."main"."invoices" WHERE status = 'paid'
            UNION ALL SELECT date_trunc('month', created_at), total_amount FROM "kinetic"."main"."orders"
        ) x GROUP BY 1
    ),
    discounts AS (
        SELECT date_trunc('month', created_at) AS month,
            COUNT(*) FILTER (WHERE discount_code_id IS NOT NULL) AS orders_with_code,
            SUM(COALESCE(discount_code_amount, 0) + COALESCE(subscriber_discount_amount, 0)) AS discount_given
        FROM "kinetic"."main"."orders" GROUP BY 1
    ),
    refund AS (
        SELECT date_trunc('month', refunded_at) AS month, SUM(amount) AS refund_amount
        FROM "kinetic"."main"."refunds" WHERE status = 'succeeded' GROUP BY 1
    )
    SELECT strftime(m.month_start, '%Y-%m') AS month,
        ROUND(COALESCE(g.gross_revenue, 0), 2) AS gross_revenue,
        COALESCE(d.orders_with_code, 0) AS orders_with_code,
        ROUND(COALESCE(d.discount_given, 0), 2) AS discount_given,
        ROUND(COALESCE(r.refund_amount, 0), 2) AS refund_amount,
        ROUND((COALESCE(g.gross_revenue, 0) - COALESCE(d.discount_given, 0) - COALESCE(r.refund_amount, 0)) * 100.0
            / NULLIF(g.gross_revenue, 0), 2) AS net_margin_proxy_pct
    FROM months m
    LEFT JOIN gross g ON g.month = m.month_start
    LEFT JOIN discounts d ON d.month = m.month_start
    LEFT JOIN refund r ON r.month = m.month_start
    ORDER BY m.month_start
  `);

	const recovery = useSQLQuery(`
    WITH failed_orders AS (SELECT DISTINCT order_id FROM "kinetic"."main"."payments" WHERE status = 'failed'),
    recovered AS (
        SELECT fo.order_id, EXISTS(
            SELECT 1 FROM "kinetic"."main"."payments" p WHERE p.order_id = fo.order_id AND p.status = 'succeeded'
        ) AS is_recovered
        FROM failed_orders fo
    )
    SELECT COUNT(*) AS orders_with_failed_payment,
        SUM(CASE WHEN is_recovered THEN 1 ELSE 0 END) AS recovered_count,
        ROUND(100.0 * SUM(CASE WHEN is_recovered THEN 1 ELSE 0 END) / COUNT(*), 2) AS recovery_rate_pct
    FROM recovered
  `);

	const trendRows = Array.isArray(trend.data) ? trend.data : [];
	const chartData = trendRows.map((r: any) => ({
		month: String(r.month),
		discount_given: N(r.discount_given),
		net_margin_proxy_pct: r.net_margin_proxy_pct == null ? null : N(r.net_margin_proxy_pct),
	}));
	const rec = Array.isArray(recovery.data) && recovery.data.length ? (recovery.data[0] as any) : null;

	return (
		<section className="mb-4">
			<h2 className="text-lg font-semibold" style={{ color: TEXT }}>
				Discount cost, payment recovery, and net-margin proxy
			</h2>
			<p className="text-sm mb-3" style={{ color: MUTED }}>
				This dataset has no per-product cost-of-goods data, so there's no true
				gross margin to compute. "Net margin proxy" = gross revenue minus
				discounts given minus successful refunds, as a % of gross — it
				tracks revenue erosion, not true profitability.
			</p>
			<div className="grid grid-cols-2 gap-8 mb-4">
				<div>
					{recovery.isLoading ? (
						<div className="h-10 w-24 bg-gray-200 animate-pulse rounded" />
					) : (
						<p className="text-3xl font-bold" style={{ color: TEXT }}>
							{rec ? pct(rec.recovery_rate_pct) : '—'}
						</p>
					)}
					<p className="text-sm mt-1" style={{ color: MUTED }}>
						Failed-payment recovery rate ({rec ? N(rec.orders_with_failed_payment) : 0} orders had a
						failed attempt). This dataset only ships orders that eventually
						succeeded, so 100% here is a data-integrity check, not a
						leaky-bucket signal.
					</p>
				</div>
			</div>
			{trend.isLoading ? (
				<ChartSkeleton height={200} />
			) : trend.isError ? (
				<ErrorNote error={trend.error} />
			) : (
				<>
					<p className="text-sm font-medium mb-1" style={{ color: TEXT }}>
						Discount code cost by month
					</p>
					<ResponsiveContainer width="100%" height={180}>
						<BarChart data={chartData}>
							<CartesianGrid strokeDasharray="3 3" stroke="#eee" />
							<XAxis dataKey="month" fontSize={11} interval={2} />
							<YAxis tickFormatter={(v) => usd(v)} fontSize={11} width={44} />
							<Tooltip formatter={(v: number) => usdFull(N(v))} />
							<Bar dataKey="discount_given" name="Discount given" fill={PALETTE[1]} />
						</BarChart>
					</ResponsiveContainer>

					<p className="text-sm font-medium mb-1 mt-4" style={{ color: TEXT }}>
						Net-margin proxy by month
					</p>
					<ResponsiveContainer width="100%" height={180}>
						<LineChart data={chartData}>
							<CartesianGrid strokeDasharray="3 3" stroke="#eee" />
							<XAxis dataKey="month" fontSize={11} interval={2} />
							<YAxis tickFormatter={(v) => `${v}%`} fontSize={11} width={36} domain={[80, 100]} />
							<Tooltip formatter={(v: number) => pct(v)} />
							<Line
								type="linear"
								dataKey="net_margin_proxy_pct"
								name="Net margin proxy"
								stroke={PALETTE[2]}
								strokeWidth={2}
								dot={false}
								connectNulls
							/>
						</LineChart>
					</ResponsiveContainer>
				</>
			)}
		</section>
	);
}

function CfoTab() {
	return (
		<div>
			<CohortCacLtvSection />
			<MarginDiscountSection />
		</div>
	);
}

// ===========================================================================
// PERFORMANCE MARKETING TAB
// ===========================================================================

// PMM story 1: campaign-level spend + platform-reported efficiency (not just partner-level)
function CampaignPerformanceSection() {
	const q = useSQLQuery(`
    WITH campaign_perf AS (
        SELECT 'meta' AS platform, mc.name AS campaign_name, mi.date,
            mi.spend AS spend_usd, mi.impressions, mi.clicks,
            COALESCE(ma.purchases, 0) AS platform_conversions
        FROM "kinetic"."main"."meta_ad_insights_daily" mi
        JOIN "kinetic"."main"."meta_campaigns" mc ON mc.campaign_id = mi.campaign_id
        LEFT JOIN (
            SELECT campaign_id, date, SUM(value) AS purchases
            FROM "kinetic"."main"."meta_ad_actions_daily" WHERE action_type = 'purchase' GROUP BY 1, 2
        ) ma ON ma.campaign_id = mi.campaign_id AND ma.date = mi.date

        UNION ALL
        SELECT 'google_search', gc.name, gp.date, gp.cost_micros / 1000000.0, gp.impressions, gp.clicks, gp.conversions
        FROM "kinetic"."main"."google_search_performance_daily" gp
        JOIN "kinetic"."main"."google_search_campaigns" gc ON gc.campaign_id = gp.campaign_id

        UNION ALL
        SELECT 'youtube', yc.name, yp.date, yp.cost_micros / 1000000.0, yp.impressions, yp.clicks, yp.conversions
        FROM "kinetic"."main"."youtube_performance_daily" yp
        JOIN "kinetic"."main"."youtube_campaigns" yc ON yc.campaign_id = yp.campaign_id

        UNION ALL
        SELECT 'dv360', dio.name, dp.date, dp.cost_micros / 1000000.0, dp.impressions, dp.clicks, dp.conversions
        FROM "kinetic"."main"."dv360_performance_daily" dp
        JOIN "kinetic"."main"."dv360_insertion_orders" dio ON dio.insertion_order_id = dp.insertion_order_id

        UNION ALL
        SELECT 'snap', sc.name, sp.date, sp.spend_micro / 1000000.0, sp.impressions, sp.swipes, sp.conversions
        FROM "kinetic"."main"."snap_stats_daily" sp
        JOIN "kinetic"."main"."snap_campaigns" sc ON sc.campaign_id = sp.campaign_id

        UNION ALL
        SELECT 'tiktok', tc.campaign_name, tp.date, tp.spend_micro / 1000000.0, tp.impressions, tp.clicks, tp.conversions
        FROM "kinetic"."main"."tiktok_reports_daily" tp
        JOIN "kinetic"."main"."tiktok_campaigns" tc ON tc.campaign_id = tp.campaign_id
    )
    SELECT platform, campaign_name,
        ROUND(SUM(spend_usd), 2) AS total_spend,
        SUM(impressions) AS impressions,
        SUM(clicks) AS clicks,
        ROUND(SUM(platform_conversions), 0) AS platform_conversions,
        ROUND(SUM(spend_usd) / NULLIF(SUM(platform_conversions), 0), 2) AS platform_cac_usd,
        ROUND(100.0 * SUM(clicks) / NULLIF(SUM(impressions), 0), 3) AS ctr_pct
    FROM campaign_perf
    GROUP BY 1, 2
    ORDER BY platform_cac_usd DESC NULLS FIRST
  `);

	const rows = Array.isArray(q.data) ? q.data : [];

	return (
		<section className="mb-8">
			<h2 className="text-lg font-semibold" style={{ color: TEXT }}>
				Campaign-level spend &amp; platform-reported efficiency
			</h2>
			<p className="text-sm mb-3" style={{ color: MUTED }}>
				All 38 real campaigns across all 6 platforms, day-level spend rolled
				up to totals — sorted worst-CAC-first so an underperformer surfaces
				immediately. "Platform CAC" uses each ad platform's own
				self-reported conversions (Meta: purchase actions; others: their
				native conversions field) — this dataset has no join key tying an
				individual ad-platform campaign to a specific site session, so it
				will differ from the site-analytics-attributed revenue on the
				Overview tab, same as in the real world.
			</p>
			{q.isLoading ? (
				<TableSkeleton />
			) : q.isError ? (
				<ErrorNote error={q.error} />
			) : (
				<div className="overflow-y-auto" style={{ maxHeight: 320 }}>
					<table className="w-full text-sm">
						<thead>
							<tr style={{ color: MUTED }}>
								<th className="text-left py-1 font-medium">Platform</th>
								<th className="text-left py-1 font-medium">Campaign</th>
								<th className="text-right py-1 font-medium">Spend</th>
								<th className="text-right py-1 font-medium">CTR</th>
								<th className="text-right py-1 font-medium">Platform conv.</th>
								<th className="text-right py-1 font-medium">Platform CAC</th>
							</tr>
						</thead>
						<tbody>
							{rows.map((r: any) => (
								<tr key={`${r.platform}-${r.campaign_name}`}>
									<td className="py-1" style={{ color: TEXT }}>
										{CHANNEL_LABEL[String(r.platform)] ?? String(r.platform)}
									</td>
									<td className="py-1" style={{ color: TEXT }}>
										{String(r.campaign_name)}
									</td>
									<td className="py-1 text-right" style={{ color: TEXT }}>
										{usd(N(r.total_spend))}
									</td>
									<td className="py-1 text-right" style={{ color: TEXT }}>
										{pct(r.ctr_pct)}
									</td>
									<td className="py-1 text-right" style={{ color: TEXT }}>
										{N(r.platform_conversions).toLocaleString()}
									</td>
									<td
										className="py-1 text-right"
										style={{ color: r.platform_cac_usd == null ? MUTED : TEXT }}
									>
										{r.platform_cac_usd == null ? 'n/a (0 conv.)' : usdFull(N(r.platform_cac_usd))}
									</td>
								</tr>
							))}
						</tbody>
					</table>
				</div>
			)}
		</section>
	);
}

// PMM story 2: CTR / CVR benchmarks by platform and ad format
function FormatCtrCvrSection() {
	const q = useSQLQuery(`
    WITH fmt_perf AS (
        SELECT 'meta' AS platform, 'all_formats' AS ad_format, mi.impressions, mi.clicks, COALESCE(ma.purchases, 0) AS conv
        FROM "kinetic"."main"."meta_ad_insights_daily" mi
        LEFT JOIN (
            SELECT campaign_id, date, SUM(value) AS purchases
            FROM "kinetic"."main"."meta_ad_actions_daily" WHERE action_type = 'purchase' GROUP BY 1, 2
        ) ma ON ma.campaign_id = mi.campaign_id AND ma.date = mi.date

        UNION ALL
        SELECT 'google_search', 'text_search', impressions, clicks, conversions
        FROM "kinetic"."main"."google_search_performance_daily"

        UNION ALL
        SELECT 'youtube', yc.video_ad_format, yp.impressions, yp.clicks, yp.conversions
        FROM "kinetic"."main"."youtube_performance_daily" yp
        JOIN "kinetic"."main"."youtube_campaigns" yc ON yc.campaign_id = yp.campaign_id

        UNION ALL
        SELECT 'dv360', dli.line_item_type, dp.impressions, dp.clicks, dp.conversions
        FROM "kinetic"."main"."dv360_performance_daily" dp
        JOIN "kinetic"."main"."dv360_line_items" dli ON dli.line_item_id = dp.line_item_id

        UNION ALL
        SELECT 'snap', sa.ad_type, sp.impressions, sp.swipes, sp.conversions
        FROM "kinetic"."main"."snap_stats_daily" sp
        JOIN "kinetic"."main"."snap_ads" sa ON sa.ad_id = sp.ad_id

        UNION ALL
        SELECT 'tiktok', ta.ad_format, tp.impressions, tp.clicks, tp.conversions
        FROM "kinetic"."main"."tiktok_reports_daily" tp
        JOIN "kinetic"."main"."tiktok_ads" ta ON ta.ad_id = tp.ad_id
    )
    SELECT platform, ad_format,
        SUM(impressions) AS impressions,
        SUM(clicks) AS clicks,
        ROUND(100.0 * SUM(clicks) / NULLIF(SUM(impressions), 0), 3) AS ctr_pct,
        ROUND(SUM(conv), 0) AS conversions,
        ROUND(100.0 * SUM(conv) / NULLIF(SUM(clicks), 0), 3) AS cvr_pct
    FROM fmt_perf
    GROUP BY 1, 2
    ORDER BY 1, 2
  `);

	const rows = Array.isArray(q.data) ? q.data : [];

	return (
		<section className="mb-4">
			<h2 className="text-lg font-semibold" style={{ color: TEXT }}>
				Click-through &amp; conversion rate by platform and ad format
			</h2>
			<p className="text-sm mb-3" style={{ color: MUTED }}>
				"Swipes" stand in for clicks on Snap. Meta and Google Search don't
				expose a per-ad format field in this dataset, so they're shown as a
				single bucket. CVR uses each platform's own self-reported
				conversions (see note on the campaign table above).
			</p>
			{q.isLoading ? (
				<TableSkeleton />
			) : q.isError ? (
				<ErrorNote error={q.error} />
			) : (
				<table className="w-full text-sm">
					<thead>
						<tr style={{ color: MUTED }}>
							<th className="text-left py-1 font-medium">Platform</th>
							<th className="text-left py-1 font-medium">Format</th>
							<th className="text-right py-1 font-medium">CTR</th>
							<th className="text-right py-1 font-medium">CVR</th>
						</tr>
					</thead>
					<tbody>
						{rows.map((r: any) => (
							<tr key={`${r.platform}-${r.ad_format}`}>
								<td className="py-1" style={{ color: TEXT }}>
									{CHANNEL_LABEL[String(r.platform)] ?? String(r.platform)}
								</td>
								<td className="py-1" style={{ color: TEXT }}>
									{String(r.ad_format)}
								</td>
								<td className="py-1 text-right" style={{ color: TEXT }}>
									{pct(r.ctr_pct)}
								</td>
								<td className="py-1 text-right" style={{ color: TEXT }}>
									{pct(r.cvr_pct)}
								</td>
							</tr>
						))}
					</tbody>
				</table>
			)}
		</section>
	);
}

function PmmTab() {
	return (
		<div>
			<CampaignPerformanceSection />
			<FormatCtrCvrSection />
		</div>
	);
}

// ===========================================================================
// Root — tab navigation
// ===========================================================================

const TABS: { key: string; label: string }[] = [
	{ key: 'overview', label: 'Overview' },
	{ key: 'ceo', label: 'CEO' },
	{ key: 'cmo', label: 'CMO' },
	{ key: 'cfo', label: 'CFO' },
	{ key: 'pmm', label: 'Performance Marketing' },
];

export default function KineticOverviewDive() {
	const [tab, setTab] = useDiveState<string>('tab', 'overview');

	return (
		<div className="p-6" style={{ background: '#f8f8f8' }}>
			<h1 className="text-2xl font-semibold" style={{ color: TEXT }}>
				Kinetic — Marketing &amp; Revenue Overview
			</h1>
			<p className="text-sm mb-4" style={{ color: MUTED }}>
				Aug 2023 – Jul 2026 · the 6 starter queries plus persona-specific
				views for the CEO, CMO, CFO, and Performance Marketing Manager
			</p>

			<div className="flex gap-2 mb-6" style={{ borderBottom: '1px solid #ddd' }}>
				{TABS.map((t) => (
					<button
						key={t.key}
						onClick={() => setTab(t.key)}
						className="text-sm px-3 py-2"
						style={{
							color: tab === t.key ? PALETTE[0] : MUTED,
							fontWeight: tab === t.key ? 600 : 400,
							borderBottom: tab === t.key ? `2px solid ${PALETTE[0]}` : '2px solid transparent',
							background: 'none',
							cursor: 'pointer',
						}}
					>
						{t.label}
					</button>
				))}
			</div>

			{tab === 'overview' && <OverviewTab />}
			{tab === 'ceo' && <CeoTab />}
			{tab === 'cmo' && <CmoTab />}
			{tab === 'cfo' && <CfoTab />}
			{tab === 'pmm' && <PmmTab />}
		</div>
	);
}
