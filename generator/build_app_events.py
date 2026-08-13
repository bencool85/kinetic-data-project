"""
Phase 5 - app_events table (4 of 4, completes Phase 5). Fitness-specific
event vocabulary within each app_sessions.csv row: class_started,
workout_completed, workout_abandoned, streak_achieved.

Per-session funnel: every session gets a `class_started` event near its own
started_at, picking a workout_type from a small realistic taxonomy
(strength/hiit/yoga/cycling/running/mobility/core). Most sessions
(WORKOUT_COMPLETION_RATE = 85%) resolve to a `workout_completed` event near
the session's own ended_at, with duration_minutes matching that session's
real duration (single source of truth -- not re-decided here); the rest
resolve to `workout_abandoned` partway through the session window (someone
started a class and quit early -- the app-usage equivalent of web_events'
cart abandonment).

`streak_achieved` is NOT randomly sprinkled -- it's computed from each
customer's own REAL distinct session dates (consecutive-day runs, allowing
no gap). The first session on the day a run first reaches one of
STREAK_THRESHOLDS (3/7/14/30/60/100 days) gets a streak_achieved event with
that exact streak_days value. This means every streak_achieved event is
independently verifiable against app_sessions.csv's own dates -- exactly
the kind of derived-not-invented signal this whole project is built on.

Output: data/app_events.csv
"""
import datetime
import numpy as np
import pandas as pd

from params import SEED

WORKOUT_TYPES = ["strength", "hiit", "yoga", "cycling", "running", "mobility", "core"]
WORKOUT_TYPE_WEIGHTS = [0.22, 0.18, 0.15, 0.15, 0.12, 0.10, 0.08]

WORKOUT_COMPLETION_RATE = 0.85
STREAK_THRESHOLDS = [3, 7, 14, 30, 60, 100]


def _streak_days_for_dates(dates_sorted):
    """dates_sorted: sorted list of distinct dates for one customer. Returns
    {date: run_length_as_of_that_date} for a consecutive-day run (gap <= 1 day)."""
    run_length = {}
    current_run = 0
    prev_date = None
    for d in dates_sorted:
        if prev_date is not None and (d - prev_date).days == 1:
            current_run += 1
        else:
            current_run = 1
        run_length[d] = current_run
        prev_date = d
    return run_length


def build_app_events(seed=SEED + 18):
    rng = np.random.default_rng(seed)
    sessions = pd.read_csv("../data/app_sessions.csv")
    sessions["started_at"] = pd.to_datetime(sessions["started_at"])
    sessions["ended_at"] = pd.to_datetime(sessions["ended_at"])
    sessions["date"] = sessions["started_at"].dt.date

    rows = []

    def emit(session, event_type, occurred_at, workout_type=None, duration_minutes=None, streak_days=None):
        rows.append({
            "session_id": session.session_id,
            "customer_id": session.customer_id,
            "event_type": event_type,
            "occurred_at": occurred_at,
            "workout_type": workout_type,
            "duration_minutes": duration_minutes,
            "streak_days": streak_days,
        })

    # --- Per-session class_started / workout_completed|abandoned ---
    for session in sessions.itertuples():
        workout_type = str(rng.choice(WORKOUT_TYPES, p=WORKOUT_TYPE_WEIGHTS))
        start_offset = min(90, max(1, int((session.ended_at - session.started_at).total_seconds() * 0.05)))
        class_started_at = session.started_at + datetime.timedelta(seconds=int(rng.integers(1, start_offset + 1)))
        emit(session, "class_started", class_started_at, workout_type=workout_type)

        session_duration_min = (session.ended_at - session.started_at).total_seconds() / 60
        if rng.random() < WORKOUT_COMPLETION_RATE:
            emit(session, "workout_completed", session.ended_at,
                 workout_type=workout_type, duration_minutes=round(session_duration_min, 1))
        else:
            abandon_frac = float(rng.uniform(0.2, 0.6))
            # Whole seconds only -- same fractional-second timestamp pitfall
            # already fixed once in build_web_sessions.py/build_web_events.py.
            abandon_offset_seconds = int(round((session.ended_at - session.started_at).total_seconds() * abandon_frac))
            abandon_at = session.started_at + datetime.timedelta(seconds=abandon_offset_seconds)
            if abandon_at <= class_started_at:
                abandon_at = class_started_at + datetime.timedelta(seconds=30)
                abandon_at = min(abandon_at, session.ended_at)
            emit(session, "workout_abandoned", abandon_at,
                 workout_type=workout_type, duration_minutes=round(abandon_frac * session_duration_min, 1))

    # --- streak_achieved: derived from each customer's own real session dates ---
    # Pick, per (customer_id, date), the LAST session that day to attach the
    # streak event to (if a customer happens to have 2 sessions same day).
    last_session_by_day = (
        sessions.sort_values("started_at").groupby(["customer_id", "date"]).last().reset_index()
    )
    for cid, grp in last_session_by_day.groupby("customer_id"):
        dates_sorted = sorted(grp["date"])
        run_length = _streak_days_for_dates(dates_sorted)
        reached = set()
        for d in dates_sorted:
            rl = run_length[d]
            for threshold in STREAK_THRESHOLDS:
                if rl >= threshold and threshold not in reached:
                    reached.add(threshold)
                    session_row = grp[grp["date"] == d].iloc[0]
                    streak_at = pd.Timestamp(session_row["ended_at"])
                    emit(session_row, "streak_achieved", streak_at, streak_days=threshold)

    df = pd.DataFrame(rows).sort_values("occurred_at").reset_index(drop=True)
    df.insert(0, "event_id", [f"app_evt_{i:07d}" for i in range(1, len(df) + 1)])
    df["occurred_at"] = df["occurred_at"].apply(lambda d: pd.Timestamp(d).isoformat())
    return df


if __name__ == "__main__":
    df = build_app_events()
    df.to_csv("../data/app_events.csv", index=False)
    print(f"Wrote {len(df)} app_events\n")
    print(df["event_type"].value_counts().to_string())
    print()
    print(df.loc[df["event_type"] == "streak_achieved", "streak_days"].value_counts().sort_index().to_string())
