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

9 customer-grain segments (grew from the originally-agreed 7 by two -- see
the "Lapsed - Still Buying" and "High Churn Risk" segments below, each added
to fix or fill a real gap rather than force-fit into the original 7).

Anonymous-grain segments: Ben's instruction was that every anonymous-grain
audience concept needs a version on every platform capable of receiving a
retargeting pixel -- not just the one platform it happened to be drafted on.
All 6 paid-media platforms in this project's scope (meta, google_search,
youtube, dv360, snap, tiktok) support pixel-based custom/retargeting
audiences, so each of the 3 concepts (Website Visitors - Last 30 Days, Cart
Abandoners, Lookalike - Recent Converters) now gets one row per platform: 3
concepts x 6 platforms = 18 anonymous-grain rows (up from 3). segment_name is
disambiguated per platform (e.g. "Cart Abandoners - Meta", "Cart Abandoners -
Google Search", ...) since segment_name must stay unique. created_at is kept
identical across all 6 platform-versions of a given concept -- simpler, and
there's no real reason the same underlying audience concept would be built on
different platforms at meaningfully different times.

27 total segments: 9 customer-grain + 18 anonymous-grain.

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
    # up -- RESOLVED as of Phase 2's `subscriptions` table, which assigns
    # billing_interval and computes current_period_end (a real, future-dated
    # next-renewal date) for every open subscription; (2) below-average
    # recent engagement -- still proxied by engagement_tier == "regular" (the
    # lower of the only two tiers the simulation currently assigns to
    # *active* subscribers; "casual" is reserved for lapsed/never-subscribed
    # customers, so it can't be used as the active-subscriber low-engagement
    # signal today). Once Phase 5's real app/web usage events exist, that
    # should replace the tier proxy with an actual recency/frequency signal
    # -- this half is still an open dependency, flagged in the description.
    ("High Churn Risk (Renewal Approaching, Low Engagement)",
     "Active subscriber approaching their next renewal/billing decision with below-average recent "
     "product engagement. Flags subscribers at elevated risk of voluntary churn at their next renewal. "
     "Renewal timing is computable today from subscriptions.current_period_end (Phase 2). "
     "NOTE: the engagement half still depends on Phase 5 (real usage-event recency/frequency) -- "
     "until then it's proxied by engagement_tier, so membership can't be fully computed yet.",
     "churn_propensity_model", datetime.date(2024, 10, 25)),  # ~2 weeks after the 20th real churn in the simulation
]

# (concept_name, description, created_at) -- each concept gets one row per
# platform below, across all 6 platforms capable of receiving a retargeting
# pixel.
ANONYMOUS_CONCEPTS = [
    ("Website Visitors - Last 30 Days", "Anonymous devices with a tracked site visit in the trailing 30 days.",
     START_DATE + datetime.timedelta(days=30)),
    ("Cart Abandoners", "Anonymous devices that began checkout without completing a purchase.",
     START_DATE + datetime.timedelta(days=30)),
    ("Lookalike - Recent Converters", "Ad-platform lookalike/similar audience modeled on recently converted subscribers.",
     datetime.date(2024, 10, 17)),  # ~2 weeks after the 50th real conversion in the simulation
]

# Every paid-media platform in scope supports pixel-based custom/retargeting
# audiences, so every concept above is replicated across all 6.
PLATFORMS = ["meta", "google_search", "youtube", "dv360", "snap", "tiktok"]
PLATFORM_LABELS = {
    "meta": "Meta",
    "google_search": "Google Search",
    "youtube": "YouTube",
    "dv360": "DV360",
    "snap": "Snap",
    "tiktok": "TikTok",
}


def _fake_platform_audience_id(platform, i):
    # Shapes loosely mimic what each platform actually returns for a custom-audience id.
    if platform == "meta":
        return str(23_850_000_000_000_000 + i)          # Meta: large numeric object id
    if platform == "google_search":
        return str(800_000_000_000 + i)                  # Google Ads: numeric UserList id
    if platform == "youtube":
        return str(900_000_000_000 + i)                  # YouTube: shares Google Ads infra, distinct UserList id range
    if platform == "dv360":
        return str(5_000_000_000 + i)                     # DV360: numeric audience id, smaller id space than Google Ads
    if platform == "snap":
        return _snap_uuid(i)                              # Snap: UUID-shaped audience segment id
    if platform == "tiktok":
        return str(7_100_000_000_000_000_000 + i)        # TikTok: long numeric audience id
    return str(100000 + i)


def _snap_uuid(i):
    # Deterministic (not uuid.uuid4() -- that's not seed-reproducible), but
    # shaped like a real UUID, since Snap's Marketing API keys audiences by UUID.
    # zfill pads on the LEFT, so i's actual varying digits sit at the END of h --
    # take the last 30 chars (not the first 30) so small values of i don't all
    # collapse to the same mostly-zero id.
    h = format(i, "x").zfill(32)[-30:]
    return f"{h[0:8]}-{h[8:12]}-4{h[12:15]}-a{h[15:18]}-{h[18:30]}"


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

    for concept_name, description, created_at in ANONYMOUS_CONCEPTS:
        for platform in PLATFORMS:
            seg_num += 1
            label = PLATFORM_LABELS[platform]
            rows.append({
                "segment_id": f"seg_{seg_num:03d}",
                "segment_name": f"{concept_name} - {label}",
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
