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
