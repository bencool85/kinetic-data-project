"""
Phase 5 - web_sessions table (1 of 4). Marketing-site/storefront browsing
sessions -- NOT in-app fitness usage (that's app_sessions/app_events, later
in this phase). This is the table generation_plan.md's convention #2-4
apply to: anonymous_id always present, customer_id nullable (populated only
once identity_map's resolution point has passed), UTM fields that name the
channel cleanly but only loosely match a real campaign name.

Two populations, both derived from already-simulated ground truth rather
than invented independently:

1. Anonymous ghosts (17,050) -- `_sim_anonymous_population.csv` already
   carries `num_sessions` (1-3, decided back in Phase 0) and `channel` for
   each ghost; this table just has to realize those exact counts as actual
   session rows, single-source-of-truth style, not re-decide how many
   sessions each ghost gets. Guest purchasers' LAST session lands exactly
   on their `guest_purchase_date` (the checkout session) -- everything
   about the purchase itself is already locked in orders.csv/refunds.csv;
   this just guarantees a session exists on that date for `web_events`
   (table 2 of 4) to hang a `purchase` event off of later.
2. Known (non-deleted) customers -- reuses `_last_activity_date()` from
   build_devices.py (single source of truth for "when did this customer's
   story end") and layers in:
   - 1-3 pre-signup sessions (SAME distributional shape as the ghost
     population, since before converting a future customer looks exactly
     like any other anonymous visitor), the LAST of which occurs at the
     exact `created_at` timestamp and is where identity resolves --
     customer_id populates from that session onward (started_at >=
     created_at), never before.
   - one session on every date the timeline's own `reactivations` list
     records a win-back (utm_source = that reactivation's channel).
   - one session on every date this customer has a known-customer order in
     orders.csv (a return visit to buy something).
   - "filler" organic browsing sessions across their active tenure, volume
     driven by `engagement_tier` (power > regular > casual) -- this is the
     Phase 5 usage signal generation_plan.md's cross-phase commitment #2
     requires; app_sessions/app_events (later tables in this phase) must
     size their own per-customer volume off this SAME engagement_tier, not
     invent a separate signal that could drift out of sync with it.

Soft-deleted customers get ZERO rows (same full-erasure treatment as
customer_addresses.csv/devices.csv). Second devices are NOT separately
modeled here (out of scope for this table -- session history is tracked
against each customer's PRIMARY anonymous_id only).

Only the pre-signup/converting session and reactivation sessions carry real
UTM attribution; every return-visit and filler session is organic/direct
(utm fields null) -- realistic web analytics only attributes NEW or
re-marketing-driven traffic, not routine returning-user visits.

Output: data/web_sessions.csv
"""
import datetime
import json
import numpy as np
import pandas as pd

from params import SEED, END_DATE
from build_devices import _last_activity_date
from build_customers import customer_id_for

PRESIGNUP_SESSION_COUNTS = [1, 2, 3]
PRESIGNUP_SESSION_WEIGHTS = [0.703, 0.217, 0.080]  # mirrors the ghost population's own num_sessions shape

WEB_SESSION_RATE_PER_MONTH = {"power": 1.5, "regular": 0.5, "casual": 0.15}  # filler browsing sessions

DEVICE_CATEGORY_WEIGHTS = {"mobile": 0.55, "desktop": 0.40, "tablet": 0.05}

PAID_CHANNELS = {"meta", "google_search", "youtube", "dv360", "snap", "tiktok"}
REACTIVATION_CHANNEL_MAP = {"email": "email", "push": "push", "organic": "organic_direct"}

REFERRER_BY_CHANNEL = {
    "meta": "m.facebook.com", "google_search": "google.com", "youtube": "youtube.com",
    "dv360": "doubleclick.net", "snap": "snapchat.com", "tiktok": "tiktok.com",
    "organic_direct": None, "email": None, "push": None,
}
CAMPAIGN_THEMES_PAID = ["prospecting", "retargeting", "lookalike", "brand_lift", "conversion"]
CAMPAIGN_THEMES_LIFECYCLE = ["winback_promo", "reactivation", "trial_reminder"]

LANDING_PAGES = ["/", "/pricing", "/courses", "/shop", "/trial", "/blog"]
LANDING_PAGE_WEIGHTS = [0.35, 0.20, 0.15, 0.15, 0.10, 0.05]


