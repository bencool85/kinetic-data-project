"""
Validation for `subscription_plans` (Phase 1, table 3 of 47) -- pandas-based,
same 5-layer approach (see validate_products.py's docstring for why pandas
instead of DuckDB).

Note on scope: the Phase 0 master timeline only tracks plan *tier* per
interval ("basic"/"plus"), not billing_interval (monthly vs. annual) -- that
distinction doesn't exist yet in the ground truth. So "matches the simulation"
here specifically means every tier value the timeline actually uses has a
real plan of that tier -- it does NOT (yet) mean every interval's
monthly/annual split is derivable from the timeline. Phase 2 (`subscriptions`)
will need to assign billing_interval itself when it builds real interval rows;
flagging this now so it isn't a surprise later.
"""
import datetime
import json
import pandas as pd

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    plans = pd.read_csv("../data/subscription_plans.csv")
    timeline = json.load(open("../internal/_sim_customer_timeline.json"))

    # --- 1. Structural ---
    check("Structural", "plan_id non-null and unique",
          plans["plan_id"].notna().all() and plans["plan_id"].is_unique)
    check("Structural", "tier in {basic, plus}", plans["tier"].isin(["basic", "plus"]).all())
    check("Structural", "billing_interval in {month, year}", plans["billing_interval"].isin(["month", "year"]).all())
    check("Structural", "price > 0", (plans["price"] > 0).all())
    check("Structural", "currency is usd", (plans["currency"] == "usd").all())
    check("Structural", "is_active is boolean", plans["is_active"].isin([True, False]).all())
    check("Structural", "created_at is a valid date", pd.to_datetime(plans["created_at"], errors="coerce").notna().all())
    check("Structural", "(tier, billing_interval) is unique -- no duplicate plans",
          not plans.duplicated(subset=["tier", "billing_interval"]).any())

    # --- 2. Referential integrity ---
    check("Referential", "no outward FKs from subscription_plans (n/a by design)", True)

    # --- 3. Temporal ordering ---
    interval_starts = [datetime.date.fromisoformat(iv["start"])
                        for t in timeline for iv in t["subscription_intervals"]]
    if interval_starts:
        earliest_sub_start = min(interval_starts)
        created_at = pd.to_datetime(plans["created_at"]).min().date()
        check("Temporal", "plans exist (created_at) before the earliest simulated subscription interval",
              created_at <= earliest_sub_start,
              f"created_at={created_at}, earliest sub interval={earliest_sub_start}")

    # --- 4. Business-rule invariants ---
    basic_m = plans.loc[(plans.tier == "basic") & (plans.billing_interval == "month"), "price"].iloc[0]
    basic_y = plans.loc[(plans.tier == "basic") & (plans.billing_interval == "year"), "price"].iloc[0]
    plus_m = plans.loc[(plans.tier == "plus") & (plans.billing_interval == "month"), "price"].iloc[0]
    plus_y = plans.loc[(plans.tier == "plus") & (plans.billing_interval == "year"), "price"].iloc[0]

    check("Business rule", "Basic annual is cheaper than 12x Basic monthly (real discount)", basic_y < basic_m * 12)
    check("Business rule", "Plus annual is cheaper than 12x Plus monthly (real discount)", plus_y < plus_m * 12)
    check("Business rule", "Plus costs more than Basic at the same billing interval (monthly)", plus_m > basic_m)
    check("Business rule", "Plus costs more than Basic at the same billing interval (annual)", plus_y > basic_y)

    basic_discount = 1 - basic_y / (basic_m * 12)
    plus_discount = 1 - plus_y / (plus_m * 12)
    check("Business rule", "Plus annual's discount ratio is close to Basic annual's (consistent pricing logic)",
          abs(basic_discount - plus_discount) < 0.01,
          f"basic discount={basic_discount:.3%}, plus discount={plus_discount:.3%}")

    tiers_in_sim = {iv["plan"] for t in timeline for iv in t["subscription_intervals"]}
    check("Business rule", "every plan tier used in the simulation ('basic'/'plus') has a matching row here",
          tiers_in_sim <= set(plans["tier"]),
          f"unmatched tiers: {tiers_in_sim - set(plans['tier'])}")

    # --- 5. Distributional sanity ---
    check("Distributional", "exactly 4 plans: 2 tiers x 2 billing intervals", len(plans) == 4)
    check("Distributional", "both tiers ('basic', 'plus') present", set(plans["tier"]) == {"basic", "plus"})
    check("Distributional", "both billing intervals ('month', 'year') present",
          set(plans["billing_interval"]) == {"month", "year"})

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
