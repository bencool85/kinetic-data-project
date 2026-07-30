"""
Shared helpers for Phase 0 simulation: weighted date/channel sampling against the
seasonality calendar and channel mix schedule built in Steps 2-3.
"""
import calendar as calendar_module
import datetime
import pandas as pd

CALENDAR_PATH = "../internal/_sim_seasonality_calendar.csv"
CHANNEL_MIX_PATH = "../internal/_sim_channel_mix_schedule.csv"


def load_calendar(path=CALENDAR_PATH):
    return pd.read_csv(path, parse_dates=["week_start"])


def load_channel_mix(path=CHANNEL_MIX_PATH):
    return pd.read_csv(path, parse_dates=["week_start"])


def sample_weighted_date(calendar_df, rng, start_date=None, end_date=None):
    """Sample a date, weighted by weekly seasonality multiplier, optionally
    restricted to [start_date, end_date]."""
    df = calendar_df
    if start_date is not None:
        df = df[df["week_start"] >= pd.Timestamp(start_date)]
    if end_date is not None:
        df = df[df["week_start"] <= pd.Timestamp(end_date)]
    if df.empty:
        df = calendar_df
    weights = df["multiplier"].to_numpy(dtype=float)
    weights = weights / weights.sum()
    idx = rng.choice(len(df), p=weights)
    week_start = df.iloc[idx]["week_start"].date()
    day_offset = int(rng.integers(0, 7))
    date = week_start + datetime.timedelta(days=day_offset)
    if start_date is not None and date < start_date:
        date = start_date
    if end_date is not None and date > end_date:
        date = end_date
    return date


def sample_seasonal_month_date(rng, earliest_date, latest_date, monthly_weights):
    """Sample a date weighted by CALENDAR MONTH ONLY (e.g. MONTHLY_SEASONALITY --
    January highest), independent of the multi-year growth trend. Used for events
    like win-back timing, where the goal is "every January, regardless of year,
    this is more likely" -- reusing the full seasonality calendar (which bakes in
    3 years of growth trend) would bias toward whichever real months happen to be
    closest to the dataset's end date, not toward January specifically.

    Builds the list of (year, month) periods spanning [earliest_date, latest_date],
    weights each by monthly_weights[month], samples one, then a day uniformly
    within that period's overlap with the [earliest_date, latest_date] bounds."""
    periods = []
    y, m = earliest_date.year, earliest_date.month
    while (y, m) <= (latest_date.year, latest_date.month):
        periods.append((y, m))
        m += 1
        if m == 13:
            m = 1
            y += 1

    weights = [monthly_weights[m] for (_, m) in periods]
    total = sum(weights)
    weights = [w / total for w in weights]
    idx = rng.choice(len(periods), p=weights)
    y, m = periods[idx]

    days_in_month = calendar_module.monthrange(y, m)[1]
    day_lo = earliest_date.day if (y, m) == (earliest_date.year, earliest_date.month) else 1
    day_hi = latest_date.day if (y, m) == (latest_date.year, latest_date.month) else days_in_month
    if day_hi < day_lo:
        day_hi = day_lo
    day = int(rng.integers(day_lo, day_hi + 1))
    return datetime.date(y, m, day)


def sample_channel(channel_mix_df, rng, on_date):
    """Weighted-sample a channel from the mix active in the week containing on_date."""
    df = channel_mix_df
    candidates = df[df["week_start"] <= pd.Timestamp(on_date)]
    row = candidates.iloc[-1] if not candidates.empty else df.iloc[0]
    channels = [c for c in df.columns if c != "week_start"]
    weights = pd.Series([row[c] for c in channels], dtype=float)
    weights = (weights / weights.sum()).to_numpy()  # guard against rounding drift in the CSV
    return str(rng.choice(channels, p=weights))
