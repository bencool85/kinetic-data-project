"""
Phase 5 - web_events table (2 of 4). Page-level events within each
web_sessions.csv row: page_view / product_view / add_to_cart /
begin_checkout / purchase / search, per schema_reference.md's vocabulary.

The central cross-table guarantee this table has to deliver: EVERY row in
orders.csv gets exactly one `purchase` event, attached to a real session
that (a) belongs to the right anonymous_id/customer_id and (b) actually
falls on the order's own order_date -- reusing web_sessions.csv's own
already-validated "every order has a same-day session" / "every guest
purchaser's last session lands on guest_purchase_date" invariants rather
than re-deciding session timing here.

Two linkage problems had to be solved to make that guarantee real, since
neither orders.csv nor web_sessions.csv carries a direct FK to the other:

1. Known-customer orders: when a customer has more than one order on the
   same calendar day, there's more than one same-day session too (
   build_web_sessions.py creates one session per order), but nothing on
   disk says WHICH session belongs to WHICH order. Resolved by pairing them
   deterministically within each (customer_id, date) group: sessions sorted
   by started_at, orders sorted by order_id, zipped 1:1. Ties are
   interchangeable (same customer, same day) so any valid pairing is
   correct.
2. Guest orders: guest_email in orders.csv is randomly generated at build
   time and carries no link back to the originating ghost's anonymous_id.
   The only shared key is (order_date, subtotal) -- and 276 of the 1,257
   guest purchasers collide on that key with at least one other ghost (131
   collision groups), so a plain merge would silently produce wrong or
   duplicate matches. Resolved the same way as #1: build a queue of
   candidate order_ids per (date, amount) key and pop one per ghost,
   iterating ghosts in `_sim_anonymous_population.csv`'s own row order
   (deterministic, reproducible). Collisions are provably interchangeable
   (identical date + amount), so any pairing within a collision group is
   equally valid.

Every purchase event's product_id is the customer's ACTUAL purchased
product (from order_line_items.csv, single source of truth), not a random
pick -- the whole point of tying this to real orders is that the funnel
resolves to what was really bought.

Non-purchase sessions get a plausible browsing pattern: 1-4 page views,
0-2 product views (uniformly random catalog products -- a simplification;
this table doesn't weight by real popularity), a small chance of a search,
and a small chance of add_to_cart/begin_checkout WITHOUT a completed
purchase (cart abandonment -- consistent with segments.csv's own "Cart
Abandoners" segment vocabulary, seg_016-021, even though those anonymous-
grain segments don't get customer_segment_membership rows).

Output: data/web_events.csv
"""
import datetime
import numpy as np
import pandas as pd

from params import SEED

FUNNEL_STAGES = ["page_view", "product_view", "add_to_cart", "begin_checkout", "purchase"]

SEARCH_QUERIES = [
    "yoga mat", "resistance bands", "hiit workout", "marathon training plan",
    "beginner strength program", "kinetic water bottle", "quarter zip pullover",
    "mobility routine", "spin class", "core workout", "total body transformation",
    "yoga block bundle",
]

BROWSE_PAGE_PATHS = ["/", "/pricing", "/courses", "/shop", "/trial", "/blog", "/about"]
BROWSE_PAGE_WEIGHTS = [0.30, 0.15, 0.15, 0.20, 0.08, 0.07, 0.05]

SESSION_SEARCH_RATE = 0.15
CART_ABANDON_RATE = 0.06          # of non-purchase sessions
ABANDON_REACHES_CHECKOUT_RATE = 0.35  # of abandoners, % that get as far as begin_checkout (not just add_to_cart)


