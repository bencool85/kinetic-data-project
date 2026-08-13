"""
Phase 6 - braze_email_events table (2 of 4). Dot-path event_type naming per
schema_reference.md: users.messages.email.Send/.Open/.Click/.Bounce/
.Unsubscribe.

Every send in this table traces to a real source already sitting in an
earlier phase's shipped tables -- reusing braze_email_campaigns.csv's own
`trigger_event` vocabulary as the map:

- trial_started / trial_ending: every trial object in subscriptions.csv
  (trial_start notna) -- welcome send at trial_start, reminder ~2 days
  before trial_end.
- payment_failed: every deduped payment_failed row in
  subscription_events.csv (deduped the same way build_invoices.py already
  had to -- a duplicate webhook must not produce two dunning emails).
- reactivation: the master timeline's own `reactivations` list, filtered to
  channel == "email" (the SAME field web_sessions.csv already used for its
  reactivation-day sessions) -- sent a few days before the reactivation
  itself, since the email is what prompts it.
- merch_to_sub_trigger: customers whose first-ever subscription object has
  a real gap between signup (customers.created_at) and trial_start -- the
  exact same population/boundary customer_segment_membership.py's seg_005
  logic uses -- sent a few days before that trial_start.
- order_placed: every order in orders.csv (known-customer AND guest alike
  -- this is the one place external_user_id is "almost" always populated,
  per schema_reference.md; guests get an email_address but no
  external_user_id).
- cart_abandoned: web_events.csv sessions with an add_to_cart but no
  purchase, known-customer only (guests have no email on file until they
  actually check out, so they can't be retargeted pre-purchase).

Plus 2 broadcast sends (Monthly Newsletter, Seasonal Sale Promo) to the
email-opted-in, non-deleted customer base that already existed as of each
send date -- Seasonal Sale Promo's 3 send dates match discount_codes.csv's
own HOLIDAY2024/JANRESET10_2025/JANRESET10_2026 valid_from dates exactly.

Soft-deleted customers are excluded from EVERY population here (including
their historical orders), same full-erasure treatment already applied to
customer_addresses/devices/web_sessions/app_sessions.

Each send resolves through a funnel (Send -> maybe Bounce, or -> maybe Open
-> maybe Click, -> maybe Unsubscribe after an Open) with different rates for
triggered vs. broadcast campaigns (triggered/transactional mail gets opened
far more reliably than broadcast marketing mail, realistically).

Output: data/braze_email_events.csv
"""
import datetime
import json
import numpy as np
import pandas as pd

from params import SEED, START_DATE, END_DATE
from build_customers import customer_id_for

TRIGGERED_RATES = {"bounce": 0.015, "open": 0.55, "click_given_open": 0.30, "unsub_given_open": 0.01}
BROADCAST_RATES = {"bounce": 0.020, "open": 0.28, "click_given_open": 0.15, "unsub_given_open": 0.03}

TRIAL_ENDING_LEAD_DAYS = 2
REACTIVATION_LEAD_DAYS_RANGE = (2, 5)
MERCH_TO_SUB_LEAD_DAYS_RANGE = (1, 3)
CART_ABANDON_LEAD_DAYS = 1

SEASONAL_SEND_DATES = [datetime.date(2024, 11, 15), datetime.date(2025, 1, 1), datetime.date(2026, 1, 1)]


def _random_time_of_day(rng):
    return datetime.time(int(rng.integers(6, 21)), int(rng.integers(0, 60)))


def _funnel(rng, campaign_id, external_user_id, email, send_at, rates):
    events = [("users.messages.email.Send", send_at)]
    if rng.random() < rates["bounce"]:
        events.append(("users.messages.email.Bounce", send_at + datetime.timedelta(minutes=int(rng.integers(1, 30)))))
        return events
    if rng.random() < rates["open"]:
        open_at = send_at + datetime.timedelta(minutes=int(rng.integers(5, 2880)))
        events.append(("users.messages.email.Open", open_at))
        if rng.random() < rates["click_given_open"]:
            click_at = open_at + datetime.timedelta(seconds=int(rng.integers(5, 600)))
            events.append(("users.messages.email.Click", click_at))
        if rng.random() < rates["unsub_given_open"]:
            unsub_at = open_at + datetime.timedelta(seconds=int(rng.integers(10, 1200)))
            events.append(("users.messages.email.Unsubscribe", unsub_at))
    return events


