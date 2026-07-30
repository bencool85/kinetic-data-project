"""
Phase 2 - subscription_events table (table 2 of 3): the event log behind
every subscriptions.csv row. event_type vocabulary matches
schema_reference.md exactly: trial_started, trial_converted, trial_expired,
canceled_during_trial, renewed, upgraded, downgraded, payment_failed,
canceled, resumed.

Amended (2026-07-30, while building `invoices`): a currently `past_due`
subscription's current_period_start is the PENDING/failed renewal attempt
itself (that's the whole reason it's past_due) -- not a successful one, so
it must not also get a "renewed" event at that same cycle boundary (that
would contradict the payment_failed event at the identical timestamp: a
subscription can't have both successfully renewed and be past_due for the
exact same billing attempt). The renewed-event loop now excludes that final
cycle boundary specifically for past_due subscriptions.

Built by importing `build_subscription_objects()` directly from
build_subscriptions.py (the same in-memory objects, not a re-parse of
subscriptions.csv) -- single source of truth, so the two tables can never
drift apart on subscription_id/customer_id/dates.

Two kinds of source events, combined:
1. Directly derivable from each subscription object's own fields (no new
   invention): trial_started (trial_start), trial_converted (trial_end, only
   for the interval_id==1 converted case), trial_expired (trial_end, for
   expired_passively), canceled_during_trial (canceled_at, for
   canceled_during_trial). Also the past_due overlay's own payment_failed
   (past_due_since) -- that mechanic was invented at the subscriptions layer
   and its event has to be invented here too, using the exact same date
   (past_due_since), not a freshly-rolled one.
2. Pulled straight from the master timeline's raw `subscription_events` list
   (payment_failed blips + the unresolved one at involuntary churn,
   upgraded/downgraded, canceled, resumed) -- matched to the right
   subscription_id via (sim_customer_id, interval_id), since the timeline
   already tags each raw event with the interval it happened in.
   old_plan/new_plan for upgraded/downgraded aren't stored on the raw event,
   but are fully implied by event_type in this design (upgraded is always
   basic->plus, downgraded always plus->basic -- see
   simulate_subscription_lifecycle's single binary swap), so they're filled
   in here rather than left blank.

`renewed` events don't exist anywhere in the master timeline at all (Phase 0
never modeled individual billing-cycle rollovers) -- generated here by
cycling the same `_advance()` billing-interval math subscriptions.py already
uses, from the subscription's origin date up to (not including)
current_period_start.

Realistic messiness (per schema_reference.md's own intro, "duplicate
webhook-style events"): a small share of events (DUPLICATE_WEBHOOK_RATE) get
a byte-for-byte duplicate row -- same subscription/type/timestamp, new
event_id -- simulating Stripe's at-least-once webhook delivery.

Output: data/subscription_events.csv
"""
import datetime
import json
import numpy as np
import pandas as pd

from params import SEED, DUPLICATE_WEBHOOK_RATE
import build_subscriptions as bs


