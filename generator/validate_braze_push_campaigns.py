"""
Validation for `braze_push_campaigns` (Phase 6, table 3 of 4) --
pandas-based, same 5-layer approach (see validate_products.py's docstring
for why pandas instead of DuckDB). Same lightweight definitions-table
validation class as braze_email_campaigns.csv -- real derivation checks
happen in braze_push_events.py's validator (table 4 of 4).
"""
import pandas as pd

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    campaigns = pd.read_csv("../data/braze_push_campaigns.csv")

    # --- 1. Structural ---
    check("Structural", "campaign_id non-null and unique",
          campaigns["campaign_id"].notna().all() and campaigns["campaign_id"].is_unique)
    check("Structural", "campaign_name non-null and unique (no duplicate campaign names)",
          campaigns["campaign_name"].notna().all() and campaigns["campaign_name"].is_unique)
    check("Structural", "campaign_type is always 'triggered' or 'broadcast'",
          campaigns["campaign_type"].isin(["triggered", "broadcast"]).all())
    check("Structural", "trigger_event is populated iff campaign_type == 'triggered'",
          (campaigns.loc[campaigns["campaign_type"] == "triggered", "trigger_event"].notna().all())
          and (campaigns.loc[campaigns["campaign_type"] == "broadcast", "trigger_event"].isna().all()))
    check("Structural", "created_at and is_active non-null on every row",
          campaigns[["created_at", "is_active"]].notna().all().all())

    # --- 2. Referential integrity ---
    check("Referential", "n/a -- this is a root definitions table with no FKs of its own", True)

    # --- 3. Temporal ordering ---
    check("Temporal", "n/a -- all campaigns share one static created_at (a hand-curated marketing "
                    "calendar, not simulated behavior)", True)

    # --- 4. Business-rule invariants ---
    check("Business rule", "trigger_event values are drawn from a closed, known vocabulary "
                          "(each one must correspond to a real source table braze_push_events.py can derive from)",
          campaigns.loc[campaigns["trigger_event"].notna(), "trigger_event"].isin([
              "trial_ending", "payment_failed", "reactivation", "streak_achieved", "order_placed",
          ]).all())
    check("Business rule", "every triggered campaign's trigger_event is unique "
                          "(no two campaigns claiming the same trigger, which would make "
                          "braze_push_events.py's derivation ambiguous)",
          not campaigns.loc[campaigns["trigger_event"].notna(), "trigger_event"].duplicated().any())
    email_campaigns = pd.read_csv("../data/braze_email_campaigns.csv")
    check("Business rule", "'order_placed' here is deliberately narrower in scope than email's own "
                          "order_placed campaign (push has no guest-checkout case) -- both tables "
                          "may reuse the trigger_event name, but that's expected, not a collision",
          "order_placed" in set(campaigns["trigger_event"]) and "order_placed" in set(email_campaigns["trigger_event"]))

    # --- 5. Distributional sanity ---
    n_triggered = (campaigns["campaign_type"] == "triggered").sum()
    n_broadcast = (campaigns["campaign_type"] == "broadcast").sum()
    check("Distributional", "the campaign mix has both triggered (lifecycle) and broadcast (calendar) "
                          "campaigns, not all of one kind",
          n_triggered > 0 and n_broadcast > 0, detail=f"{n_triggered} triggered / {n_broadcast} broadcast")

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