def _spaced_timestamps(rng, started_at, ended_at, n):
    """n monotonically increasing timestamps within [started_at, ended_at],
    evenly spaced with a little jitter, guaranteed strictly increasing.
    Takes the shared seeded rng explicitly -- NOT np.random.default_rng()
    internally, which would draw from an unseeded source and break
    reproducibility."""
    duration = (ended_at - started_at).total_seconds()
    if duration < n:
        # Degenerate case (more stages than seconds available): 1-second
        # increments from the start; every web_sessions.csv row has enough
        # runway in practice (min duration is 30s, max n here is 9), but
        # this keeps the function safe regardless.
        return [started_at + datetime.timedelta(seconds=i) for i in range(1, n + 1)]

    step = duration / (n + 1)
    out = []
    for i in range(1, n + 1):
        jitter = float(rng.uniform(-step * 0.15, step * 0.15))
        # Whole seconds only -- the float offset here previously flowed
        # straight into timedelta(seconds=offset), giving every row a
        # fractional-second timestamp (all 117,706 of them). That was
        # invisible to this table's OWN validator (a single consistent
        # fractional format parses fine on its own) but broke downstream
        # once braze_email_events.py mixed these with its own whole-second
        # timestamps into one column pandas couldn't parse with one format.
        offset = int(round(min(duration, max(i, i * step + jitter))))
        out.append(started_at + datetime.timedelta(seconds=offset))

    # Enforce strict monotonicity forward, then re-clip to ended_at and fix
    # backward if clipping introduced a tie.
    for i in range(1, len(out)):
        if out[i] <= out[i - 1]:
            out[i] = out[i - 1] + datetime.timedelta(seconds=1)
    if out[-1] > ended_at:
        out[-1] = ended_at
        for i in range(len(out) - 2, -1, -1):
            if out[i] >= out[i + 1]:
                out[i] = out[i + 1] - datetime.timedelta(seconds=1)
            else:
                break
    return out


def _build_purchase_session_map(sessions, orders):
    """order_id -> session_id, for every row in orders.csv."""
    mapping = {}

    # --- Known-customer orders ---
    known_orders = orders[orders["customer_id"].notna()].copy()
    known_orders["order_date"] = pd.to_datetime(known_orders["order_date"]).dt.date
    known_sessions = sessions[sessions["customer_id"].notna()].copy()
    known_sessions["date"] = known_sessions["started_at"].dt.date

    session_queues = {}
    for (cid, date), grp in known_sessions.groupby(["customer_id", "date"]):
        session_queues[(cid, date)] = list(grp.sort_values("started_at")["session_id"])

    for (cid, date), grp in known_orders.groupby(["customer_id", "order_date"]):
        queue = session_queues.get((cid, date), [])
        for order_id in sorted(grp["order_id"]):
            if queue:
                mapping[order_id] = queue.pop(0)

    # --- Guest orders ---
    guest_orders = orders[orders["customer_id"].isna()].copy()
    order_id_queues = {}
    for (date, amount), grp in guest_orders.groupby(["order_date", "subtotal"]):
        order_id_queues[(date, round(amount, 2))] = sorted(grp["order_id"])

    anon = pd.read_csv("../internal/_sim_anonymous_population.csv")
    guests = anon[anon["is_guest_purchaser"]]
    ghost_last_session = sessions[sessions["anonymous_id"].isin(guests["anonymous_id"])].sort_values(
        "started_at").groupby("anonymous_id").last()["session_id"]

    for ghost in guests.itertuples():
        key = (ghost.guest_purchase_date, round(ghost.guest_purchase_amount, 2))
        queue = order_id_queues.get(key, [])
        if not queue:
            continue
        order_id = queue.pop(0)
        session_id = ghost_last_session.get(ghost.anonymous_id)
        if session_id is not None:
            mapping[order_id] = session_id

    return mapping


