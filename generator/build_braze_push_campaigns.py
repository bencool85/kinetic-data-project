"""
Phase 6 - braze_push_campaigns table (3 of 4). Same "campaigns before
events" build-order reasoning as discount_codes/braze_email_campaigns: the
push events table (4 of 4) needs real campaign definitions to send against.

A push-appropriate subset of triggers, not a blind mirror of every email
campaign -- push is native to different moments than email (streak
celebrations, urgent re-engagement) and doesn't fit others (nobody expects
an abandoned-cart push the way they'd expect that email, and guests have no
device to push to at all, so push has no order_placed-for-guests case the
way email does).

- Triggered: trial_ending (same trigger as email's reminder, sent via a
  second channel), payment_failed (urgent enough to justify both channels),
  reactivation (win-back pushes -- filtered to the master timeline's own
  channel=='push' reactivations in braze_push_events.py; if that population
  happens to be empty in this dataset's specific draw, the campaign still
  exists as a real marketing-team decision, same as any campaign that goes
  quiet for a period), streak_achieved (a natural push moment -- ties
  directly to app_events.csv), and order_placed (KNOWN customers only --
  push has no equivalent to email's guest-checkout case, since a guest has
  no app install/device to push to).
- Broadcast: New Class Launch (occasional, tied to no fixed calendar --
  braze_push_events.py will pick real dates) and Weekly Motivation Push
  (a much higher-cadence broadcast than email's monthly newsletter, which
  is realistic for push -- it's cheap and low-friction compared to email).

Output: data/braze_push_campaigns.csv
"""
import pandas as pd

from params import START_DATE

# (campaign_name, campaign_type, trigger_event, description)
CAMPAIGNS = [
    ("Trial Ending Reminder - Push", "triggered", "trial_ending",
     "Push variant of the email trial-ending reminder, ~2 days before trial_end."),
    ("Payment Failed - Push", "triggered", "payment_failed",
     "Push variant of the dunning email, fired on subscription_events.csv payment_failed events."),
    ("Win-Back Lapsed Subscriber - Push", "triggered", "reactivation",
     "Fires for win-back reactivations whose true channel (in the master timeline) is push."),
    ("Streak Celebration", "triggered", "streak_achieved",
     "Fires on every app_events.csv streak_achieved milestone (3/7/14/30/60/100 days)."),
    ("Order Shipped - Push", "triggered", "order_placed",
     "Push shipping notification for known-customer orders only -- guests have no device to push to."),
    ("New Class Launch", "broadcast", None,
     "Occasional broadcast announcing new course/class content, sent to push-opted-in customers."),
    ("Weekly Motivation Push", "broadcast", None,
     "Higher-cadence broadcast than email's newsletter -- push is cheap and low-friction."),
]


def build_braze_push_campaigns():
    rows = []
    for i, (name, ctype, trigger, description) in enumerate(CAMPAIGNS, start=1):
        rows.append({
            "campaign_id": f"camp_push_{i:03d}",
            "campaign_name": name,
            "campaign_type": ctype,
            "trigger_event": trigger,
            "description": description,
            "created_at": START_DATE.isoformat(),
            "is_active": True,
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = build_braze_push_campaigns()
    df.to_csv("../data/braze_push_campaigns.csv", index=False)
    print(f"Wrote {len(df)} braze_push_campaigns\n")
    print(df.to_string(index=False))
