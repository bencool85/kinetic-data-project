"""
Phase 0 - Steps 2 & 3: Seasonality calendar + acquisition channel mix over time.

Produces:
  internal/_sim_seasonality_calendar.csv   (weekly demand multiplier)
  internal/_sim_channel_mix_schedule.csv   (weekly channel share, sums to 1.0)
  internal/seasonality_preview.png         (chart for sanity-checking)
"""
import datetime
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from params import (
    SEED, START_DATE, END_DATE, MONTHLY_SEASONALITY, GROWTH_END_MULTIPLIER,
    WEEKLY_NOISE_STDEV, CHANNEL_MIX_START, CHANNEL_MIX_END,
)

rng = np.random.default_rng(SEED)


def build_seasonality_calendar():
    weeks = pd.date_range(START_DATE, END_DATE, freq="W-MON")
    total_days = (END_DATE - START_DATE).days
    rows = []
    for w in weeks:
        month_factor = MONTHLY_SEASONALITY[w.month]
        progress = (w.date() - START_DATE).days / total_days  # 0 -> 1 over the 3 years
        growth_factor = 1.0 + progress * (GROWTH_END_MULTIPLIER - 1.0)
        noise = rng.normal(1.0, WEEKLY_NOISE_STDEV)
        multiplier = max(0.1, month_factor * growth_factor * noise)
        rows.append({"week_start": w.date().isoformat(), "multiplier": round(multiplier, 4)})
    return pd.DataFrame(rows)


def build_channel_mix_schedule(calendar_df):
    total_days = (END_DATE - START_DATE).days
    channels = list(CHANNEL_MIX_START.keys())
    rows = []
    for week_start in calendar_df["week_start"]:
        w = datetime.date.fromisoformat(week_start)
        progress = (w - START_DATE).days / total_days
        shares = {
            ch: CHANNEL_MIX_START[ch] + progress * (CHANNEL_MIX_END[ch] - CHANNEL_MIX_START[ch])
            for ch in channels
        }
        total = sum(shares.values())
        shares = {ch: round(v / total, 4) for ch, v in shares.items()}
        rows.append({"week_start": week_start, **shares})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    cal = build_seasonality_calendar()
    mix = build_channel_mix_schedule(cal)

    cal.to_csv("../internal/_sim_seasonality_calendar.csv", index=False)
    mix.to_csv("../internal/_sim_channel_mix_schedule.csv", index=False)

    # Preview chart: seasonality multiplier over time
    cal["week_start"] = pd.to_datetime(cal["week_start"])
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(cal["week_start"], cal["multiplier"], linewidth=1.2, color="#2a6f6f")
    ax.set_title("Seasonality demand multiplier — weekly (drives signups, spend, traffic)")
    ax.set_ylabel("Multiplier")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig("../internal/seasonality_preview.png", dpi=130)

    print("=== Seasonality calendar (sample) ===")
    print(cal.head(8).to_string(index=False))
    print(f"...{len(cal)} weekly rows total, min={cal['multiplier'].min():.2f}, "
          f"max={cal['multiplier'].max():.2f}, mean={cal['multiplier'].mean():.2f}")

    print("\n=== Channel mix schedule (first vs last week) ===")
    print(mix.iloc[[0, -1]].to_string(index=False))
