"""
Phase 7 - dv360_performance_daily table (3 of 3, completes DV360). The
genuinely-different-shape table schema_reference.md calls out: unlike
Meta/YouTube/Snap/TikTok's one-row-per-ad-or-ad-group-per-day, DV360 buys
programmatically across many open-web exchanges and environments, so EACH
line_item/day fragments into several (exchange, environment) rows here --
real-time bidding across a fragmented supply chain, not one owned/operated
surface.

Same seasonality-calendar x channel-mix-schedule spend driver as every
other platform (paid_media_common.py), split across the 5 evergreen
objectives (DV360_OBJECTIVE_SPEND_SHARE) then across that objective's line
items, THEN across a random 3-7 (exchange, environment) combinations for
that line_item/day -- video (brand_lift) line items draw from the
Connected-TV-inclusive environment list, display line items don't.

Output: data/dv360_performance_daily.csv
"""
import numpy as np
import pandas as pd

from params import (SEED, START_DATE, END_DATE, DV360_OBJECTIVE_SPEND_SHARE, AD_PAUSE_DAY_RATE,
                     DV360_EXCHANGES, DV360_EXCHANGE_WEIGHTS, DV360_ENVIRONMENTS_DISPLAY,
                     DV360_ENVIRONMENTS_DISPLAY_WEIGHTS, DV360_ENVIRONMENTS_VIDEO, DV360_ENVIRONMENTS_VIDEO_WEIGHTS,
                     DV360_CPM_RANGE_BY_OBJECTIVE, DV360_CTR_RANGE_BY_OBJECTIVE, DV360_CONVERSION_RATE_BY_OBJECTIVE,
                     DV360_AVG_CONVERSION_VALUE_RANGE, DV360_EXCHANGE_ENV_COMBOS_PER_DAY_RANGE)
from paid_media_common import load_calendar_lookups, daily_channel_spend, date_range


def build_dv360_performance_daily(seed=SEED + 60):
    rng = np.random.default_rng(seed)
    week_starts, multiplier_by_week, channel_share_by_week = load_calendar_lookups()

    ios = pd.read_csv("../data/dv360_insertion_orders.csv")
    line_items = pd.read_csv("../data/dv360_line_items.csv")
    line_items = line_items.merge(ios[["insertion_order_id", "ad_objective"]], on="insertion_order_id")
    by_objective = {obj: g for obj, g in line_items.groupby("ad_objective")}

    rows = []
    for d in date_range(START_DATE, END_DATE):
        total_spend = daily_channel_spend(d, "dv360", week_starts, multiplier_by_week, channel_share_by_week, rng)
        for objective, share in DV360_OBJECTIVE_SPEND_SHARE.items():
            lis = by_objective.get(objective)
            if lis is None or len(lis) == 0:
                continue
            objective_spend = total_spend * share
            weights = rng.uniform(0.8, 1.2, size=len(lis))
            weights = weights / weights.sum()
            for (_, li), weight in zip(lis.iterrows(), weights):
                if rng.random() < AD_PAUSE_DAY_RATE:
                    continue
                rows.extend(_fragment_across_exchanges(rng, li, d, objective_spend * weight, objective))

    df = pd.DataFrame(rows).sort_values(["date", "line_item_id", "exchange", "environment"]).reset_index(drop=True)
    return df


def _fragment_across_exchanges(rng, li, d, line_item_spend, objective):
    is_video = li["line_item_type"] == "LINE_ITEM_TYPE_VIDEO_DEFAULT"
    envs = DV360_ENVIRONMENTS_VIDEO if is_video else DV360_ENVIRONMENTS_DISPLAY
    env_weights = DV360_ENVIRONMENTS_VIDEO_WEIGHTS if is_video else DV360_ENVIRONMENTS_DISPLAY_WEIGHTS

    lo, hi = DV360_EXCHANGE_ENV_COMBOS_PER_DAY_RANGE
    n_combos = int(rng.integers(lo, hi + 1))
    exchanges_drawn = rng.choice(DV360_EXCHANGES, size=n_combos, p=DV360_EXCHANGE_WEIGHTS, replace=True)
    envs_drawn = rng.choice(envs, size=n_combos, p=env_weights, replace=True)
    combos = list(set(zip(exchanges_drawn, envs_drawn)))  # dedupe same-day repeats of the same combo

    combo_weights = rng.uniform(0.6, 1.4, size=len(combos))
    combo_weights = combo_weights / combo_weights.sum()

    cpm_lo, cpm_hi = DV360_CPM_RANGE_BY_OBJECTIVE[objective]
    ctr_lo, ctr_hi = DV360_CTR_RANGE_BY_OBJECTIVE[objective]
    conv_rate = DV360_CONVERSION_RATE_BY_OBJECTIVE[objective]
    value_lo, value_hi = DV360_AVG_CONVERSION_VALUE_RANGE

    out = []
    for (exchange, environment), weight in zip(combos, combo_weights):
        spend = line_item_spend * weight
        cpm = rng.uniform(cpm_lo, cpm_hi) * (1.15 if environment == "CONNECTED_TV" else 1.0)  # CTV inventory runs pricier
        ctr = rng.uniform(ctr_lo, ctr_hi)

        impressions = max(1, int(round(spend / cpm * 1000)))
        clicks = max(0, int(round(impressions * ctr)))
        cost_micros = int(round(spend * 1_000_000))

        conversions = round(clicks * conv_rate * rng.uniform(0.7, 1.3), 2)
        conversions_value = round(conversions * rng.uniform(value_lo, value_hi), 2)

        out.append({
            "line_item_id": li["line_item_id"], "insertion_order_id": li["insertion_order_id"],
            "date": d.isoformat(), "exchange": exchange, "environment": environment,
            "impressions": impressions, "clicks": clicks, "cost_micros": cost_micros,
            "cpm_micros": int(round(cost_micros / impressions * 1000)),
            "ctr": round(clicks / impressions, 6),
            "conversions": conversions, "conversions_value": conversions_value,
        })
    return out


if __name__ == "__main__":
    df = build_dv360_performance_daily()
    df.to_csv("../data/dv360_performance_daily.csv", index=False)
    print(f"Wrote {len(df)} dv360_performance_daily rows\n")
    print(f"Total cost: ${df['cost_micros'].sum() / 1_000_000:,.2f}")
    print(f"Total impressions: {df['impressions'].sum():,}")
    print(f"Total conversions: {df['conversions'].sum():,.1f}")
    print(df["exchange"].value_counts())
    print(df["environment"].value_counts())