def build_subscription_events(timeline, seed=SEED + 8):
    rng = np.random.default_rng(seed)
    objects = bs.build_subscription_objects(timeline)
    raw_events_by_customer = {t["customer_id"]: t["subscription_events"] for t in timeline}

    rows = []

    def emit(subscription_id, customer_id, event_type, event_at, old_plan=None, new_plan=None,
             resolved=None, reason=None):
        rows.append({
            "subscription_id": subscription_id, "customer_id": customer_id,
            "event_type": event_type, "event_at": event_at,
            "old_plan": old_plan, "new_plan": new_plan, "resolved": resolved, "reason": reason,
        })

    for obj in objects:
        sub_id, cid, sim_id = obj["subscription_id"], obj["customer_id"], obj["sim_customer_id"]

        if obj["interval_id"] == 0:
            # A trial that never converted to a real interval.
            emit(sub_id, cid, "trial_started", obj["trial_start"])
            if obj["cancel_reason"] == "trial_canceled":
                emit(sub_id, cid, "canceled_during_trial", obj["canceled_at"])
            elif obj["cancel_reason"] == "trial_expired":
                emit(sub_id, cid, "trial_expired", obj["trial_end"])
            # trial_in_progress: no resolution event yet -- still pending as of END_DATE.
            continue

        if obj["interval_id"] == 1:
            emit(sub_id, cid, "trial_started", obj["trial_start"])
            emit(sub_id, cid, "trial_converted", obj["trial_end"])
            origin = obj["trial_end"]
        else:
            # resumed is also present in the raw timeline events (matched below),
            # so it isn't manually emitted here -- avoids emitting it twice.
            origin = obj["start_date"]

        # renewed: one per fully-elapsed billing cycle since origin, up to
        # (and including) the cycle that produced current_period_start --
        # EXCEPT for a currently 'past_due' subscription, where
        # current_period_start IS the pending/failed renewal attempt itself
        # (see its payment_failed event below), not a successful one. Emitting
        # a "renewed" event for that same cycle boundary would contradict the
        # payment_failed event happening at the identical timestamp -- a
        # subscription can't have both successfully renewed and be past_due
        # for that exact same billing attempt.
        k = 1
        while True:
            candidate = bs._advance(origin, obj["billing_interval"], k)
            if obj["status"] == "past_due" and candidate >= obj["current_period_start"]:
                break
            if candidate <= obj["current_period_start"]:
                emit(sub_id, cid, "renewed", candidate)
                k += 1
            else:
                break

        # Raw timeline events for this specific interval: payment_failed
        # (both resolved blips and the unresolved one at involuntary churn),
        # upgraded/downgraded, canceled, resumed.
        for e in raw_events_by_customer.get(sim_id, []):
            if e.get("interval_id") != obj["interval_id"]:
                continue
            et = e["event_type"]
            event_at = datetime.date.fromisoformat(e["event_at"])
            if et == "payment_failed":
                emit(sub_id, cid, "payment_failed", event_at, resolved=e["resolved"])
            elif et in ("upgraded", "downgraded"):
                new_tier = "plus" if et == "upgraded" else "basic"
                old_tier = "basic" if et == "upgraded" else "plus"
                emit(sub_id, cid, et, event_at,
                     old_plan=bs._plan_id(old_tier, obj["billing_interval"]),
                     new_plan=bs._plan_id(new_tier, obj["billing_interval"]))
            elif et == "canceled":
                emit(sub_id, cid, "canceled", event_at, reason=e["reason"])
            elif et == "resumed":
                emit(sub_id, cid, "resumed", event_at)

        # past_due overlay's own payment_failed -- invented at the
        # subscriptions layer, so its event has to be invented here too,
        # using the exact same past_due_since date (single source of truth).
        if obj["status"] == "past_due":
            emit(sub_id, cid, "payment_failed", obj["past_due_since"], resolved=False)

    df = pd.DataFrame(rows)
    df["event_at"] = pd.to_datetime(df["event_at"])
    df = df.sort_values(["customer_id", "event_at"]).reset_index(drop=True)

    # Give each event a plausible intra-day time-of-day (dates alone are what
    # the underlying logic produces; a real event stream has second-level
    # timestamps) -- deterministic offset keyed on each row's pre-duplication
    # position, assigned BEFORE duplicating so a duplicated row carries the
    # exact same full timestamp as its original (that's the point: a
    # redelivered webhook is a byte-for-byte copy, including event_at).
    offsets = pd.to_timedelta([(i * 37) % 86400 for i in range(len(df))], unit="s")
    df["event_at"] = df["event_at"] + offsets

    # Realistic messiness: duplicate a small share of events byte-for-byte
    # (same subscription/type/timestamp/fields), simulating Stripe's
    # at-least-once webhook redelivery.
    n_dupes = int(round(len(df) * DUPLICATE_WEBHOOK_RATE))
    dupe_idx = rng.choice(df.index, size=n_dupes, replace=False)
    df = pd.concat([df, df.loc[dupe_idx]], ignore_index=True)
    df = df.sort_values(["customer_id", "event_at"]).reset_index(drop=True)

    df.insert(0, "event_id", [f"evt_{i+1:06d}" for i in range(len(df))])
    df["event_at"] = df["event_at"].dt.strftime("%Y-%m-%dT%H:%M:%S")

    return df[["event_id", "subscription_id", "customer_id", "event_type", "event_at",
                "old_plan", "new_plan", "resolved", "reason"]]


if __name__ == "__main__":
    timeline = json.load(open("../internal/_sim_customer_timeline.json"))
    df = build_subscription_events(timeline)
    df.to_csv("../data/subscription_events.csv", index=False)
    print(f"Wrote {len(df)} subscription_events\n")
    print(df["event_type"].value_counts().to_string())
    n_dupe_rows = df.duplicated(subset=["subscription_id", "event_type", "event_at"]).sum()
    print(f"\nDuplicate webhook-style rows (same subscription/type/timestamp, different event_id): {n_dupe_rows} "
          f"({n_dupe_rows/len(df):.2%})")
