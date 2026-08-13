"""
Validation for `google_search_keyword_performance_daily` (Phase 7, Google
Search table 4 of 4 by schema order, but the granular ground-truth table
google_search_performance_daily.py aggregates from). Central checks:
internal arithmetic consistency, keyword identity is stable across days
(same keyword_text/match_type every time that keyword_id appears), and
the same cross-phase seasonality/channel-mix correlation check used for
Meta's insights table.
"""
import numpy as np
import pandas as pd

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    kw = pd.read_csv("../data/google_search_keyword_performance_daily.csv")
    ad_groups = pd.read_csv("../data/google_search_ad_groups.csv")
    campaigns = pd.read_csv("../data/google_search_campaigns.csv")
    web_sessions = pd.read_csv("../data/web_sessions.csv")
    orders = pd.read_csv("../data/orders.csv")
    subs = pd.read_csv("../data/subscriptions.csv")

    kw["date"] = pd.to_datetime(kw["date"])

    # --- 1. Structural ---
    required = ["keyword_id", "ad_group_id", "campaign_id", "date", "keyword_text", "match_type",
                "quality_score", "impressions", "clicks", "cost_micros", "ctr", "conversions", "conversions_value"]
    check("Structural", "all required fields non-null (average_cpc_micros nullable only when clicks==0)",
          kw[required].notna().all().all())
    check("Structural", "average_cpc_micros is null IFF clicks == 0",
          (kw["average_cpc_micros"].isna() == (kw["clicks"] == 0)).all())
    check("Structural", "match_type is always a valid Google Ads keyword match type",
          kw["match_type"].isin(["EXACT", "PHRASE", "BROAD"]).all())
    check("Structural", "quality_score is always an integer in Google Ads' 1-10 range",
          kw["quality_score"].between(1, 10).all())
    check("Structural", "impressions, clicks, cost_micros, conversions, conversions_value all non-negative",
          (kw[["impressions", "clicks", "cost_micros", "conversions", "conversions_value"]] >= 0).all().all())
    check("Structural", "(keyword_id, date) is unique -- exactly one row per keyword per day",
          not kw.duplicated(subset=["keyword_id", "date"]).any())

    # --- 2. Referential integrity ---
    check("Referential", "every ad_group_id exists in google_search_ad_groups.csv",
          kw["ad_group_id"].isin(ad_groups["ad_group_id"]).all())
    check("Referential", "every campaign_id on a row matches that ad_group_id's OWN campaign_id",
          kw.merge(ad_groups[["ad_group_id", "campaign_id"]], on="ad_group_id", suffixes=("", "_true"))
          .pipe(lambda d: (d["campaign_id"] == d["campaign_id_true"]).all()))
    check("Referential", "each keyword_id's keyword_text and match_type are IDENTICAL across every day "
                        "it appears (stable keyword identity, not redrawn daily)",
          kw.groupby("keyword_id")[["keyword_text", "match_type"]].nunique().eq(1).all().all())

    # --- 3. Temporal ordering ---
    check("Temporal", "every row's date falls within the [2023-08-01, 2026-07-30] project window",
          (kw["date"] >= pd.Timestamp("2023-08-01")).all() and (kw["date"] <= pd.Timestamp("2026-07-30")).all())

    # --- 4. Business-rule invariants ---
    check("Business rule", "ctr recomputes exactly from clicks/impressions",
          np.isclose(kw["ctr"], kw["clicks"] / kw["impressions"], atol=1e-4).all())
    nz = kw[kw["clicks"] > 0]
    check("Business rule", "average_cpc_micros recomputes exactly from cost_micros/clicks",
          np.isclose(nz["average_cpc_micros"], nz["cost_micros"] / nz["clicks"], atol=1.0).all())
    check("Business rule", "clicks never exceed impressions", (kw["clicks"] <= kw["impressions"]).all())

    # --- 5. Distributional sanity ---
    blended_cpc = kw["cost_micros"].sum() / 1_000_000 / kw["clicks"].sum()
    check("Distributional", "blended CPC lands in a plausible Google Search range ($0.30-$2.50)",
          0.30 <= blended_cpc <= 2.50, detail=f"${blended_cpc:.2f}")
    blended_ctr = kw["clicks"].sum() / kw["impressions"].sum()
    check("Distributional", "blended CTR lands in a plausible Search range (2%-10%, much higher than paid social)",
          0.02 <= blended_ctr <= 0.10, detail=f"{blended_ctr:.2%}")
    total_claimed = kw["conversions"].sum()
    total_real = len(orders) + len(subs[subs["trial_start"].isna() | (subs["start_date"] != subs["trial_start"])])
    ratio = total_claimed / total_real
    check("Distributional", "Google Search's self-attributed 'conversions' total is within a believable "
                          "over-attribution multiple of the business's actual total real purchases (0.2x-3.5x -- "
                          "search intent typically converts/self-attributes higher than social, so a slightly "
                          "wider band than Meta's is appropriate here)",
          0.2 <= ratio <= 3.5, detail=f"{total_claimed:.0f} claimed vs. {total_real} real (ratio {ratio:.2f}x)")

    kw["week_start"] = (kw["date"] - pd.to_timedelta(kw["date"].dt.weekday, unit="D")).dt.date
    weekly_cost = kw.groupby("week_start")["cost_micros"].sum() / 1_000_000
    ws = web_sessions[web_sessions["utm_source"] == "google_search"].copy()
    ws["started_at"] = pd.to_datetime(ws["started_at"])
    ws["week_start"] = (ws["started_at"] - pd.to_timedelta(ws["started_at"].dt.weekday, unit="D")).dt.date
    weekly_sessions = ws.groupby("week_start").size()
    joined = pd.DataFrame({"cost": weekly_cost, "sessions": weekly_sessions}).dropna()
    corr = joined["cost"].corr(joined["sessions"])
    check("Distributional", "weekly Google Search spend correlates positively with web_sessions.csv's own "
                          "google_search-attributed weekly session count (same seasonality calendar + "
                          "channel-mix schedule driving both, no row-level join between them)",
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
