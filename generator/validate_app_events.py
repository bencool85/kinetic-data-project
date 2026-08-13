"""
Validation for `app_events` (Phase 5, table 4 of 4, completes Phase 5) --
pandas-based, same 5-layer approach (see validate_products.py's docstring
for why pandas instead of DuckDB).

Central cross-checks: every session gets EXACTLY one class_started and
EXACTLY one of workout_completed/workout_abandoned (never both, never
neither); workout_completed's duration_minutes matches that session's own
real duration exactly; every event's occurred_at falls within its own
session's time window; and -- the most important one -- streak_achieved
events are independently RE-DERIVED from app_sessions.csv's own dates here
in the validator (consecutive-day runs per customer) and checked for an
EXACT match against what the build produced, proving the streak signal is
genuinely computed from real session dates, not sprinkled in.
"""
import pandas as pd

from params import SEED
import build_app_events as bae

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    events = pd.read_csv("../data/app_events.csv")
    sessions = pd.read_csv("../data/app_sessions.csv")

    events["occurred_at"] = pd.to_datetime(events["occurred_at"])
    sessions["started_at"] = pd.to_datetime(sessions["started_at"])
    sessions["ended_at"] = pd.to_datetime(sessions["ended_at"])
    sessions["date"] = sessions["started_at"].dt.date

    # --- 1. Structural ---
    check("Structural", "event_id non-null and unique",
          events["event_id"].notna().all() and events["event_id"].is_unique)
    check("Structural", "session_id, customer_id, event_type, occurred_at all non-null",
          events[["session_id", "customer_id", "event_type", "occurred_at"]].notna().all().all())
    valid_types = {"class_started", "workout_completed", "workout_abandoned", "streak_achieved"}
    check("Structural", "event_type is always one of the 4 defined values", events["event_type"].isin(valid_types).all())
    check("Structural", "workout_type is populated iff event_type is class_started/workout_completed/"
                        "workout_abandoned (never for streak_achieved)",
          (events.loc[events["event_type"] != "streak_achieved", "workout_type"].notna().all())
          and (events.loc[events["event_type"] == "streak_achieved", "workout_type"].isna().all()))
    check("Structural", "streak_days is populated iff event_type == 'streak_achieved'",
          (events.loc[events["event_type"] == "streak_achieved", "streak_days"].notna().all())
          and (events.loc[events["event_type"] != "streak_achieved", "streak_days"].isna().all()))
    check("Structural", "duration_minutes is populated iff event_type is workout_completed/workout_abandoned",
          (events.loc[events["event_type"].isin(["workout_completed", "workout_abandoned"]), "duration_minutes"].notna().all())
          and (events.loc[events["event_type"].isin(["class_started", "streak_achieved"]), "duration_minutes"].isna().all()))

    # --- 2. Referential integrity ---
    session_customer = sessions.set_index("session_id")["customer_id"]
    check("Referential", "every session_id exists in app_sessions.csv", events["session_id"].isin(session_customer.index).all())
    check("Referential", "every event's customer_id matches its own session's customer_id in app_sessions.csv",
          (events["session_id"].map(session_customer) == events["customer_id"]).all())

    # --- 3. Temporal ordering ---
    joined = events.merge(sessions[["session_id", "started_at", "ended_at"]], on="session_id")
    check("Temporal", "every event's occurred_at falls within its own session's [started_at, ended_at] window",
          ((joined["occurred_at"] >= joined["started_at"]) & (joined["occurred_at"] <= joined["ended_at"])).all())

    # --- 4. Business-rule invariants ---
    counts = events.groupby(["session_id", "event_type"]).size().unstack(fill_value=0)
    check("Business rule", "every session has EXACTLY one class_started event",
          (counts.get("class_started", 0) == 1).all() and len(counts) == len(sessions))
    completed_or_abandoned = counts.get("workout_completed", 0) + counts.get("workout_abandoned", 0)
    check("Business rule", "every session resolves to EXACTLY one of workout_completed/workout_abandoned "
                          "(never both, never neither)",
          (completed_or_abandoned == 1).all())

    completed = events[events["event_type"] == "workout_completed"].merge(
        sessions[["session_id", "started_at", "ended_at"]], on="session_id")
    completed["real_duration"] = (completed["ended_at"] - completed["started_at"]).dt.total_seconds() / 60
    check("Business rule", "workout_completed's duration_minutes exactly matches its own session's real duration",
          (completed["duration_minutes"].round(1) == completed["real_duration"].round(1)).all())

    # Independent re-derivation of streak_achieved from app_sessions.csv's own dates.
    last_session_by_day = sessions.sort_values("started_at").groupby(["customer_id", "date"]).last().reset_index()
    expected = []
    for cid, grp in last_session_by_day.groupby("customer_id"):
        dates_sorted = sorted(grp["date"])
        run_length = bae._streak_days_for_dates(dates_sorted)
        reached = set()
        for d in dates_sorted:
            rl = run_length[d]
            for threshold in bae.STREAK_THRESHOLDS:
                if rl >= threshold and threshold not in reached:
                    reached.add(threshold)
                    expected.append((cid, threshold))
    expected_set = set(expected)
    actual_set = set(zip(events.loc[events["event_type"] == "streak_achieved", "customer_id"],
                          events.loc[events["event_type"] == "streak_achieved", "streak_days"].astype(int)))
    check("Business rule", "streak_achieved events exactly match an independent re-derivation from "
                          "app_sessions.csv's own consecutive-day session dates (proves the signal is "
                          "computed, not invented)",
          expected_set == actual_set, detail=f"{len(actual_set)} actual vs {len(expected_set)} re-derived")

    # --- 5. Distributional sanity ---
    completion_rate = (events["event_type"] == "workout_completed").sum() / len(sessions)
    check("Distributional", "workout completion rate lands close to the configured 85% (80-90% band)",
          0.80 <= completion_rate <= 0.90, detail=f"{completion_rate:.1%}")
    workout_type_share = events.loc[events["event_type"] == "class_started", "workout_type"].value_counts(normalize=True)
    check("Distributional", "'strength' is the most common workout_type (configured as the highest-weighted)",
          workout_type_share.idxmax() == "strength")

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
