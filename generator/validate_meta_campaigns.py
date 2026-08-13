"""
Validation for `meta_campaigns` (Phase 7, Meta table 1 of 4) -- pandas-based,
same 5-layer approach used throughout this project. Lightweight
definitions-table validation, same class as braze_email_campaigns.csv --
the real derivation/consistency checks live in the daily tables' validators.
"""
import pandas as pd

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    campaigns = pd.read_csv("../data/meta_campaigns.csv")

    # --- 1. Structural ---
    check("Structural", "campaign_id non-null and unique",
          campaigns["campaign_id"].notna().all() and campaigns["campaign_id"].is_unique)
    check("Structural", "account_id, name, ad_objective, objective, status non-null on every row",
          campaigns[["account_id", "name", "ad_objective", "objective", "status"]].notna().all().all())
    check("Structural", "ad_objective is always one of the 5 shared objectives",
          campaigns["ad_objective"].isin(["prospecting", "retargeting", "lookalike", "conversion", "brand_lift"]).all())
    check("Structural", "status is always a valid Meta campaign status",
          campaigns["status"].isin(["ACTIVE", "PAUSED", "ARCHIVED", "COMPLETED"]).all())
    check("Structural", "objective is always a valid Meta Outcome-objective enum value",
          campaigns["objective"].isin(["OUTCOME_TRAFFIC", "OUTCOME_SALES", "OUTCOME_AWARENESS",
                                        "OUTCOME_ENGAGEMENT", "OUTCOME_LEADS", "OUTCOME_APP_PROMOTION"]).all())
    check("Structural", "exactly one budget field (daily_budget XOR lifetime_budget) is set per row -- "
                       "real Meta campaigns never carry both",
          ((campaigns["daily_budget"].notna()) ^ (campaigns["lifetime_budget"].notna())).all())

    # --- 2. Referential integrity ---
    check("Referential", "n/a -- this is a root definitions table with no FKs of its own", True)

    # --- 3. Temporal ordering ---
    campaigns["start_time"] = pd.to_datetime(campaigns["start_time"])
    campaigns["created_time"] = pd.to_datetime(campaigns["created_time"])
    check("Temporal", "created_time is always at or before start_time (a campaign can't run before it's created)",
          (campaigns["created_time"] <= campaigns["start_time"]).all())
    with_stop = campaigns[campaigns["stop_time"].notna()].copy()
    with_stop["stop_time"] = pd.to_datetime(with_stop["stop_time"])
    check("Temporal", "stop_time (where set) is always after start_time",
          (with_stop["stop_time"] > pd.to_datetime(with_stop["start_time"])).all())

    # --- 4. Business-rule invariants ---
    check("Business rule", "ad_objective values are unique among the 4 evergreen (always-on) campaigns "
                          "(no two evergreen campaigns competing for the same objective)",
          not campaigns.loc[campaigns["ad_objective"] != "brand_lift", "ad_objective"].duplicated().any())
    check("Business rule", "every brand_lift campaign has a lifetime_budget (flighted, not daily-paced)",
          (campaigns.loc[campaigns["ad_objective"] == "brand_lift", "lifetime_budget"].notna()).all())
    check("Business rule", "every non-brand_lift (evergreen) campaign has a daily_budget, "
                          "runs open-ended (no stop_time), and is ACTIVE",
          (campaigns.loc[campaigns["ad_objective"] != "brand_lift", "daily_budget"].notna().all())
          and (campaigns.loc[campaigns["ad_objective"] != "brand_lift", "stop_time"].isna().all())
          and (campaigns.loc[campaigns["ad_objective"] != "brand_lift", "status"] == "ACTIVE").all())

    # --- 5. Distributional sanity ---
    n_evergreen = (campaigns["ad_objective"] != "brand_lift").sum()
    n_brand_lift = (campaigns["ad_objective"] == "brand_lift").sum()
    check("Distributional", "4 evergreen campaigns (one per non-brand_lift objective) + brand_lift flights",
          n_evergreen == 4 and n_brand_lift >= 1, detail=f"{n_evergreen} evergreen / {n_brand_lift} brand_lift")

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
