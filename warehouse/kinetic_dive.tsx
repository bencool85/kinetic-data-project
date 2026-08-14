import { useSQLQuery } from '@motherduck/react-sql-query';
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

const N = (v: unknown): number => (v == null ? 0 : Number(v));
const usd = (v: number) =>
	Math.abs(v) >= 1000000
		? `$${(v / 1000000).toFixed(1)}M`
		: Math.abs(v) >= 1000
			? `$${(v / 1000).toFixed(1)}K`
			: `$${Math.round(v)}`;
const usdFull = (v: number) => `$${Math.round(v).toLocaleString()}`;

function ChartSkeleton({ height = 240 }: { height?: number }) {
	return (
		<div
			className="animate-pulse rounded bg-gray-100"
			style={{ height }}
		/>
	);
}

function ErrorNote({ error }: { error: unknown }) {
	return (
		<p className="text-sm" role="alert" style={{ color: '#bc1200' }}>
			{String(error)}
		</p>
	);
}

// ---------------------------------------------------------------------------
// Section 1: Monthly paid media spend by partner
// ---------------------------------------------------------------------------
const PARTNERS = ['meta', 'google_search', 'tiktok', 'youtube', 'dv360', 'snap'];
const PARTNER_LABEL: Record<string, string> = {
	meta: 'Meta',
	google_search: 'Google Search',
	tiktok: 'TikTok',
	youtube: 'YouTube',
	dv360: 'DV360',
	snap: 'Snap',
};

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
								name={PARTNER_LABEL[p]}
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

// ---------------------------------------------------------------------------
// Section 2: Directly attributed revenue by paid vs. owned channel
// ---------------------------------------------------------------------------
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

// ---------------------------------------------------------------------------
// Section 3: Active subscribers by month
// ---------------------------------------------------------------------------
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

// ---------------------------------------------------------------------------
// Section 4: Non-subscription (storefront) revenue by month
// ---------------------------------------------------------------------------
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

// ---------------------------------------------------------------------------
// Section 5: Monthly churn rate
// ---------------------------------------------------------------------------
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

// ---------------------------------------------------------------------------
// Section 6: Top 5 grossing products per year (table — fewer than 8 categories)
// ---------------------------------------------------------------------------
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
				<div className="animate-pulse space-y-2">
					<div className="h-4 w-3/4 rounded bg-gray-200" />
					<div className="h-4 w-1/2 rounded bg-gray-200" />
					<div className="h-4 w-2/3 rounded bg-gray-200" />
				</div>
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

// ---------------------------------------------------------------------------
// Top-level KPI row
// ---------------------------------------------------------------------------
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

// ---------------------------------------------------------------------------
// Root
// ---------------------------------------------------------------------------
export default function KineticOverviewDive() {
	return (
		<div className="p-6" style={{ background: '#f8f8f8' }}>
			<h1 className="text-2xl font-semibold" style={{ color: TEXT }}>
				Kinetic — Marketing &amp; Revenue Overview
			</h1>
			<p className="text-sm mb-8" style={{ color: MUTED }}>
				Aug 2023 – Jul 2026 · all 6 starter analysis queries in one dashboard
			</p>

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
