"""
Phase 7 shared helpers -- used by every platform's *_performance_daily /
*_insights_daily / *_stats_daily / *_reports_daily build script. Centralizes
the one thing all 6 platforms have in common: daily spend/volume that moves
with the SAME seasonality calendar and channel-mix schedule that already
drove web_sessions.csv's own utm_source volume (Phase 5), so a platform's
reported spend curve and its own attributed session volume move together
even though (per schema_reference.md) there's no row-level join between
them.
"""
import bisect
import datetime

import numpy as np
import pandas as pd

from params import BASE_DAILY_AD_SPEND_TOTAL, AD_SPEND_NOISE_SD


def load_calendar_lookups():
    """Returns (week_starts: sorted list[date], multiplier_by_week: dict,
    channel_share_by_week: dict[date -> dict[channel -> float]])."""
    cal = pd.read_csv("../internal/_sim_seasonality_calendar.csv")
    cal["week_start"] = pd.to_datetime(cal["week_start"]).dt.date
    mix = pd.read_csv("../internal/_sim_channel_mix_schedule.csv")
    mix["week_start"] = pd.to_datetime(mix["week_start"]).dt.date

    week_starts = sorted(cal["week_start"].tolist())
    multiplier_by_week = dict(zip(cal["week_start"], cal["multiplier"]))
    channel_cols = [c for c in mix.columns if c != "week_start"]
    channel_share_by_week = {
        row["week_start"]: {c: row[c] for c in channel_cols} for _, row in mix.iterrows()
    }
    return week_starts, multiplier_by_week, channel_share_by_week


def week_start_for(d, week_starts):
    """Maps any date to its containing calendar week (Monday), clamping to
    the first/last known week for dates outside the calendar's own range
    (a handful of days at the very start of START_DATE before the first
    Monday, and END_DATE trailing a few days past the last Monday)."""
    idx = bisect.bisect_right(week_starts, d) - 1
    if idx < 0:
        return week_starts[0]
    if idx >= len(week_starts):
        return week_starts[-1]
    return week_starts[idx]


def daily_channel_spend(d, channel, week_starts, multiplier_by_week, channel_share_by_week, rng):
    """Total whole-business daily spend for one channel on one date, as the
    deterministic seasonality*mix baseline times a lognormal noise draw --
    same noise mechanism used throughout this project (e.g. WEEKLY_NOISE_STDEV
    elsewhere) applied at daily grain here since ad spend pacing is a
    day-to-day operational decision, not a weekly-locked one."""
    wk = week_start_for(d, week_starts)
    baseline = BASE_DAILY_AD_SPEND_TOTAL * multiplier_by_week[wk] * channel_share_by_week[wk][channel]
    noise = rng.lognormal(mean=0.0, sigma=AD_SPEND_NOISE_SD)
    return baseline * noise


def date_range(start_date, end_date):
    d = start_date
    while d <= end_date:
        yield d
        d += datetime.timedelta(days=1)


def cap_flight_at_budget(flight_days, budget_usd, row_fn, spend_col, to_usd):
    """Added 2026-09-29. A lifetime-budget flight must never spend more than
    its budget (real platforms stop billing there), but each flight day's
    spend is a random draw around budget / n_days, so the total could land a
    few percent over. If it does, scale that flight's days down proportionally
    so it spends exactly its budget.

    flight_days: list of (rng_state_before_row, ad, date, spend_usd, row)
    tuples collected while building the flight. The saved rng state lets each
    row be rebuilt with the SAME random rates (CPM, CTR, etc.) at the lower
    spend, using a throwaway generator -- so the shared random stream, and
    therefore every other row in the table, is untouched. A flight already
    within budget is returned exactly as drawn.
    """
    rows = [r for (_, _, _, _, r) in flight_days]
    total = sum(r[spend_col] * to_usd for r in rows)
    if total <= budget_usd:
        return rows
    factor = budget_usd / total
    for _ in range(20):  # per-row rounding can leave a few cents over; nudge down until it fits
        rebuilt = []
        for state, ad, d, spend, _row in flight_days:
            replay = np.random.default_rng()
            replay.bit_generator.state = state
            rebuilt.append(row_fn(replay, ad, d, spend * factor, "brand_lift"))
        new_total = sum(r[spend_col] * to_usd for r in rebuilt)
        if new_total <= budget_usd:
            return rebuilt
        factor *= budget_usd / new_total * 0.9999
    raise RuntimeError("could not fit flight within budget")
