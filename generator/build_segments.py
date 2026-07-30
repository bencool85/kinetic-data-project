"""
Phase 1 - segments table: DEFINITIONS only (membership comes in Phase 4, via
customer_segment_membership, computed from real behavior -- not invented
independently). Two grains distinguished by audience_grain:
- 'customer': behavioral segments maintained by an internal system
  (source_system populated, ad_platform/platform_audience_id null).
- 'anonymous_device': ad-platform custom/retargeting audiences
  (ad_platform + platform_audience_id populated, source_system null). Each
  paid-media platform's ad-set-level table (built in Phase 7) will get a
  nullable targeting_segment_id -> segments.segment_id pointing at these.

Small, curated list per the agreed scope: 8 customer-grain + 3
anonymous-grain (grew from the originally-agreed 7 customer-grain by one,
after catching that "lapsed but still buying courses/merch" -- a real,
explicitly-modeled population in the simulation -- didn't cleanly fit any of
the original 7; see the "Lapsed - Still Buying" segment below). The
"Lookalike - Recent Converters" audience's created_at is
deliberately later than the others -- a lookalike/similar-audience algorithm
needs an existing seed audience of real converters to build from, so it
couldn't have existed since day 1. Computed directly from the simulation: the
50th conversion lands ~429 days after START_DATE, so the audience is dated
~2 weeks after that (time to actually build and upload it).

Output: data/segments.csv
"""
import datetime
import json
import pandas as pd

from params import START_DATE

CUSTOMER_SEGMENTS = [
    # Lifecycle-stage segments (time-based, mutually exclusive across the
    # lapsed population -- deliberately behavior-agnostic: whether someone is
    # still buying courses/merch after lapsing is a separate, overlapping tag
    # below, not baked into the time bucket itself).
    ("Active Subscriber", "Customer currently has an open (non-lapsed) subscription interval."),
    ("Lapsed 0-30 Days", "Subscription canceled within the last 30 days."),
    ("Lapsed 31-90 Days", "Subscription canceled 31-90 days ago."),
    ("Lapsed 90+ Days", "Subscription canceled more than 90 days ago."),
    ("Course/Merch-Only (Never Subscribed)", "Never started a subscription trial; purchase history is course and/or merch only."),
    ("Trial In Progress", "Currently within an active (unresolved) subscription trial period."),
    ("High-LTV Customer", "Lifetime order + subscription revenue in the top decile of the customer base."),
    # Behavioral overlay: can co-occur with ANY of the three lapsed buckets
    # above (a customer lapsed 12 days ago and one lapsed 400 days ago can
    # both carry this tag if either is still buying a la carte). This is the
    # win-back-worthy population -- churned the subscription but still
    # engaged with the brand -- as distinct from the fully-quiet majority.
    ("Lapsed - Still Buying (Courses/Merch)", "Subscription has lapsed (any duration), but the customer has placed at least one course or merch order since their subscription ended."),
]

# (segment_name, description, ad_platform, created_at)
ANONYMOUS_SEGMENTS = [
    ("Website Visitors - Last 30 Days", "Anonymous devices with a tracked site visit in the trailing 30 days.",
     "google_search", START_DATE + datetime.timedelta(days=30)),
    ("Cart Abandoners", "Anonymous devices that began checkout without completing a purchase.",
     "meta", START_DATE + datetime.timedelta(days=30)),
    ("Lookalike - Recent Converters", "Ad-platform lookalike/similar audience modeled on recently converted subscribers.",
     "tiktok", datetime.date(2024, 10, 17)),  # ~2 weeks after the 50th real conversion in the simulation
]


def _fake_platform_audience_id(platform, i):
    # Shapes loosely mimic what each platform actually returns for a custom-audience id.
    if platform == "meta":
        return str(23_850_000_000_000_000 + i)          # Meta: large numeric object id
    if platform == "google_search":
        return str(800_000_000_000 + i)                  # Google Ads: numeric UserList id
    if platform == "tiktok":
        return str(7_100_000_000_000_000_000 + i)        # TikTok: long numeric audience id
    return str(100000 + i)


def build_segments():
    rows = []
    seg_num = 0

    for name, description in CUSTOMER_SEGMENTS:
        seg_num += 1
        rows.append({
            "segment_id": f"seg_{seg_num:03d}",
            "segment_name": name,
            "audience_grain": "customer",
            "description": description,
            "source_system": "internal_crm",
            "ad_platform": None,
            "platform_audience_id": None,
            "created_at": START_DATE.isoformat(),
            "is_active": True,
        })

    for name, description, platform, created_at in ANONYMOUS_SEGMENTS:
        seg_num += 1
        rows.append({
            "segment_id": f"seg_{seg_num:03d}",
            "segment_name": name,
            "audience_grain": "anonymous_device",
            "description": description,
            "source_system": None,
            "ad_platform": platform,
            "platform_audience_id": _fake_platform_audience_id(platform, seg_num),
            "created_at": created_at.isoformat(),
            "is_active": True,
        })

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = build_segments()
    df.to_csv("../data/segments.csv", index=False)
    print(f"Wrote {len(df)} segments\n")
    print(df.to_string(index=False))
