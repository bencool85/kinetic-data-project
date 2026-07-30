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

Small, curated list per the agreed scope: 9 customer-grain + 3
anonymous-grain (grew from the originally-agreed 7 customer-grain by two --
see the "Lapsed - Still Buying" and "High Churn Risk" segments below, each
added to fix or fill a real gap rather than force-fit into the original 7).
The "Lookalike - Recent Converters" audience's created_at is deliberately
later than the others -- a lookalike/similar-audience algorithm needs an
existing seed audience of real converters to build from, so it couldn't have
existed since day 1. Computed directly from the simulation: the 50th
conversion lands ~429 days after START_DATE, so the audience is dated ~2
weeks after that (time to actually build and upload it). Same logic applies
to "High Churn Risk" (needs a real base of observed churns to model against).

Output: data/segments.csv
"""
import datetime
import json
import pandas as pd

from params import START_DATE

# (segment_name, description, source_system, created_at)
CUSTOMER_SEGMENTS = [
    # Lifecycle-stage segments (time-based, mutually exclusive across the
    # lapsed population -- deliberately behavior-agnostic: whether someone is
    # still buying courses/merch after lapsing is a separate, overlapping tag
    # below, not baked into the time bucket itself).
    ("Active Subscriber", "Customer currently has an open (non-lapsed) subscription interval.",
     "internal_crm", START_DATE),
    ("Lapsed 0-30 Days", "Subscription canceled within the last 30 days.",
     "internal_crm", START_DATE),
    ("Lapsed 31-90 Days", "Subscription canceled 31-90 days ago.",
     "internal_crm", START_DATE),
    ("Lapsed 90+ Days", "Subscription canceled more than 90 days ago.",
     "internal_crm", START_DATE),
    ("Course/Merch-Only (Never Subscribed)", "Never started a subscription trial; purchase history is course and/or merch only.",
     "internal_crm", START_DATE),
    ("Trial In Progress", "Currently within an active (unresolved) subscription trial period.",
     "internal_crm", START_DATE),
    ("High-LTV Customer", "Lifetime order + subscription revenue in the top decile of the customer base.",
     "internal_crm", START_DATE),
    # Behavioral overlay: can co-occur with ANY of the three lapsed buckets
    # above (a customer lapsed 12 days ago and one lapsed 400 days ago can
    # both carry this tag if either is still buying a la carte). This is the
    # win-back-worthy population -- churned the subscription but still
    # engaged with the brand -- as distinct from the fully-quiet majority.
    ("Lapsed - Still Buying (Courses/Merch)",
     "Subscription has lapsed (any duration), but the customer has placed at least one course or merch order since their subscription ended.",
     "internal_crm", START_DATE),
    # Predictive segment (its own source_system, distinct from the simple
    # rule-based segments above -- this one is a model output, not a plain
    # SQL filter). Two conditions: (1) a renewal/billing decision is coming
    # up -- requires the subscription's billing_interval and a computed
    # next-renewal-date, which don't exist until Phase 2's `subscriptions`
    # table; (2) below-average recent engagement -- for now, proxied by
    # engagement_tier == "regular" (the lower of the only two tiers the
    # simulation currently assigns to *active* subscribers; "casual" is
    # reserved for lapsed/never-subscribed customers, so it can't be used as
    # the active-subscriber low-engagement signal today). Once Phase 5's real
    # app/web usage events exist, that should replace the tier proxy with an
    # actual recency/frequency signal.
    ("High Churn Risk (Renewal Approaching, Low Engagement)",
     "Active subscriber approaching their next renewal/billing decision with below-average recent "
     "product engagement. Flags subscribers at elevated risk of voluntary churn at their next renewal. "
     "NOTE: full computation depends on Phase 2 (subscriptions.billing_interval + next renewal date) and "
     "ideally Phase 5 (real usage-event recency/frequency) -- membership can't be fully computed until then.",
     "churn_propensity_model", datetime.date(2024, 10, 25)),  # ~2 weeks after the 20th real churn in the simulation
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

    for name, description, source_system, created_at in CUSTOMER_SEGMENTS:
        seg_num += 1
        rows.append({
            "segment_id": f"seg_{seg_num:03d}",
            "segment_name": name,
            "audience_grain": "customer",
            "description": description,
            "source_system": source_system,
            "ad_platform": None,
            "platform_audience_id": None,
            "created_at": created_at.isoformat(),
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
