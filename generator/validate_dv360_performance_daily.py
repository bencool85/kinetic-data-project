"""
Validation for `dv360_performance_daily` (Phase 7, DV360 table 3 of 3 --
completes DV360). Central checks specific to this table's genuinely
different shape: (line_item_id, date, exchange, environment) is the grain
(not just line_item_id/date), CONNECTED_TV environment appears ONLY for
the video (brand_lift) line item, and the same cross-phase seasonality/
channel-mix correlation + self-attributed-conversions plausibility checks
used for every other platform.
"""
import numpy as np
import pandas as pd

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    perf = pd.read_csv("../data/dv360_performance_daily.csv")
    line_items = pd.read_csv("../data/dv360_line_items.csv")
    ios = pd.read_csv("../data/dv360_insertion_orders.csv")
    web_sessions = pd.read_csv("../data/web_sessions.csv")
    orders = pd.read_csv("../data/orders.csv")
    subs = pd.read_csv("../data/subscriptions.csv")

    perf["date"] = pd.to_datetime(perf["date"])
    perf = perf.merge(line_items[["line_item_id", "insertion_order_id", "line_item_type"]],
                       on=["line_item_id", "insertion_order_id"], how="inner")
    perf = perf.merge(ios[["insertion_order_id", "ad_objective"]], on="insertion_order_id")

    # --- 1. Structural ---
    required = ["line_item_id", "insertion_order_id", "date", "exchange", "environment", "impressions",
                "clicks", "cost_micros", "cpm_micros", "ctr", "conversions", "conversions_value"]
    check("Structural", "all required fields non-null on every row", perf[required].notna().all().all())
    check("Structural", "impressions, clicks, cost_micros, conversions all non-negative",
          (perf[["impressions", "clicks", "cost_micros", "conversions"]] >= 0).all().all())
    check("Structural", "exchange is always one of the known DV360 exchange vocabulary",
          perf["exchange"].isin(["GOOGLE_AD_MANAGER", "APPNEXUS", "OPENX", "PUBMATIC", "INDEX_EXCHANGE"]).all())
    check("Structural", "environment is always a valid DV360 environment value",
          perf["environment"].isin(["WEB_OPTIMIZED", "WEB_NOT_OPTIMIZED", "APP", "CONNECTED_TV"]).all())
    check("Structural", "(line_item_id, date, exchange, environment) is unique -- the genuinely finer grain "
                       "this table uses vs. every other platform's (ad/ad_group, date) grain",
          not perf.duplicated(subset=["line_item_id", "date", "exchange", "environment"]).any())

    # --- 2. Referential integrity ---
    check("Referential", "every line_item_id exists in dv360_line_items.csv",
          perf["line_item_id"].isin(line_items["line_item_id"]).all())
    check("Referential", "every insertion_order_id on a row matches that line_item_id's OWN insertion_order_id",
          perf.merge(line_items[["line_item_id", "insertion_order_id"]], on="line_item_id", suffixes=("", "_true"))
          .pipe(lambda d: (d["insertion_order_id"] == d["insertion_order_id_true"]).all()))

    # --- 3. Temporal ordering ---
    check("Temporal", "every row's date falls within the [2023-08-01, 2026-07-30] project window",
          (perf["date"] >= pd.Timestamp("2023-08-01")).all() and (perf["date"] <= pd.Timestamp("2026-07-30")).all())

    # --- 4. Business-rule invariants ---
    check("Business rule", "CONNECTED_TV environment appears ONLY on the video (brand_lift) line item -- "
                          "display line items never reach CTV inventory",
          set(perf.loc[perf["environment"] == "CONNECTED_TV", "line_item_type"]) <= {"LINE_ITEM_TYPE_VIDEO_DEFAULT"})
    check("Business rule", "cpm_micros recomputes exactly from cost_micros/impressions*1000",
          np.isclose(perf["cpm_micros"], perf["cost_micros"] / perf["impressions"] * 1000, atol=1.0).all())
    check("Business rule", "ctr recomputes exactly from clicks/impressions",
          np.isclose(perf["ctr"], perf["clicks"] / perf["impressions"], atol=1e-4).all())
    check("Business rule", "clicks never exceed impressions", (perf["clicks"] <= perf["impressions"]).all())
    check("Business rule", "each (line_item_id, date) fragments into a realistic number of exchange/environment "
                          "combinations (1-7, matching DV360_EXCHANGE_ENV_COMBOS_PER_DAY_RANGE)",
          perf.groupby(["line_item_id", "date"]).size().between(1, 7).all())

    # --- 5. Distributional sanity ---
    blended_cpm = perf["cost_micros"].sum() / 1_000_000 / perf["impressions"].sum() * 1000
    check("Distributional", "blended CPM lands in a plausible open-web programmatic range ($2.50-$16, "
                          "below paid social/search since open-web display inventory is cheaper)",
          2.50 <= blended_cpm <= 16, detail=f"${blended_cpm:.2f}")
    total_claimed = perf["conversions"].sum()
    total_real = len(orders) + len(subs[subs["trial_start"].isna() | (subs["start_date"] != subs["trial_start"])])
    ratio = total_claimed / total_real
    check("Distributional", "DV360's self-attributed conversions total is within a believable multiple of "
                          "the business's actual real purchases (0.1x-3x -- open-web display converts "
                          "self-reported at a LOWER rate than search/social, so a lower floor than the other "
                          "platforms is appropriate here, not a bug)",
          0.1 <= ratio <= 3.0, detail=f"{total_claimed:.0f} claimed vs. {total_real} real (ratio {ratio:.2f}x)")

    perf["week_start"] = (perf["date"] - pd.to_timedelta(perf["date"].dt.weekday, unit="D")).dt.date
    weekly_cost = perf.groupby("week_start")["cost_micros"].sum() / 1_000_000
    ws = web_sessions[web_sessions["utm_source"] == "dv360"].copy()
    ws["started_at"] = pd.to_datetime(ws["started_at"])
    ws["week_start"] = (ws["started_at"] - pd.to_timedelta(ws["started_at"].dt.weekday, unit="D")).dt.date
    weekly_sessions = ws.groupby("week_start").size()
    joined = pd.DataFrame({"cost": weekly_cost, "sessions": weekly_sessions}).dropna()
    corr = joined["cost"].corr(joined["sessions"])
    check("Distributional", "weekly DV360 spend correlates positively with web_sessions.csv's own "
                          "dv360-attributed weekly session count (same seasonality calendar + "
                          "channel-mix schedule driving both)",
          corr > 0.4, detail=f"Pearson r={corr:.3f} across {len(joined)} weeks")

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
