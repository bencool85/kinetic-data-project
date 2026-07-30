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

    # --- 5. Distributional sanity ---
    check("Distributional", "10 total segments: 7 customer-grain, 3 anonymous_device-grain, as designed",
          len(segments) == 10 and len(customer_rows) == 7 and len(anon_rows) == 3)

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
