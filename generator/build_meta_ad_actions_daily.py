"""
Phase 7 - meta_ad_actions_daily table (4 of 4, completes Meta). Meta's
Insights API returns a normalized `actions` array per ad/day (one
action_type + value pair per element) -- this table ships that array
flattened to one row per (ad_id, date, action_type), per
schema_reference.md.

Deliberately DERIVED FROM meta_ad_insights_daily.csv's own clicks/
impressions columns (not independently redrawn) -- same "derive from an
already-shipped upstream table" pattern app_events.py used for
streak_achieved off app_sessions.csv. This guarantees the funnel is
internally consistent by construction: link_click can never exceed that
same ad/day's own insights row clicks, and the click-driven funnel
(landing_page_view -> add_to_cart -> initiate_checkout -> purchase) is
monotonically non-increasing because each stage is defined as a fraction
of the previous one.

'purchase' here is Meta's OWN self-attributed pixel/conversions-API count
-- NOT reconciled against orders.csv (schema_reference.md: no user-level
joins from ad platforms to our own data). Real ad platforms' self-reported
conversion counts routinely diverge from site-side order counts (different
attribution windows, click vs. view-through credit, etc.) -- that
divergence is realistic messiness, checked only for plausible order-of-
magnitude in the validator, not exact reconciliation.

video_view is a separate, funnel-independent action (not derived from
clicks) -- only emitted for the video-forward objectives (prospecting,
brand_lift), same as Meta only reports video metrics on ads actually
running video creative.

Output: data/meta_ad_actions_daily.csv
"""
import numpy as np
import pandas as pd

from params import SEED, META_ACTION_FUNNEL_BY_OBJECTIVE, META_VIDEO_VIEW_RATE_BY_OBJECTIVE


def build_meta_ad_actions_daily(seed=SEED + 31):
    rng = np.random.default_rng(seed)
    insights = pd.read_csv("../data/meta_ad_insights_daily.csv")
    campaigns = pd.read_csv("../data/meta_campaigns.csv")
    insights = insights.merge(campaigns[["campaign_id", "ad_objective"]], on="campaign_id")

    rows = []
    for row in insights.itertuples():
        rates = META_ACTION_FUNNEL_BY_OBJECTIVE[row.ad_objective]
        link_click = int(round(row.clicks * rates["link_click_rate"]))
        lpv = int(round(link_click * rates["to_lpv"]))
        atc = int(round(lpv * rates["to_atc"]))
        checkout = int(round(atc * rates["to_checkout"]))
        purchase = int(round(checkout * rates["to_purchase"]))

        for action_type, value in [
            ("link_click", link_click), ("landing_page_view", lpv), ("add_to_cart", atc),
            ("initiate_checkout", checkout), ("purchase", purchase),
        ]:
            rows.append({"ad_id": row.ad_id, "campaign_id": row.campaign_id, "date": row.date,
                         "action_type": action_type, "value": value})

        video_rate = META_VIDEO_VIEW_RATE_BY_OBJECTIVE.get(row.ad_objective)
        if video_rate is not None:
            video_views = int(round(row.impressions * video_rate * rng.uniform(0.85, 1.15)))
            rows.append({"ad_id": row.ad_id, "campaign_id": row.campaign_id, "date": row.date,
                         "action_type": "video_view", "value": video_views})

    df = pd.DataFrame(rows)
    df = df[df["value"] > 0].reset_index(drop=True)  # Meta's actions array omits zero-count action types entirely
    return df


if __name__ == "__main__":
    df = build_meta_ad_actions_daily()
    df.to_csv("../data/meta_ad_actions_daily.csv", index=False)
    print(f"Wrote {len(df)} meta_ad_actions_daily rows\n")
    print(df.groupby("action_type")["value"].sum().sort_values(ascending=False))