def build_braze_email_events(seed=SEED + 19):
    rng = np.random.default_rng(seed)
    campaigns = pd.read_csv("../data/braze_email_campaigns.csv").set_index("trigger_event")["campaign_id"]
    broadcast_campaigns = pd.read_csv("../data/braze_email_campaigns.csv")
    broadcast_campaigns = broadcast_campaigns[broadcast_campaigns["campaign_type"] == "broadcast"]

    customers = pd.read_csv("../data/customers.csv")
    non_deleted = customers[~customers["is_deleted"]].copy()
    non_deleted["created_at"] = pd.to_datetime(non_deleted["created_at"])
    email_by_customer = non_deleted.set_index("customer_id")["email"]
    non_deleted_ids = set(non_deleted["customer_id"])

    subs = pd.read_csv("../data/subscriptions.csv")
    subs = subs[subs["customer_id"].isin(non_deleted_ids)]
    sub_events = pd.read_csv("../data/subscription_events.csv").drop_duplicates(
        subset=["subscription_id", "event_type", "event_at"])
    orders = pd.read_csv("../data/orders.csv")
    web_events = pd.read_csv("../data/web_events.csv")
    timeline = json.load(open("../internal/_sim_customer_timeline.json"))

    sends = []  # (campaign_id, external_user_id, email, send_at, campaign_type)

    def add_send(trigger_event, cid, email, send_at):
        if send_at.date() > END_DATE:
            return
        sends.append((campaigns[trigger_event], cid, email, send_at, "triggered"))

    # --- trial_started / trial_ending ---
    trial_rows = subs[subs["trial_start"].notna()]
    for row in trial_rows.itertuples():
        cid = row.customer_id
        email = email_by_customer.get(cid)
        trial_start = datetime.datetime.combine(datetime.date.fromisoformat(row.trial_start), _random_time_of_day(rng))
        add_send("trial_started", cid, email, trial_start)
        trial_end = datetime.date.fromisoformat(row.trial_end)
        reminder_date = trial_end - datetime.timedelta(days=TRIAL_ENDING_LEAD_DAYS)
        if reminder_date >= datetime.date.fromisoformat(row.trial_start):
            reminder_at = datetime.datetime.combine(reminder_date, _random_time_of_day(rng))
            add_send("trial_ending", cid, email, reminder_at)

    # --- payment_failed ---
    payment_failed = sub_events[(sub_events["event_type"] == "payment_failed")
                                 & sub_events["customer_id"].isin(non_deleted_ids)]
    for row in payment_failed.itertuples():
        cid = row.customer_id
        email = email_by_customer.get(cid)
        sent_at = pd.Timestamp(row.event_at).to_pydatetime() + datetime.timedelta(minutes=int(rng.integers(5, 120)))
        add_send("payment_failed", cid, email, sent_at)

    # --- reactivation (email channel only) ---
    for t in timeline:
        cid = customer_id_for(t["customer_id"])
        if cid not in non_deleted_ids:
            continue
        for react in t["reactivations"]:
            if react["channel"] != "email":
                continue
            lead = int(rng.integers(*REACTIVATION_LEAD_DAYS_RANGE))
            send_date = datetime.date.fromisoformat(react["reactivated_at"]) - datetime.timedelta(days=lead)
            send_at = datetime.datetime.combine(send_date, _random_time_of_day(rng))
            add_send("reactivation", cid, email_by_customer.get(cid), send_at)

    # --- merch_to_sub_trigger ---
    subs_sorted = subs.copy()
    subs_sorted["first_date"] = pd.to_datetime(subs_sorted["trial_start"].fillna(subs_sorted["start_date"]))
    # .head(1) per group, NOT .first() -- groupby().first() reconciles NaNs
    # column-by-column across the whole group (it would happily borrow
    # canceled_at from a LATER subscription object if the true first row's
    # own canceled_at were null), which risks a Frankenstein row. head(1)
    # guarantees the literal first row, no per-column mixing.
    first_obj = subs_sorted.sort_values("first_date").groupby("customer_id").head(1).set_index("customer_id")
    for cid, row in first_obj.iterrows():
        if cid not in non_deleted_ids or pd.isna(row["trial_start"]):
            continue
        signup_date = non_deleted.set_index("customer_id").loc[cid, "created_at"]
        if row["first_date"] <= signup_date:
            continue  # direct signup, never course/merch-only -- no triggering email exists
        lead = int(rng.integers(*MERCH_TO_SUB_LEAD_DAYS_RANGE))
        send_date = (row["first_date"] - datetime.timedelta(days=lead)).date()
        send_at = datetime.datetime.combine(send_date, _random_time_of_day(rng))
        add_send("merch_to_sub_trigger", cid, email_by_customer.get(cid), send_at)

    # --- order_placed (known-customer + guest) ---
    for order in orders.itertuples():
        cid = order.customer_id if pd.notna(order.customer_id) else None
        if cid is not None and cid not in non_deleted_ids:
            continue
        email = email_by_customer.get(cid) if cid else order.guest_email
        add_send("order_placed", cid, email, datetime.datetime.fromisoformat(order.created_at))

    # --- cart_abandoned (known customer only) ---
    purchased_sessions = set(web_events.loc[web_events["event_type"] == "purchase", "session_id"])
    abandon = web_events[(web_events["event_type"] == "add_to_cart")
                          & (~web_events["session_id"].isin(purchased_sessions))
                          & web_events["customer_id"].notna()]
    abandon = abandon[abandon["customer_id"].isin(non_deleted_ids)]
    for row in abandon.itertuples():
        send_at = pd.Timestamp(row.occurred_at).to_pydatetime() + datetime.timedelta(days=CART_ABANDON_LEAD_DAYS)
        add_send("cart_abandoned", row.customer_id, email_by_customer.get(row.customer_id), send_at)

    # --- Broadcast: Monthly Newsletter ---
    newsletter_id = broadcast_campaigns.loc[broadcast_campaigns["campaign_name"] == "Monthly Newsletter", "campaign_id"].iloc[0]
    month = datetime.date(START_DATE.year, START_DATE.month, 1)
    while month <= END_DATE:
        eligible = non_deleted[(non_deleted["created_at"].dt.date <= month) & non_deleted["email_opt_in"]]
        send_at_base = datetime.datetime.combine(month, datetime.time(9, 0))
        for row in eligible.itertuples():
            send_at = send_at_base + datetime.timedelta(minutes=int(rng.integers(0, 600)))
            sends.append((newsletter_id, row.customer_id, row.email, send_at, "broadcast"))
        month = (month.replace(day=1) + datetime.timedelta(days=32)).replace(day=1)

    # --- Broadcast: Seasonal Sale Promo ---
    seasonal_id = broadcast_campaigns.loc[broadcast_campaigns["campaign_name"] == "Seasonal Sale Promo", "campaign_id"].iloc[0]
    for send_date in SEASONAL_SEND_DATES:
        if send_date > END_DATE:
            continue
        eligible = non_deleted[(non_deleted["created_at"].dt.date <= send_date) & non_deleted["email_opt_in"]]
        send_at_base = datetime.datetime.combine(send_date, datetime.time(8, 0))
        for row in eligible.itertuples():
            send_at = send_at_base + datetime.timedelta(minutes=int(rng.integers(0, 600)))
            sends.append((seasonal_id, row.customer_id, row.email, send_at, "broadcast"))

    # --- Resolve every send through the open/click/bounce/unsub funnel ---
    # Each send gets its own send_id shared across that send's funnel events
    # -- without it, two sends of the same recurring broadcast campaign to
    # the same customer (e.g. two different months' newsletters) would be
    # ungroupable, and funnel ordering (Send before its own Open/Click)
    # couldn't be verified per-send from the shipped table alone.
    rows = []
    for i, (campaign_id, external_user_id, email, send_at, campaign_type) in enumerate(sends, start=1):
        send_id = f"braze_email_send_{i:07d}"
        rates = TRIGGERED_RATES if campaign_type == "triggered" else BROADCAST_RATES
        for event_type, occurred_at in _funnel(rng, campaign_id, external_user_id, email, send_at, rates):
            rows.append({
                "send_id": send_id,
                "campaign_id": campaign_id,
                "external_user_id": external_user_id,
                "email_address": email,
                "event_type": event_type,
                "occurred_at": occurred_at,
            })

    df = pd.DataFrame(rows).sort_values("occurred_at").reset_index(drop=True)
    df.insert(0, "event_id", [f"braze_email_evt_{i:07d}" for i in range(1, len(df) + 1)])
    df["occurred_at"] = df["occurred_at"].apply(lambda d: pd.Timestamp(d).isoformat())
    return df


if __name__ == "__main__":
    df = build_braze_email_events()
    df.to_csv("../data/braze_email_events.csv", index=False)
    print(f"Wrote {len(df)} braze_email_events\n")
    print(df["event_type"].value_counts().to_string())
    print(f"\nSend count: {(df['event_type'] == 'users.messages.email.Send').sum()}")
    print(f"external_user_id null: {df['external_user_id'].isna().sum()} ({df['external_user_id'].isna().mean():.1%})")
