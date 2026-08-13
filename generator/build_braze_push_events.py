"""
Phase 6 - braze_push_events table (4 of 4, completes Phase 6). Same
dot-path event_type naming as braze_email_events, under the
users.messages.pushnotification namespace, and device_id/platform in place
of email_address, per schema_reference.md.

Every triggered send is gated on `push_opt_in == True` -- unlike email,
where a transactional message can always be delivered to an address on
file, push requires the OS-level permission grant; a customer who never
granted it categorically cannot receive one, so it's not just a marketing
preference filter here, it's a delivery precondition. Populations mirror
braze_push_campaigns.csv's own trigger_event vocabulary and reuse the same
real sources braze_email_events.py already established:

- trial_ending / payment_failed: same subscriptions.csv/subscription_events.csv
  populations as the email versions, gated on push_opt_in.
- reactivation: the master timeline's own reactivations list, filtered to
  channel == "push" this time (not "email").
- streak_achieved: every row in app_events.csv's own streak_achieved
  events, gated on push_opt_in -- ties this table directly to Phase 5.
- order_placed: known-customer orders ONLY (guests have no device to push
  to), gated on push_opt_in.

Plus 2 broadcasts: New Class Launch (6 fixed calendar dates) and Weekly
Motivation Push (bi-weekly cadence, but only a random 40% sample of the
eligible list per send -- realistic frequency capping/rotation, since no
real push provider blasts its entire opted-in base every two weeks
forever).

Every send is pinned to the customer's PRIMARY device (devices.csv's first
row per customer_id, same convention app_sessions.csv already established),
and `platform` mirrors that device's own device_type.

Output: data/braze_push_events.csv
"""
import datetime
import json
import numpy as np
import pandas as pd

from params import SEED, START_DATE, END_DATE
from build_customers import customer_id_for

TRIGGERED_RATES = {"bounce": 0.030, "open": 0.35, "click_given_open": 0.20, "unsub_given_open": 0.008}
BROADCAST_RATES = {"bounce": 0.030, "open": 0.18, "click_given_open": 0.10, "unsub_given_open": 0.020}

TRIAL_ENDING_LEAD_DAYS = 2
WEEKLY_PUSH_SAMPLE_RATE = 0.40
NEW_CLASS_LAUNCH_DATES = [
    datetime.date(2023, 11, 10), datetime.date(2024, 3, 15), datetime.date(2024, 8, 20),
    datetime.date(2025, 1, 20), datetime.date(2025, 6, 10), datetime.date(2026, 2, 5),
]


def _random_time_of_day(rng):
    return datetime.time(int(rng.integers(7, 22)), int(rng.integers(0, 60)))


def _funnel(rng, send_at, rates):
    events = [("users.messages.pushnotification.Send", send_at)]
    if rng.random() < rates["bounce"]:
        events.append(("users.messages.pushnotification.Bounce",
                        send_at + datetime.timedelta(minutes=int(rng.integers(1, 15)))))
        return events
    if rng.random() < rates["open"]:
        open_at = send_at + datetime.timedelta(minutes=int(rng.integers(1, 720)))
        events.append(("users.messages.pushnotification.Open", open_at))
        if rng.random() < rates["click_given_open"]:
            click_at = open_at + datetime.timedelta(seconds=int(rng.integers(1, 120)))
            events.append(("users.messages.pushnotification.Click", click_at))
        if rng.random() < rates["unsub_given_open"]:
            unsub_at = open_at + datetime.timedelta(seconds=int(rng.integers(5, 600)))
            events.append(("users.messages.pushnotification.Unsubscribe", unsub_at))
    return events


