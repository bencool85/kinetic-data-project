"""
Validation for `invoices` (Phase 2, table 3 of 3 -- completes Phase 2)
-- pandas-based, same 5-layer approach (see validate_products.py's docstring
for why pandas instead of DuckDB).

Central cross-checks: paid-invoice count reconciles exactly against
subscription_events.csv's own (deduped) renewed-event count plus one initial
invoice per paid subscription object; every invoice's amount_due matches
subscription_plans.csv's price for its own plan_id (not the subscription's
FINAL plan_id, since ~32 subscriptions have a mid-life tier change and must
bill the pre-change price before it and the post-change price after);
uncollectible/open invoices only exist where a real precondition holds
(involuntary churn landing exactly on a renewal boundary; currently past_due).
"""
import datetime
import json
import pandas as pd

import build_subscriptions as bs

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    invoices = pd.read_csv("../data/invoices.csv")
    subs = pd.read_csv("../data/subscriptions.csv")
    plans = pd.read_csv("../data/subscription_plans.csv")
    events = pd.read_csv("../data/subscription_events.csv")
    timeline = json.load(open("../internal/_sim_customer_timeline.json"))
    objects = bs.build_subscription_objects(timeline)

    invoices["period_start"] = pd.to_datetime(invoices["period_start"])
    invoices["period_end"] = pd.to_datetime(invoices["period_end"])
    invoices["paid_at"] = pd.to_datetime(invoices["paid_at"])

    # --- 1. Structural ---
    check("Structural", "invoice_id non-null and unique",
          invoices["invoice_id"].notna().all() and invoices["invoice_id"].is_unique)
    check("Structural", "subscription_id and customer_id non-null on every row",
          invoices["subscription_id"].notna().all() and invoices["customer_id"].notna().all())
    check("Structural", "plan_id non-null and every value exists in subscription_plans",
          invoices["plan_id"].notna().all() and invoices["plan_id"].isin(plans["plan_id"]).all())
    check("Structural", "status in {paid, open, uncollectible, void}",
          invoices["status"].isin(["paid", "open", "uncollectible", "void"]).all())
    check("Structural", "currency is always 'usd'", (invoices["currency"] == "usd").all())
    check("Structural", "amount_due > 0 on every invoice", (invoices["amount_due"] > 0).all())
    check("Structural", "period_start < period_end on every invoice",
          (invoices["period_start"] < invoices["period_end"]).all())
    check("Structural", "paid_at populated if and only if status == 'paid'",
          (invoices["status"].eq("paid") == invoices["paid_at"].notna()).all())
    check("Structural", "'void' status is a valid enum value but intentionally has 0 rows (not modeled -- flagged, not silently omitted)",
          (invoices["status"] == "void").sum() == 0)

    # --- 2. Referential integrity ---
    check("Referential", "every invoices.subscription_id exists in subscriptions.csv",
          invoices["subscription_id"].isin(subs["subscription_id"]).all())
    joined = invoices.merge(subs[["subscription_id", "customer_id"]], on="subscription_id", suffixes=("", "_sub"))
    check("Referential", "every invoice's customer_id matches the customer_id on its own subscription_id",
          (joined["customer_id"] == joined["customer_id_sub"]).all())

    never_converted_sub_ids = {o["subscription_id"] for o in objects if o["interval_id"] == 0}
    check("Referential", "no invoice exists for a trial-only subscription that never converted "
                        "(interval_id==0 in the subscription objects -- nothing was ever charged)",
          not invoices["subscription_id"].isin(never_converted_sub_ids).any())

    # --- 3. Temporal ordering ---
    price_check = invoices.merge(plans[["plan_id", "price"]], on="plan_id")

    first_invoice = invoices.sort_values("period_start").drop_duplicates(subset="subscription_id", keep="first")
    obj_by_sub = {o["subscription_id"]: o for o in objects}
    mismatches = 0
    for row in first_invoice.itertuples():
        obj = obj_by_sub[row.subscription_id]
        origin = obj["trial_end"] if obj["interval_id"] == 1 else obj["start_date"]
        if row.period_start.date() != origin:
            mismatches += 1
    check("Temporal", "every subscription's very first invoice starts exactly at its origin "
                      "(trial_end for a converted trial, start_date for a resubscribe)",
          mismatches == 0, f"{mismatches} mismatches out of {len(first_invoice)} subscriptions with invoices")

    # No overlaps/gaps: within each subscription, sorted invoices' periods must
    # be contiguous (each period_start == previous period_end).
    contiguity_breaks = 0
    for sub_id, g in invoices.sort_values("period_start").groupby("subscription_id"):
        ends = g["period_end"].tolist()
        starts = g["period_start"].tolist()
        for i in range(1, len(starts)):
            if starts[i] != ends[i - 1]:
                contiguity_breaks += 1
    check("Temporal", "within each subscription, consecutive invoice periods are perfectly contiguous "
                      "(no gaps, no overlaps)",
          contiguity_breaks == 0, f"{contiguity_breaks} breaks found")

    check("Temporal", "no invoice's period_start falls after END_DATE (no invoices invented for the future)",
          (invoices["period_start"] <= pd.Timestamp(datetime.date(2026, 7, 30))).all())

    # --- 4. Business-rule invariants ---
    events_dedup = events.drop_duplicates(subset=["subscription_id", "event_type", "event_at"])
    renewed_count = (events_dedup["event_type"] == "renewed").sum()
    n_paid_objects = sum(1 for o in objects if o["interval_id"] >= 1)
    expected_paid = n_paid_objects + renewed_count
    actual_paid = (invoices["status"] == "paid").sum()
    check("Business rule", "count of 'paid' invoices exactly equals (1 initial invoice per paid subscription "
                          "object) + (subscription_events.csv's own deduped 'renewed' event count)",
          actual_paid == expected_paid, f"{actual_paid} paid invoices vs. {n_paid_objects} objects + {renewed_count} renewals = {expected_paid}")

    amount_mismatches = (price_check["amount_due"] != price_check["price"]).sum()
    check("Business rule", "every invoice's amount_due matches subscription_plans.csv's price for its OWN "
                          "plan_id exactly (not just the subscription's final plan_id)",
          amount_mismatches == 0, f"{amount_mismatches} mismatches out of {len(invoices)} invoices")

    # For the 32 subscriptions with a tier change, confirm pre-change and
    # post-change invoices actually bill DIFFERENT amounts (not silently
    # using the same price throughout, which would defeat the whole point).
    changed_events = events_dedup[events_dedup["event_type"].isin(["upgraded", "downgraded"])]
    tier_change_verified = 0
    tier_change_checked = 0
    for row in changed_events.itertuples():
        sub_invoices = invoices[invoices["subscription_id"] == row.subscription_id]
        before = sub_invoices[sub_invoices["period_start"] < pd.Timestamp(row.event_at).normalize()]
        after = sub_invoices[sub_invoices["period_start"] >= pd.Timestamp(row.event_at).normalize()]
        tier_change_checked += 1
        if len(before) and len(after) and before["plan_id"].iloc[0] != after["plan_id"].iloc[0]:
            tier_change_verified += 1
        elif len(before) == 0 or len(after) == 0:
            tier_change_verified += 1  # change happened before the first invoice or after the last -- nothing to contradict
    check("Business rule", "for every subscription with a mid-life tier change, invoices before vs. after "
                          "the change date actually bill different plan_ids (price genuinely changes, not silently ignored)",
          tier_change_verified == tier_change_checked, f"{tier_change_verified}/{tier_change_checked} verified")

    uncollectible = invoices[invoices["status"] == "uncollectible"]
    unc_merged = uncollectible.merge(subs[["subscription_id", "cancel_reason"]], on="subscription_id")
    check("Business rule", "every 'uncollectible' invoice belongs to a subscription whose cancel_reason is 'involuntary'",
          (unc_merged["cancel_reason"] == "involuntary").all())

    open_inv = invoices[invoices["status"] == "open"]
    open_merged = open_inv.merge(subs[["subscription_id", "status"]], on="subscription_id", suffixes=("", "_sub"))
    check("Business rule", "every 'open' invoice belongs to a subscription that is currently 'past_due'",
          (open_merged["status_sub"] == "past_due").all())

    n_involuntary_aligned = 0
    for o in objects:
        if o["cancel_reason"] == "involuntary":
            # Direct-from-origin, matching how current_period_start/end are
            # actually derived -- chaining bs._advance(current_period_start,
            # ..., 1) off an already-clamped date can drift under relativedelta
            # month-end clamping (e.g. Jan30->Feb28->Mar28, not Mar30) and was
            # the exact bug caught while building invoices.csv.
            origin = o["trial_end"] if o["interval_id"] == 1 else o["start_date"]
            k = 0
            while bs._advance(origin, o["billing_interval"], k) != o["current_period_start"]:
                k += 1
            next_boundary = bs._advance(origin, o["billing_interval"], k + 1)
            if next_boundary == o["canceled_at"]:
                n_involuntary_aligned += 1
    check("Business rule", "count of 'uncollectible' invoices exactly matches the count of involuntary churns "
                          "whose cancellation date lands exactly on a real renewal-cycle boundary",
          len(uncollectible) == n_involuntary_aligned, f"{len(uncollectible)} uncollectible vs. {n_involuntary_aligned} aligned involuntary churns")

    n_past_due = (subs["status"] == "past_due").sum()
    check("Business rule", "count of 'open' invoices exactly matches the count of currently past_due subscriptions",
          len(open_inv) == n_past_due, f"{len(open_inv)} open invoices vs. {n_past_due} past_due subscriptions")

    # --- 5. Distributional sanity ---
    total_revenue = invoices.loc[invoices["status"] == "paid", "amount_due"].sum()
    check("Distributional", "total recognized (paid) revenue is a plausible positive figure for this dataset's scale",
          0 < total_revenue < 500_000, f"${total_revenue:,.2f}")

    avg_invoices_per_sub = invoices.groupby("subscription_id").size().mean()
    check("Distributional", "average invoices per invoiced subscription is > 1 (most subscriptions renew at least once, "
                          "not just a single initial charge)",
          avg_invoices_per_sub > 1.5, f"actual: {avg_invoices_per_sub:.2f}")

    n_fail = sum(1 for _, _, ok, _ in results if not ok)
    for layer, name, ok, detail in results:
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {layer}: {name}" + (f"  -- {detail}" if detail else ""))
    print(f"\n{len(results) - n_fail}/{len(results)} checks passed")
    return n_fail == 0


if __name__ == "__main__":
    ok = run()
    if not ok:
        raise SystemExit(1)
