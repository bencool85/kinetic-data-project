"""
Validation for `segments` (Phase 1, table 8 of 47 -- the final Phase 1 table)
-- pandas-based, same 5-layer approach (see validate_products.py's docstring
for why pandas instead of DuckDB).

This table only defines segments (no membership yet -- that's Phase 4), so
most checks are structural/business-rule around the grain split itself. One
real cross-check against the simulation: the "Lookalike - Recent Converters"
audience can't predate having a real seed audience of converters to model it
on, so its created_at must fall after a meaningful number of conversions
already exist in the master timeline.
"""
import datetime
import json
import pandas as pd

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    segments = pd.read_csv("../data/segments.csv")
    timeline = json.load(open("../internal/_sim_customer_timeline.json"))

    # --- 1. Structural ---
    check("Structural", "segment_id non-null and unique",
          segments["segment_id"].notna().all() and segments["segment_id"].is_unique)
    check("Structural", "segment_name non-null and unique",
          segments["segment_name"].notna().all() and segments["segment_name"].is_unique)
    check("Structural", "audience_grain in {customer, anonymous_device}",
          segments["audience_grain"].isin(["customer", "anonymous_device"]).all())
    check("Structural", "description non-null", segments["description"].notna().all())
    check("Structural", "created_at parses as a valid date", pd.to_datetime(segments["created_at"], errors="coerce").notna().all())
    check("Structural", "is_active is boolean", segments["is_active"].isin([True, False]).all())

    # --- 2. Referential integrity ---
    # No outward FKs yet -- ad_platform here is a literal channel name, not a
    # foreign key into a not-yet-built ad-platform table (Phase 7 will add
    # targeting_segment_id FKs pointing the other direction, into this table).
    check("Referential", "no outward FKs from segments at this phase (n/a by design)", True)

    # --- 3. Temporal ordering ---
    check("Temporal", "no segment's created_at is before the dataset's START_DATE",
          (pd.to_datetime(segments["created_at"]) >= pd.Timestamp(datetime.date(2023, 8, 1))).all())

    conversions = sorted(datetime.date.fromisoformat(t["trial"]["end"]) for t in timeline
                          if t["trial"] and t["trial"]["outcome"] == "converted")
    lookalike_created = pd.to_datetime(
        segments.loc[segments["segment_name"] == "Lookalike - Recent Converters", "created_at"].iloc[0]).date()
    seed_size_at_creation = sum(1 for d in conversions if d <= lookalike_created)
    check("Temporal", "the Lookalike audience's created_at falls after a real seed audience of >=50 converters already exists in the simulation",
          seed_size_at_creation >= 50, f"{seed_size_at_creation} converters existed by {lookalike_created}")

    churns = sorted(datetime.date.fromisoformat(t["churn_date"]) for t in timeline if t["churn_date"])
    churn_risk_created = pd.to_datetime(
        segments.loc[segments["segment_name"].str.startswith("High Churn Risk"), "created_at"].iloc[0]).date()
    churns_by_creation = sum(1 for d in churns if d <= churn_risk_created)
    check("Temporal", "the 'High Churn Risk' model's created_at falls after >=20 real churns already exist to model against",
          churns_by_creation >= 20, f"{churns_by_creation} churns existed by {churn_risk_created}")

    # --- 4. Business-rule invariants ---
    customer_rows = segments[segments["audience_grain"] == "customer"]
    anon_rows = segments[segments["audience_grain"] == "anonymous_device"]
    check("Business rule", "every customer-grain row has source_system populated and ad_platform/platform_audience_id null",
          customer_rows["source_system"].notna().all()
          and customer_rows["ad_platform"].isna().all()
          and customer_rows["platform_audience_id"].isna().all())
    check("Business rule", "every anonymous_device-grain row has ad_platform + platform_audience_id populated and source_system null",
          anon_rows["ad_platform"].notna().all()
          and anon_rows["platform_audience_id"].notna().all()
          and anon_rows["source_system"].isna().all())
    check("Business rule", "platform_audience_id is unique across anonymous segments (no two audiences share an id)",
          not anon_rows["platform_audience_id"].duplicated().any())
    check("Business rule", "every ad_platform value is one of the project's 6 paid-media platforms",
          anon_rows["ad_platform"].isin(["meta", "google_search", "youtube", "dv360", "snap", "tiktok"]).all())

    still_buying_lapsed = 0
    for t in timeline:
        if t["churn_date"] is None:
            continue
        churn_dt = datetime.date.fromisoformat(t["churn_date"])
        if any(datetime.date.fromisoformat(o["date"]) > churn_dt for o in t["order_events"]):
            still_buying_lapsed += 1
    check("Business rule", "the 'Lapsed - Still Buying' segment isn't vacuous -- real customers in the simulation actually match it "
                            "(lapsed AND has an order after their churn date)",
          still_buying_lapsed > 0, f"{still_buying_lapsed} matching customers in the timeline")

    # "High Churn Risk" has two conditions; only the engagement half is
    # checkable against today's data (billing_interval/next-renewal-date
    # doesn't exist until Phase 2). Confirm that half isn't vacuous, and
    # confirm the segment's own description is honest that it's incomplete.
    active_regular_tier = sum(
        1 for t in timeline
        if any(iv["end"] is None for iv in t["subscription_intervals"]) and t["engagement_tier"] == "regular"
    )
    check("Business rule", "the 'High Churn Risk' segment's low-engagement half (active + engagement_tier='regular') isn't vacuous",
          active_regular_tier > 0, f"{active_regular_tier} currently-active 'regular'-tier subscribers in the timeline")
    churn_risk_desc = segments.loc[segments["segment_name"].str.startswith("High Churn Risk"), "description"].iloc[0]
    check("Business rule", "'High Churn Risk' segment's description explicitly flags its Phase 2/5 dependency (so it isn't silently treated as fully computable today)",
          "Phase 2" in churn_risk_desc)
    check("Business rule", "'High Churn Risk' segment uses a distinct source_system ('churn_propensity_model') from the plain rule-based segments",
          segments.loc[segments["segment_name"].str.startswith("High Churn Risk"), "source_system"].iloc[0] == "churn_propensity_model")
    check("Business rule", "no lapsed-time-bucket segment's description re-bakes a purchase-activity condition into a time bucket "
                            "(that's what caused the original gap -- must stay purely time-based)",
          not any(kw in customer_rows.loc[customer_rows["segment_name"].str.startswith("Lapsed") &
                                           ~customer_rows["segment_name"].str.contains("Still Buying"), "description"]
                  .str.cat(sep=" ").lower() for kw in ["no purchase", "quiet", "still buying"]))

    # --- 5. Distributional sanity ---
    check("Distributional", "12 total segments: 9 customer-grain, 3 anonymous_device-grain, as designed",
          len(segments) == 12 and len(customer_rows) == 9 and len(anon_rows) == 3)

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