def build_web_events(seed=SEED + 16):
    rng = np.random.default_rng(seed)
    sessions = pd.read_csv("../data/web_sessions.csv")
    sessions["started_at"] = pd.to_datetime(sessions["started_at"])
    sessions["ended_at"] = pd.to_datetime(sessions["ended_at"])
    orders = pd.read_csv("../data/orders.csv")
    line_items = pd.read_csv("../data/order_line_items.csv")
    products = list(pd.read_csv("../data/products.csv")["product_id"])

    order_product = line_items.set_index("order_id")["product_id"]
    purchase_session_of_order = _build_purchase_session_map(sessions, orders)
    order_of_session = {sid: oid for oid, sid in purchase_session_of_order.items()}

    rows = []

    def emit(session, event_type, occurred_at, page_path=None, product_id=None, order_id=None, search_query=None):
        rows.append({
            "session_id": session.session_id,
            "anonymous_id": session.anonymous_id,
            "customer_id": session.customer_id if pd.notna(session.customer_id) else None,
            "event_type": event_type,
            "occurred_at": occurred_at,
            "page_path": page_path,
            "product_id": product_id,
            "order_id": order_id,
            "search_query": search_query,
        })

    for session in sessions.itertuples():
        started_at, ended_at = session.started_at, session.ended_at
        order_id = order_of_session.get(session.session_id)

        if order_id is not None:
            product_id = order_product.get(order_id)
            timestamps = _spaced_timestamps(rng, started_at, ended_at, len(FUNNEL_STAGES))
            for stage, ts in zip(FUNNEL_STAGES, timestamps):
                if stage == "page_view":
                    emit(session, stage, ts, page_path=str(rng.choice(BROWSE_PAGE_PATHS, p=BROWSE_PAGE_WEIGHTS)))
                elif stage in ("product_view", "add_to_cart"):
                    emit(session, stage, ts, page_path=f"/products/{product_id}", product_id=product_id)
                elif stage == "begin_checkout":
                    emit(session, stage, ts, page_path="/checkout", product_id=product_id)
                else:  # purchase
                    emit(session, stage, ts, page_path="/checkout/confirmation",
                         product_id=product_id, order_id=order_id)
            continue

        # Non-purchase session: organic browsing pattern.
        n_page_views = int(rng.integers(1, 5))
        n_product_views = int(rng.integers(0, 3))
        does_search = rng.random() < SESSION_SEARCH_RATE
        is_abandoner = rng.random() < CART_ABANDON_RATE
        reaches_checkout = is_abandoner and (rng.random() < ABANDON_REACHES_CHECKOUT_RATE)

        n_events = n_page_views + n_product_views + int(does_search) + int(is_abandoner) + int(reaches_checkout)
        if n_events == 0:
            n_events = n_page_views = 1  # every session has at least one page view

        timestamps = _spaced_timestamps(rng, started_at, ended_at, n_events)
        ts_iter = iter(timestamps)

        for _ in range(n_page_views):
            emit(session, "page_view", next(ts_iter), page_path=str(rng.choice(BROWSE_PAGE_PATHS, p=BROWSE_PAGE_WEIGHTS)))
        chosen_products = []
        for _ in range(n_product_views):
            pid = str(rng.choice(products))
            chosen_products.append(pid)
            emit(session, "product_view", next(ts_iter), page_path=f"/products/{pid}", product_id=pid)
        if does_search:
            emit(session, "search", next(ts_iter), page_path="/search", search_query=str(rng.choice(SEARCH_QUERIES)))
        if is_abandoner:
            pid = chosen_products[-1] if chosen_products else str(rng.choice(products))
            emit(session, "add_to_cart", next(ts_iter), page_path=f"/products/{pid}", product_id=pid)
            if reaches_checkout:
                emit(session, "begin_checkout", next(ts_iter), page_path="/checkout", product_id=pid)

    df = pd.DataFrame(rows).sort_values("occurred_at").reset_index(drop=True)
    df.insert(0, "event_id", [f"web_evt_{i:07d}" for i in range(1, len(df) + 1)])
    df["occurred_at"] = df["occurred_at"].apply(lambda d: d.isoformat())
    return df


if __name__ == "__main__":
    df = build_web_events()
    df.to_csv("../data/web_events.csv", index=False)
    print(f"Wrote {len(df)} web_events\n")
    print(df["event_type"].value_counts().to_string())
    n_purchases = (df["event_type"] == "purchase").sum()
    n_orders = len(pd.read_csv("../data/orders.csv"))
    print(f"\npurchase events: {n_purchases} vs orders.csv rows: {n_orders}")