def _device_category(rng):
    return str(rng.choice(list(DEVICE_CATEGORY_WEIGHTS.keys()), p=list(DEVICE_CATEGORY_WEIGHTS.values())))


def _utm_for_channel(rng, channel):
    """channel is a raw acquisition/reactivation channel name (already mapped
    to the standard vocabulary, e.g. "organic_direct" not "organic")."""
    if channel == "organic_direct":
        return None, None, None
    medium = "paid" if channel in PAID_CHANNELS else channel  # email -> "email", push -> "push"
    themes = CAMPAIGN_THEMES_PAID if channel in PAID_CHANNELS else CAMPAIGN_THEMES_LIFECYCLE
    theme = str(rng.choice(themes))
    campaign = f"{channel}_{theme}"
    return channel, medium, campaign


def _session_duration(rng):
    # Whole seconds only -- keeps timestamp formatting consistent with the
    # rest of the project (no fractional-second isoformat() output, which
    # would otherwise produce a mixed-precision column pandas can't parse
    # with a single format string).
    seconds = int(round(float(np.clip(rng.gamma(shape=2.0, scale=3.0), 0.5, 45.0)) * 60))
    return datetime.timedelta(seconds=seconds)


def _landing_page(rng):
    return str(rng.choice(LANDING_PAGES, p=LANDING_PAGE_WEIGHTS))


