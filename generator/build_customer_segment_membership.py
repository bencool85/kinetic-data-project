"""
Phase 4 - customer_segment_membership table. Effective-dated (entered_at /
exited_at) membership rows for the 9 CUSTOMER-grain segments in segments.csv
(seg_001-seg_009). Anonymous-device segments (seg_010-seg_027) never get
rows here, per schema_reference.md.

Membership is entirely DERIVED from real, already-shipped behavioral data
(subscriptions.csv, orders.csv, invoices.csv, customers.csv) -- nothing is
invented independently. Soft-deleted customers (is_deleted=True) get ZERO
rows, matching the same full-erasure treatment already applied to
customer_addresses.csv and devices.csv (this is a marketing/segmentation
table, not a transactional record that needs to be preserved for referential
integrity).

seg_009 ("High Churn Risk") is EXPLICITLY SKIPPED -- segments.csv's own
description says its engagement half depends on Phase 5 (real usage-event
recency/frequency), which doesn't exist yet. Computing it now would mean
inventing the engagement signal, which is exactly the kind of
independently-invented-data this project's whole design avoids. It gets
built once Phase 5 ships.

One subtlety worth calling out: seg_002/003/004 ("Lapsed N Days") and
seg_008 ("Lapsed - Still Buying") are computed against ANY canceled
subscription OBJECT, not just real (converted) intervals. Stripe sets
canceled_at on a trial that's canceled or simply expires too, exactly the
same as a real interval that's canceled -- and segments.csv's own wording
("Subscription canceled within the last 30 days") doesn't restrict itself
to paid intervals. So a customer whose trial expired without ever
converting still enters the lapsed-tier ladder at their trial's
cancellation date, same as a customer whose real paid interval ended --
they just never pass through seg_001 (Active Subscriber) first, since that
segment is reserved for real/paying intervals only.

Design for each segment:
- seg_001 Active Subscriber: one row per REAL (converted-trial or resub)
  interval. entered_at = start_date, exited_at = canceled_at (null if still
  open, including past_due -- past_due hasn't been canceled yet).
- seg_002/003/004 Lapsed N Days: for each canceled subscription object
  (real or trial-only), a 0-30 / 31-90 / 90+ day ladder starting at
  canceled_at. Each tier's exit is the EARLIEST of (a) its natural day
  boundary or (b) the customer's next subscription object starting (they've
  re-engaged, no longer lapsed). A tier is only emitted if it has actually
  STARTED by END_DATE; a tier still open as of END_DATE gets exited_at=null
  and no later tier is emitted (this is a point-in-time snapshot table, not
  a log of future-scheduled transitions).
- seg_005 Course/Merch-Only (Never Subscribed): only for customers with a
  real gap between signup (customers.created_at) and their first-ever
  subscription object (trial or resub) -- includes both customers who never
  have ANY subscription row at all (permanent membership, exited_at=null)
  and the merch-to-sub email pathway's customers (temporary membership,
  exited_at = their first trial_start). Customers whose very first behavior
  IS starting a trial (signup date == trial_start date -- the overwhelming
  majority) never get a row here at all: they were never actually in this
  state for a non-zero duration.
- seg_006 Trial In Progress: subscriptions.csv rows with status=='trialing'
  (unresolved as of END_DATE). entered_at = trial_start, exited_at = null.
- seg_007 High-LTV Customer: lifetime revenue (order total_amount + paid
  invoice amount_due) in the top decile across the same non-deleted
  customer population that's eligible for rows in this table. entered_at =
  the first date each qualifying customer's own running cumulative revenue
  (in chronological order of their own orders/invoices) reaches the
  decile threshold; exited_at = null (once qualified, treated as a stable
  classification going forward, same simplifying assumption Stripe-shaped
  "current status" segments elsewhere in this table make).
- seg_008 Lapsed - Still Buying: for each canceled subscription object,
  checks for a course/merch order (known customer_id only, never guest)
  landing strictly after canceled_at and strictly before the next
  subscription object (if any). entered_at = that first qualifying order's
  order_date; exited_at = the next subscription object's start (if any,
  else null).

Output: data/customer_segment_membership.csv
"""
import pandas as pd

from params import END_DATE

TIER_BOUNDARIES = [(0, 30, "seg_002"), (30, 90, "seg_003"), (90, None, "seg_004")]
END_TS = pd.Timestamp(END_DATE)


def _is_real(row):
    return pd.isna(row["trial_start"]) or row["start_date"] != row["trial_start"]


