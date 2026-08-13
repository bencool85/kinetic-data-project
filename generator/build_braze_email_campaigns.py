"""
Phase 6 - braze_email_campaigns table (1 of 4). Built first within the
phase, same reason discount_codes came first in Phase 3: braze_email_events
(table 2 of 4) needs real campaign definitions to send against.

A small, hand-curated list (like discount_codes/segments/subscription_plans
were) -- these are marketing-team decisions, not simulated behavior. Two
kinds of campaigns:

- **Triggered** (campaign_type='triggered'): fired off a real event already
  sitting in an earlier phase's shipped tables. `trigger_event` names which
  one -- braze_email_events.py (table 2 of 4) will derive its actual send
  volume from that real source (trial starts in subscriptions.csv, payment
  failures in subscription_events.csv, orders in orders.csv, cart
  abandonment in web_events.csv, and so on), not invent recipients
  independently.
- **Broadcast** (campaign_type='broadcast'): sent to a broad opted-in
  audience on a calendar schedule, not tied to one customer's individual
  behavior. The two seasonal promos here are deliberately timed to
  discount_codes.csv's own HOLIDAY2024/JANRESET10_2025/JANRESET10_2026
  valid windows -- these are the campaigns that would realistically be
  promoting those exact codes.

Output: data/braze_email_campaigns.csv
"""
import pandas as pd

from params import START_DATE

# (campaign_name, campaign_type, trigger_event, description)
CAMPAIGNS = [
    ("Trial Welcome Series", "triggered", "trial_started",
     "Fires when a subscription trial begins (direct signup or merch-to-subscriber pathway)."),
    ("Trial Ending Reminder", "triggered", "trial_ending",
     "Fires ~2 days before a trial's scheduled end, prompting conversion."),
    ("Payment Failed - Update Card", "triggered", "payment_failed",
     "Dunning email fired on every subscription_events.csv payment_failed event."),
    ("Win-Back Lapsed Subscriber", "triggered", "reactivation",
     "Fires for win-back reactivations whose true channel (in the master timeline) is email."),
    ("Merch to Subscriber Offer", "triggered", "merch_to_sub_trigger",
     "The actual 'come try a membership' send that triggers the merch-to-subscriber pathway's trial start."),
    ("Order Confirmation", "triggered", "order_placed",
     "Fires on every order (known-customer and guest checkout alike)."),
    ("Abandoned Cart Reminder", "triggered", "cart_abandoned",
     "Fires for known-customer sessions with an add_to_cart but no purchase (web_events.csv)."),
    ("Monthly Newsletter", "broadcast", None,
     "Recurring broadcast to email-opted-in customers, sent on the 1st of each month."),
    ("Seasonal Sale Promo", "broadcast", None,
     "Broadcast timed to discount_codes.csv's HOLIDAY2024/JANRESET10_2025/JANRESET10_2026 windows."),
]


def build_braze_email_campaigns():
    rows = []
    for i, (name, ctype, trigger, description) in enumerate(CAMPAIGNS, start=1):
        rows.append({
            "campaign_id": f"camp_email_{i:03d}",
            "campaign_name": name,
            "campaign_type": ctype,
            "trigger_event": trigger,
            "description": description,
            "created_at": START_DATE.isoformat(),
            "is_active": True,
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = build_braze_email_campaigns()
    df.to_csv("../data/braze_email_campaigns.csv", index=False)
    print(f"Wrote {len(df)} braze_email_campaigns\n")
    print(df.to_string(index=False))
