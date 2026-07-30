"""
Validation for `subscription_events` (Phase 2, table 2 of 3) -- pandas-based,
same 5-layer approach (see validate_products.py's docstring for why pandas
instead of DuckDB).

Central cross-checks: every event traces back to a real subscription_id in
subscriptions.csv with a matching customer_id; the handful of event types
that are directly derivable from a subscription's own fields (trial_started,
trial_converted, trial_expired, canceled_during_trial, the past_due
payment_failed) match those fields EXACTLY, not approximately; and the
realistic "duplicate webhook" messiness is present at roughly the configured
rate, distinguishable via a natural-key duplicate check (not by event_id,
which is deliberately always unique).
"""
import datetime
import json
import pandas as pd

from params import DUPLICATE_WEBHOOK_RATE
import build_subscriptions as bs
import build_subscription_events as bse

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    events = pd.read_csv("../data/subscription_events.csv")
    subs = pd.read_csv("../data/subscriptions.csv")
    timeline = json.load(open("../internal/_sim_customer_timeline.json"))
    objects = bs.build_subscription_objects(timeline)
    obj_by_sub_id = {o["subscription_id"]: o for o in objects}

    events["event_at"] = pd.to_datetime(events["event_at"])
    for col in ["trial_start", "trial_end", "canceled_at", "past_due_since"]:
        subs[col] = pd.to_datetime(subs[col])

    VALID_TYPES = {"trial_started", "trial_converted", "trial_expired", "canceled_during_trial",
                   "renewed", "upgraded", "downgraded", "payment_failed", "canceled", "resumed"}

    # --- 1. Structural ---
    check("Structural", "event_id non-null and unique",
          events["event_id"].notna().all() and events["event_id"].is_unique)
    check("Structural", "subscription_id and customer_id non-null on every row",
          events["subscription_id"].notna().all() and events["customer_id"].notna().all())
    check("Structural", f"event_type is one of the {len(VALID_TYPES)} types in schema_reference.md",
          events["event_type"].isin(VALID_TYPES).all())
    check("Structural", "event_at parses as a valid timestamp", events["event_at"].notna().all())
    check("Structural", "old_plan/new_plan populated if and only if event_type in {upgraded, downgraded}",
          (events["event_type"].isin(["upgraded", "downgraded"]) ==
           (events["old_plan"].notna() & events["new_plan"].notna())).all())
    check("Structural", "resolved populated if and only if event_type == 'payment_failed'",
          (events["event_type"].eq("payment_failed") == events["resolved"].notna()).all())
    check("Structural", "reason populated if and only if event_type in {canceled, ... } "
                        "(specifically: only the real post-conversion 'canceled' event carries a reason)",
          (events["event_type"].eq("canceled") == events["reason"].notna()).all())
    check("Structural", "reason in {voluntary, involuntary} wherever populated",
          events["reason"].dropna().isin(["voluntary", "involuntary"]).all())

    # --- 2. Referential integrity ---
    check("Referential", "every subscription_id in subscription_events exists in subscriptions.csv",
          events["subscription_id"].isin(subs["subscription_id"]).all())
    joined = events.merge(subs[["subscription_id", "customer_id"]], on="subscription_id", suffixes=("", "_sub"))
    check("Referential", "every event's customer_id matches the customer_id on its own subscription_id "
                        "(no cross-wired events)",
          (joined["customer_id"] == joined["customer_id_sub"]).all())

    # --- 3. Temporal ordering ---
    trial_started = events[events["event_type"] == "trial_started"].drop_duplicates(
        subset=["subscription_id", "event_at"])
    ts_merged = trial_started.merge(subs[["subscription_id", "trial_start"]], on="subscription_id")
    check("Temporal", "every trial_started event's date matches subscriptions.trial_start exactly",
          (ts_merged["event_at"].dt.date == ts_merged["trial_start"].dt.date).all())

    trial_converted = events[events["event_type"] == "trial_converted"].drop_duplicates(
        subset=["subscription_id", "event_at"])
    tc_merged = trial_converted.merge(subs[["subscription_id", "trial_end"]], on="subscription_id")
    check("Temporal", "every trial_converted event's date matches subscriptions.trial_end exactly",
          (tc_merged["event_at"].dt.date == tc_merged["trial_end"].dt.date).all())

    trial_expired = events[events["event_type"] == "trial_expired"].drop_duplicates(
        subset=["subscription_id", "event_at"])
    te_merged = trial_expired.merge(subs[["subscription_id", "trial_end", "cancel_reason"]], on="subscription_id")
    check("Temporal", "every trial_expired event's date matches subscriptions.trial_end exactly, "
                      "and only occurs on subscriptions whose cancel_reason is trial_expired",
          (te_merged["event_at"].dt.date == te_merged["trial_end"].dt.date).all()
          and (te_merged["cancel_reason"] == "trial_expired").all())

    cdt = events[events["event_type"] == "canceled_during_trial"].drop_duplicates(
        subset=["subscription_id", "event_at"])
    cdt_merged = cdt.merge(subs[["subscription_id", "canceled_at", "cancel_reason"]], on="subscription_id")
    check("Temporal", "every canceled_during_trial event's date matches subscriptions.canceled_at exactly, "
                      "and only occurs on subscriptions whose cancel_reason is trial_canceled",
          (cdt_merged["event_at"].dt.date == cdt_merged["canceled_at"].dt.date).all()
          and (cdt_merged["cancel_reason"] == "trial_canceled").all())

    real_canceled = events[events["event_type"] == "canceled"].drop_duplicates(subset=["subscription_id", "event_at"])
    rc_merged = real_canceled.merge(subs[["subscription_id", "canceled_at", "cancel_reason"]], on="subscription_id")
    check("Temporal", "every real 'canceled' event's date matches subscriptions.canceled_at exactly, "
                      "and its reason matches subscriptions.cancel_reason exactly",
          (rc_merged["event_at"].dt.date == rc_merged["canceled_at"].dt.date).all()
          and (rc_merged["reason"] == rc_merged["cancel_reason"]).all())

    pd_failed = events[(events["event_type"] == "payment_failed") & (events["resolved"] == False)].drop_duplicates(  # noqa: E712
        subset=["subscription_id", "event_at"])
    past_due_subs = subs[subs["status"] == "past_due"]
    pd_merged = pd_failed.merge(past_due_subs[["subscription_id", "past_due_since"]], on="subscription_id", how="inner")
    check("Temporal", "every past_due subscription has a matching unresolved payment_failed event "
                      "on exactly its past_due_since date",
          len(pd_merged) == len(past_due_subs)
          and (pd_merged["event_at"].dt.date == pd_merged["past_due_since"].dt.date).all())

    # Floor is trial_start where present (the object's true earliest possible
    # event -- trial_started fires there), else start_date (for interval_id
    # 2+ resubscribes, which have no trial at all).
    subs_floor = subs[["subscription_id", "start_date", "trial_start"]].assign(
        floor_date=lambda d: pd.to_datetime(d["trial_start"]).fillna(pd.to_datetime(d["start_date"])))
    check("Temporal", "no event's timestamp falls before its own subscription's earliest possible date "
                      "(trial_start where present, else start_date -- events never predate the object they belong to)",
          events.merge(subs_floor[["subscription_id", "floor_date"]], on="subscription_id")
          .pipe(lambda d: (d["event_at"].dt.normalize() >= d["floor_date"].dt.normalize()).all()))

    # --- 4. Business-rule invariants ---
    # renewed-event count per subscription must match an independent
    # recomputation of elapsed billing cycles (not just re-trust the builder).
    renewed_counts = events[events["event_type"] == "renewed"].drop_duplicates(
        subset=["subscription_id", "event_at"]).groupby("subscription_id").size()
    mismatches = 0
    for o in objects:
        if o["interval_id"] == 0:
            continue
        origin = o["trial_end"] if o["interval_id"] == 1 else o["start_date"]
        k = 0
        while bse.bs._advance(origin, o["billing_interval"], k + 1) <= o["current_period_start"]:
            k += 1
        expected = k
        actual = int(renewed_counts.get(o["subscription_id"], 0))
        if actual != expected:
            mismatches += 1
    check("Business rule", "every subscription's 'renewed' event count matches an independently "
                          "recomputed elapsed-billing-cycle count exactly",
          mismatches == 0, f"{mismatches} mismatches out of {len(objects)} subscription objects")

    # Exactly one trial_started (deduped) per subscription with interval_id 0 or 1.
    n_trial_objects = sum(1 for o in objects if o["interval_id"] in (0, 1))
    n_trial_started_deduped = trial_started["subscription_id"].nunique()
    check("Business rule", "exactly one trial_started event per subscription object that has a trial "
                          "(deduped for webhook-style repeats)",
          n_trial_started_deduped == n_trial_objects,
          f"{n_trial_started_deduped} vs. {n_trial_objects} trial-bearing subscription objects")

    n_upgraded = events[events["event_type"] == "upgraded"].drop_duplicates(subset=["subscription_id", "event_at"])
    n_downgraded = events[events["event_type"] == "downgraded"].drop_duplicates(subset=["subscription_id", "event_at"])
    check("Business rule", "no subscription has both an upgraded and a downgraded event "
                          "(the simulation allows at most one plan change per interval)",
          len(set(n_upgraded["subscription_id"]) & set(n_downgraded["subscription_id"])) == 0)

    # --- 5. Distributional sanity ---
    dup_key_cols = ["subscription_id", "event_type", "event_at"]
    n_dupe_rows = events.duplicated(subset=dup_key_cols).sum()
    dupe_rate = n_dupe_rows / len(events)
    check("Distributional", f"duplicate webhook-style rows present at ~{DUPLICATE_WEBHOOK_RATE:.0%} (within 1.5pp), "
                          "detectable via a natural key (subscription_id+event_type+event_at), not event_id",
          abs(dupe_rate - DUPLICATE_WEBHOOK_RATE) < 0.015, f"actual: {dupe_rate:.2%}")

    check("Distributional", "event_type distribution is non-degenerate (all 10 types minus 'paused'-adjacent "
                          "gaps have at least 1 real occurrence, except none expected to be zero here)",
          events["event_type"].nunique() == len(VALID_TYPES))

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