def build_customer_segment_membership():
    customers = pd.read_csv("../data/customers.csv")
    subs = pd.read_csv("../data/subscriptions.csv")
    orders = pd.read_csv("../data/orders.csv")
    invoices = pd.read_csv("../data/invoices.csv")

    customers = customers[~customers["is_deleted"]].copy()
    eligible_ids = set(customers["customer_id"])

    subs = subs[subs["customer_id"].isin(eligible_ids)].copy()
    orders_known = orders[orders["customer_id"].notna() & orders["customer_id"].isin(eligible_ids)].copy()
    invoices = invoices[invoices["customer_id"].isin(eligible_ids)].copy()

    subs["first_date"] = pd.to_datetime(subs["trial_start"].fillna(subs["start_date"]))
    subs["is_real"] = subs.apply(_is_real, axis=1)
    subs = subs.sort_values(["customer_id", "first_date"]).reset_index(drop=True)

    orders_known["order_date"] = pd.to_datetime(orders_known["order_date"])
    orders_by_customer = {cid: g for cid, g in orders_known.groupby("customer_id")}

    rows = []
    membership_num = 0

    def emit(customer_id, segment_id, entered_at, exited_at):
        nonlocal membership_num
        membership_num += 1
        rows.append({
            "membership_id": f"csm_{membership_num:06d}",
            "customer_id": customer_id,
            "segment_id": segment_id,
            "entered_at": pd.Timestamp(entered_at).isoformat(),
            "exited_at": pd.Timestamp(exited_at).isoformat() if exited_at is not None else None,
            "created_at": pd.Timestamp(entered_at).isoformat(),
        })

    # --- seg_001 / seg_002 / seg_003 / seg_004 / seg_005 / seg_006 / seg_008 ---
    signup_by_customer = pd.to_datetime(customers.set_index("customer_id")["created_at"])

    # Customers with ZERO subscription rows ever: permanent seg_005 membership.
    # (These never appear in subs.groupby() below at all, so they need to be
    # handled separately from the merch-to-sub-email customers who DO have a
    # subscription row, just a later one.)
    never_subscribed_ids = eligible_ids - set(subs["customer_id"])
    for cid in never_subscribed_ids:
        emit(cid, "seg_005", signup_by_customer[cid], None)

    for cid, grp in subs.groupby("customer_id"):
        grp = grp.reset_index(drop=True)
        signup_date = signup_by_customer[cid]
        first_obj_date = grp.loc[0, "first_date"]
        if first_obj_date > signup_date:
            emit(cid, "seg_005", signup_date, first_obj_date)

        for i, row in grp.iterrows():
            next_obj_date = grp.loc[i + 1, "first_date"] if i + 1 < len(grp) else None

            if row["status"] == "trialing":
                emit(cid, "seg_006", row["first_date"], None)
                continue

            canceled = pd.to_datetime(row["canceled_at"]) if pd.notna(row["canceled_at"]) else None

            if row["is_real"]:
                start = pd.to_datetime(row["start_date"])
                emit(cid, "seg_001", start, canceled)

            if canceled is None:
                continue

            # Lapsed-tier ladder (applies to any canceled object, real or trial-only)
            for lo, hi, seg in TIER_BOUNDARIES:
                entered = canceled + pd.Timedelta(days=lo)
                if entered > END_TS:
                    break
                natural_end = canceled + pd.Timedelta(days=hi) if hi is not None else None
                candidates = [d for d in [natural_end, next_obj_date] if d is not None]
                effective_end = min(candidates) if candidates else None
                if effective_end is not None and effective_end <= entered:
                    break  # already re-engaged before this tier would meaningfully start
                exited = effective_end if (effective_end is not None and effective_end <= END_TS) else None
                emit(cid, seg, entered, exited)
                if exited is None:
                    break
                if exited == next_obj_date:
                    break

            # seg_008 Lapsed - Still Buying
            cust_orders = orders_by_customer.get(cid)
            if cust_orders is not None:
                mask = cust_orders["order_date"] > canceled
                if next_obj_date is not None:
                    mask &= cust_orders["order_date"] < next_obj_date
                qualifying = cust_orders.loc[mask]
                if len(qualifying) > 0:
                    first_qualifying_date = qualifying["order_date"].min()
                    emit(cid, "seg_008", first_qualifying_date, next_obj_date)

    # --- seg_007 High-LTV Customer ---
    order_rev = orders_known[["customer_id", "order_date", "total_amount"]].rename(
        columns={"order_date": "date", "total_amount": "amount"})
    paid_inv = invoices[invoices["status"] == "paid"].copy()
    paid_inv["paid_at"] = pd.to_datetime(paid_inv["paid_at"])
    inv_rev = paid_inv[["customer_id", "paid_at", "amount_due"]].rename(
        columns={"paid_at": "date", "amount_due": "amount"})
    revenue_events = pd.concat([order_rev, inv_rev], ignore_index=True)
    revenue_events["date"] = pd.to_datetime(revenue_events["date"])

    totals = revenue_events.groupby("customer_id")["amount"].sum()
    totals = totals.reindex(customers["customer_id"], fill_value=0.0)
    threshold = totals.quantile(0.90)
    top_decile_ids = totals[(totals >= threshold) & (totals > 0)].index

    for cid in top_decile_ids:
        cust_events = revenue_events[revenue_events["customer_id"] == cid].sort_values("date")
        cumsum = cust_events["amount"].cumsum()
        qualifying_idx = cumsum[cumsum >= threshold].index[0]
        entered_at = cust_events.loc[qualifying_idx, "date"]
        emit(cid, "seg_007", entered_at, None)

    df = pd.DataFrame(rows).sort_values(["customer_id", "entered_at"]).reset_index(drop=True)
    df["membership_id"] = [f"csm_{i:06d}" for i in range(1, len(df) + 1)]
    return df


if __name__ == "__main__":
    df = build_customer_segment_membership()
    df.to_csv("../data/customer_segment_membership.csv", index=False)
    print(f"Wrote {len(df)} customer_segment_membership rows\n")
    print(df["segment_id"].value_counts().sort_index().to_string())
    print(f"\nCustomers with >=1 membership row: {df['customer_id'].nunique()}")
    print(f"Rows still open (exited_at null): {df['exited_at'].isna().sum()}")