def build_web_sessions(seed=SEED + 15):
    rng = np.random.default_rng(seed)
    customers = pd.read_csv("../data/customers.csv")
    orders = pd.read_csv("../data/orders.csv")
    anon = pd.read_csv("../internal/_sim_anonymous_population.csv")
    timeline = json.load(open("../internal/_sim_customer_timeline.json"))

    customers_by_id = customers.set_index("customer_id")
    known_orders_by_customer = {
        cid: g for cid, g in orders[orders["customer_id"].notna()].groupby("customer_id")
    }

    sessions = []  # list of dicts, pre-session_id-assignment

    def add_session(anonymous_id, customer_id, started_at, device_category, channel):
        utm_source, utm_medium, utm_campaign = _utm_for_channel(rng, channel) if channel else (None, None, None)
        sessions.append({
            "anonymous_id": anonymous_id,
            "customer_id": customer_id,
            "started_at": started_at,
            "ended_at": started_at + _session_duration(rng),
            "device_category": device_category,
            "utm_source": utm_source,
            "utm_medium": utm_medium,
            "utm_campaign": utm_campaign,
            "landing_page": _landing_page(rng),
            "referrer_domain": REFERRER_BY_CHANNEL.get(channel) if channel else None,
        })

    # --- Population 1: known, non-deleted customers ---
    for t in timeline:
        cid = customer_id_for(t["customer_id"])
        if cid not in customers_by_id.index or bool(customers_by_id.loc[cid, "is_deleted"]):
            continue

        anonymous_id = t["pre_signup_anonymous_id"]
        device_category = _device_category(rng)
        signup_dt = datetime.datetime.fromisoformat(customers_by_id.loc[cid, "created_at"])
        first_seen_dt = datetime.datetime.combine(
            datetime.date.fromisoformat(t["pre_signup_first_seen"]), datetime.time())
        signup_source = t["signup_source"]

        # Pre-signup sessions (1-3, same shape as the ghost population), last one = signup itself.
        n_pre = int(rng.choice(PRESIGNUP_SESSION_COUNTS, p=PRESIGNUP_SESSION_WEIGHTS))
        if n_pre == 1:
            pre_dts = [signup_dt]
        else:
            span_seconds = max(1, int((signup_dt - first_seen_dt).total_seconds()))
            earlier = sorted(
                first_seen_dt + datetime.timedelta(seconds=int(rng.integers(0, span_seconds)))
                for _ in range(n_pre - 1)
            )
            pre_dts = earlier + [signup_dt]
        for dt in pre_dts:
            add_session(anonymous_id, None, dt, device_category, signup_source)

        # customer_id populates from the signup moment onward -- fix up the last (signup) session.
        sessions[-1]["customer_id"] = cid

        # Reactivation-day sessions.
        for react in t["reactivations"]:
            react_dt = datetime.datetime.combine(
                datetime.date.fromisoformat(react["reactivated_at"]),
                datetime.time(int(rng.integers(7, 22)), int(rng.integers(0, 60))))
            channel = REACTIVATION_CHANNEL_MAP[react["channel"]]
            add_session(anonymous_id, cid, react_dt, device_category, channel)

        # Order-day sessions (known-customer orders only).
        for order in known_orders_by_customer.get(cid, pd.DataFrame()).itertuples():
            order_dt = datetime.datetime.combine(
                datetime.date.fromisoformat(order.order_date),
                datetime.time(int(rng.integers(7, 22)), int(rng.integers(0, 60))))
            add_session(anonymous_id, cid, order_dt, device_category, "organic_direct")

        # Filler organic browsing sessions across active tenure.
        last_activity = _last_activity_date(t)
        active_months = max(0.0, (last_activity - signup_dt.date()).days / 30.44)
        rate = WEB_SESSION_RATE_PER_MONTH[t["engagement_tier"]]
        n_filler = int(rng.poisson(rate * active_months))
        span_days = max(1, (last_activity - signup_dt.date()).days)
        for _ in range(n_filler):
            offset_days = int(rng.integers(0, span_days + 1))
            filler_dt = datetime.datetime.combine(
                signup_dt.date() + datetime.timedelta(days=offset_days),
                datetime.time(int(rng.integers(7, 23)), int(rng.integers(0, 60))))
            if filler_dt.date() > END_DATE:
                continue
            add_session(anonymous_id, cid, filler_dt, device_category, "organic_direct")

    # --- Population 2: anonymous ghosts ---
    for ghost in anon.itertuples():
        device_category = _device_category(rng)
        first_seen = datetime.date.fromisoformat(ghost.first_seen_date)
        n_sessions = int(ghost.num_sessions)

        if ghost.is_guest_purchaser:
            purchase_date = datetime.date.fromisoformat(ghost.guest_purchase_date)
            if n_sessions == 1:
                # Their one and only session must BE the purchase session,
                # not first_seen -- those differ whenever the gap > 0.
                offsets = [(purchase_date - first_seen).days]
            else:
                span = (purchase_date - first_seen).days
                # Earlier sessions land on distinct days strictly before the purchase day where
                # possible; if the gap is too tight (span < n_sessions-1) some earlier sessions
                # double up on the same day rather than crash -- still distinguished by time-of-day.
                n_earlier = min(n_sessions - 1, span) if span > 0 else 0
                earlier = sorted(rng.choice(range(0, span), size=n_earlier, replace=False)) if n_earlier > 0 else []
                earlier = earlier + [earlier[-1] if earlier else 0] * (n_sessions - 1 - len(earlier))
                offsets = earlier + [span]
            base_date = first_seen
        else:
            max_span = min(14, (END_DATE - first_seen).days)
            max_span = max(0, max_span)
            n_offsets = min(n_sessions, max_span + 1)
            offsets = sorted(rng.choice(range(0, max_span + 1), size=n_offsets, replace=False)) if max_span > 0 else [0] * n_sessions
            if len(offsets) < n_sessions:
                offsets = offsets + [offsets[-1]] * (n_sessions - len(offsets))
            base_date = first_seen

        for offset in offsets:
            session_date = base_date + datetime.timedelta(days=int(offset))
            session_dt = datetime.datetime.combine(
                session_date, datetime.time(int(rng.integers(7, 23)), int(rng.integers(0, 60))))
            add_session(ghost.anonymous_id, None, session_dt, device_category, ghost.channel)

    # --- Global chronological session_id assignment (same convention as orders.csv) ---
    df = pd.DataFrame(sessions).sort_values("started_at").reset_index(drop=True)
    df.insert(0, "session_id", [f"web_sess_{i:07d}" for i in range(1, len(df) + 1)])
    df["started_at"] = df["started_at"].apply(lambda d: d.isoformat())
    df["ended_at"] = df["ended_at"].apply(lambda d: d.isoformat())
    return df


if __name__ == "__main__":
    df = build_web_sessions()
    df.to_csv("../data/web_sessions.csv", index=False)
    print(f"Wrote {len(df)} web_sessions\n")
    print(f"With customer_id: {df['customer_id'].notna().sum()}, anonymous-only: {df['customer_id'].isna().sum()}")
    print(f"Unique anonymous_ids: {df['anonymous_id'].nunique()}")
    print(df["utm_source"].value_counts(dropna=False).to_string())