def build_braze_push_events(seed=SEED + 20):
    rng = np.random.default_rng(seed)
    campaigns = pd.read_csv("../data/braze_push_campaigns.csv").set_index("trigger_event")["campaign_id"]
    broadcast_campaigns = pd.read_csv("../data/braze_push_campaigns.csv")
    broadcast_campaigns = broadcast_campaigns[broadcast_campaigns["campaign_type"] == "broadcast"]

    customers = pd.read_csv("../data/customers.csv")
    non_deleted = customers[~customers["is_deleted"]].copy()
    non_deleted["created_at"] = pd.to_datetime(non_deleted["created_at"])
    non_deleted_ids = set(non_deleted["customer_id"])
    push_opt_in_ids = set(non_deleted.loc[non_deleted["push_opt_in"], "customer_id"])

    devices = pd.read_csv("../data/devices.csv")
    primary_device = (
        devices.dropna(subset=["customer_id"]).sort_values("device_id")
        .groupby("customer_id").first()[["device_id", "device_type"]]
    )

    subs = pd.read_csv("../data/subscriptions.csv")
    subs = subs[subs["customer_id"].isin(push_opt_in_ids)]
    sub_events = pd.read_csv("../data/subscription_events.csv").drop_duplicates(
        subset=["subscription_id", "event_type", "event_at"])
    orders = pd.read_csv("../data/orders.csv")
    app_events = pd.read_csv("../data/app_events.csv")
    timeline = json.load(open("../internal/_sim_customer_timeline.json"))

    sends = []  # (campaign_id, customer_id, send_at, campaign_type)

    def add_send(trigger_event, cid, send_at):
        if cid not in push_opt_in_ids or cid not in primary_device.index:
            return
        if send_at.date() > END_DATE:
            return
        sends.append((campaigns[trigger_event], cid, send_at, "triggered"))

    # --- trial_ending ---
    trial_rows = subs[subs["trial_start"].notna()]
    for row in trial_rows.itertuples():
        trial_end = datetime.date.fromisoformat(row.trial_end)
        reminder_date = trial_end - datetime.timedelta(days=TRIAL_ENDING_LEAD_DAYS)
        if reminder_date >= datetime.date.fromisoformat(row.trial_start):
            add_send("trial_ending", row.customer_id, datetime.datetime.combine(reminder_date, _random_time_of_day(rng)))

    # --- payment_failed ---
    payment_failed = sub_events[(sub_events["event_type"] == "payment_failed")
                                 & sub_events["customer_id"].isin(push_opt_in_ids)]
    for row in payment_failed.itertuples():
        sent_at = pd.Timestamp(row.event_at).to_pydatetime() + datetime.timedelta(minutes=int(rng.integers(1, 60)))
        add_send("payment_failed", row.customer_id, sent_at)

    # --- reactivation (push channel only) ---
    for t in timeline:
        cid = customer_id_for(t["customer_id"])
        if cid not in non_deleted_ids:
            continue
        for react in t["reactivations"]:
            if react["channel"] != "push":
                continue
            lead = int(rng.integers(1, 4))
            send_date = datetime.date.fromisoformat(react["reactivated_at"]) - datetime.timedelta(days=lead)
            add_send("reactivation", cid, datetime.datetime.combine(send_date, _random_time_of_day(rng)))

    # --- streak_achieved ---
    streaks = app_events[app_events["event_type"] == "streak_achieved"]
    for row in streaks.itertuples():
        streak_at = pd.Timestamp(row.occurred_at).to_pydatetime() + datetime.timedelta(minutes=int(rng.integers(1, 30)))
        add_send("streak_achieved", row.customer_id, streak_at)

    # --- order_placed (known customers only) ---
    known_orders = orders[orders["customer_id"].notna()]
    for row in known_orders.itertuples():
        add_send("order_placed", row.customer_id, datetime.datetime.fromisoformat(row.created_at))

    # --- Broadcast: New Class Launch ---
    new_class_id = broadcast_campaigns.loc[broadcast_campaigns["campaign_name"] == "New Class Launch", "campaign_id"].iloc[0]
    for send_date in NEW_CLASS_LAUNCH_DATES:
        if send_date > END_DATE:
            continue
        eligible = non_deleted[(non_deleted["created_at"].dt.date <= send_date)
                                & non_deleted["customer_id"].isin(push_opt_in_ids)
                                & non_deleted["customer_id"].isin(primary_device.index)]
        base = datetime.datetime.combine(send_date, datetime.time(10, 0))
        for row in eligible.itertuples():
            send_at = base + datetime.timedelta(minutes=int(rng.integers(0, 480)))
            sends.append((new_class_id, row.customer_id, send_at, "broadcast"))

    # --- Broadcast: Weekly Motivation Push (bi-weekly, 40% sample per send) ---
    weekly_id = broadcast_campaigns.loc[broadcast_campaigns["campaign_name"] == "Weekly Motivation Push", "campaign_id"].iloc[0]
    send_date = START_DATE + datetime.timedelta(days=(7 - START_DATE.weekday()) % 7)  # first Monday
    while send_date <= END_DATE:
        eligible = non_deleted[(non_deleted["created_at"].dt.date <= send_date)
                                & non_deleted["customer_id"].isin(push_opt_in_ids)
                                & non_deleted["customer_id"].isin(primary_device.index)]
        if len(eligible) > 0:
            sample = eligible.sample(frac=WEEKLY_PUSH_SAMPLE_RATE, random_state=int(rng.integers(0, 2**31)))
            base = datetime.datetime.combine(send_date, datetime.time(8, 0))
            for row in sample.itertuples():
                send_at = base + datetime.timedelta(minutes=int(rng.integers(0, 720)))
                sends.append((weekly_id, row.customer_id, send_at, "broadcast"))
        send_date += datetime.timedelta(days=14)

    # --- Resolve every send through the funnel ---
    rows = []
    for i, (campaign_id, cid, send_at, campaign_type) in enumerate(sends, start=1):
        send_id = f"braze_push_send_{i:07d}"
        device_row = primary_device.loc[cid]
        rates = TRIGGERED_RATES if campaign_type == "triggered" else BROADCAST_RATES
        for event_type, occurred_at in _funnel(rng, send_at, rates):
            rows.append({
                "send_id": send_id,
                "campaign_id": campaign_id,
                "external_user_id": cid,
                "device_id": device_row["device_id"],
                "platform": device_row["device_type"],
                "event_type": event_type,
                "occurred_at": occurred_at,
            })

    df = pd.DataFrame(rows).sort_values("occurred_at").reset_index(drop=True)
    df.insert(0, "event_id", [f"braze_push_evt_{i:07d}" for i in range(1, len(df) + 1)])
    df["occurred_at"] = df["occurred_at"].apply(lambda d: pd.Timestamp(d).isoformat())
    return df


if __name__ == "__main__":
    df = build_braze_push_events()
    df.to_csv("../data/braze_push_events.csv", index=False)
    print(f"Wrote {len(df)} braze_push_events\n")
    print(df["event_type"].value_counts().to_string())
    print(f"\nSend count: {(df['event_type'] == 'users.messages.pushnotification.Send').sum()}")
