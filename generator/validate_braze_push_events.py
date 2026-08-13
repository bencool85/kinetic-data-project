"""
Validation for `braze_push_events` (Phase 6, table 4 of 4 -- completes
Phase 6) -- pandas-based, same 5-layer approach (see validate_products.py's
docstring for why pandas instead of DuckDB).

Central cross-checks: same send_id/funnel-ordering discipline as
braze_email_events.py's validator (exactly one Send per send_id, every
Open/Click/Bounce/Unsubscribe strictly after its own Send), PLUS two checks
that are push-specific and have no email analog: (1) external_user_id is
NEVER null (push has no guest-checkout case the way email does -- every
send needs a real device), and (2) every single external_user_id on every
row must have push_opt_in == True in customers.csv (push_opt_in is a hard
delivery precondition here, not just a marketing-preference filter like it
is for email). Also verifies device_id/platform are internally consistent
with devices.csv's own primary-device convention, and exact-count
reconciliation of order_placed (known-customer, push-opted-in, has a
primary device) and streak_achieved (app_events.csv's own streak_achieved
population, push-opted-in) Send counts.
"""
import pandas as pd

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    events = pd.read_csv("../data/braze_push_events.csv")
    campaigns = pd.read_csv("../data/braze_push_campaigns.csv")
    customers = pd.read_csv("../data/customers.csv")
    devices = pd.read_csv("../data/devices.csv")
    orders = pd.read_csv("../data/orders.csv")
    app_events = pd.read_csv("../data/app_events.csv")

    events["occurred_at"] = pd.to_datetime(events["occurred_at"])

    non_deleted = customers[~customers["is_deleted"]]
    non_deleted_ids = set(non_deleted["customer_id"])
    push_opt_in_ids = set(non_deleted.loc[non_deleted["push_opt_in"], "customer_id"])
    primary_device = (
        devices.dropna(subset=["customer_id"]).sort_values("device_id")
        .groupby("customer_id").first()[["device_id", "device_type"]]
    )

    # --- 1. Structural ---
    check("Structural", "event_id non-null and unique",
          events["event_id"].notna().all() and events["event_id"].is_unique)
    check("Structural", "send_id, campaign_id, event_type, occurred_at, device_id, platform all non-null",
          events[["send_id", "campaign_id", "event_type", "occurred_at", "device_id", "platform"]].notna().all().all())
    valid_types = {
        "users.messages.pushnotification.Send", "users.messages.pushnotification.Open",
        "users.messages.pushnotification.Click", "users.messages.pushnotification.Bounce",
        "users.messages.pushnotification.Unsubscribe",
    }
    check("Structural", "event_type is always one of the 5 dot-path pushnotification values",
          events["event_type"].isin(valid_types).all())
    check("Structural", "occurred_at timestamps are whole-second (no fractional-second formatting bug)",
          not events["occurred_at"].dt.microsecond.astype(bool).any())
    check("Structural", "external_user_id is NEVER null (push has no guest-checkout case -- "
                       "every send targets a known customer's device)",
          events["external_user_id"].notna().all())

    # --- 2. Referential integrity ---
    check("Referential", "every campaign_id exists in braze_push_campaigns.csv",
          events["campaign_id"].isin(campaigns["campaign_id"]).all())
    check("Referential", "every external_user_id exists in customers.csv and is NOT soft-deleted",
          events["external_user_id"].isin(non_deleted_ids).all())
    check("Referential", "every external_user_id has push_opt_in == True in customers.csv "
                        "(push_opt_in is a hard delivery precondition, unlike email)",
          events["external_user_id"].isin(push_opt_in_ids).all())
    check("Referential", "every device_id exists in devices.csv",
          events["device_id"].isin(devices["device_id"]).all())
    merged = events.merge(devices[["device_id", "device_type"]], on="device_id", how="left", suffixes=("", "_dev"))
    check("Referential", "platform on every row exactly matches that device_id's own device_type in devices.csv",
          (merged["platform"] == merged["device_type"]).all())
    expected_device = events["external_user_id"].map(primary_device["device_id"])
    check("Referential", "device_id on every row is that customer's PRIMARY device "
                        "(devices.csv's first row per customer_id, same convention app_sessions.csv uses)",
          (events["device_id"] == expected_device).all())

    # --- 3. Temporal ordering ---
    send_times = events[events["event_type"] == "users.messages.pushnotification.Send"].set_index("send_id")["occurred_at"]
    check("Structural", "every send_id has EXACTLY one Send event",
          events["send_id"].isin(send_times.index).all()
          and (events[events["event_type"] == "users.messages.pushnotification.Send"]["send_id"].value_counts() == 1).all())
    non_send = events[events["event_type"] != "users.messages.pushnotification.Send"].copy()
    non_send["send_time"] = non_send["send_id"].map(send_times)
    check("Temporal", "every Open/Click/Bounce/Unsubscribe occurs strictly AFTER its own send_id's Send event",
          (non_send["occurred_at"] > non_send["send_time"]).all())

    # --- 4. Business-rule invariants ---
    order_placed_id = campaigns.loc[campaigns["trigger_event"] == "order_placed", "campaign_id"].iloc[0]
    n_order_sends = len(events[(events["campaign_id"] == order_placed_id)
                                & (events["event_type"] == "users.messages.pushnotification.Send")])
    known_orders = orders[orders["customer_id"].notna()]
    expected_order_sends = known_orders[known_orders["customer_id"].isin(push_opt_in_ids)
                                         & known_orders["customer_id"].isin(primary_device.index)].shape[0]
    check("Business rule", "order_placed's Send count exactly equals orders.csv's own eligible "
                          "(known-customer + push-opted-in + has-a-device) row count",
          n_order_sends == expected_order_sends, detail=f"{n_order_sends} vs {expected_order_sends}")

    streak_id = campaigns.loc[campaigns["trigger_event"] == "streak_achieved", "campaign_id"].iloc[0]
    n_streak_sends = len(events[(events["campaign_id"] == streak_id)
                                 & (events["event_type"] == "users.messages.pushnotification.Send")])
    streaks = app_events[app_events["event_type"] == "streak_achieved"]
    expected_streak = streaks[streaks["customer_id"].isin(push_opt_in_ids)
                               & streaks["customer_id"].isin(primary_device.index)].shape[0]
    check("Business rule", "streak_achieved's Send count exactly equals app_events.csv's own "
                          "streak_achieved population (for push-opted-in customers with a device)",
          n_streak_sends == expected_streak, detail=f"{n_streak_sends} vs {expected_streak}")

    email_campaigns = pd.read_csv("../data/braze_email_campaigns.csv")
    check("Business rule", "no trigger_event exists in push campaigns that doesn't have a real source "
                          "population this build can derive from (closed vocabulary check)",
          campaigns.loc[campaigns["trigger_event"].notna(), "trigger_event"].isin([
              "trial_ending", "payment_failed", "reactivation", "streak_achieved", "order_placed",
          ]).all())

    # --- 5. Distributional sanity ---
    n_send = (events["event_type"] == "users.messages.pushnotification.Send").sum()
    n_open = (events["event_type"] == "users.messages.pushnotification.Open").sum()
    open_rate = n_open / n_send
    check("Distributional", "overall open rate lands in a plausible push-marketing range (10-30%, "
                          "lower than email's -- push open rates trail email in practice)",
          0.10 <= open_rate <= 0.30, detail=f"{open_rate:.1%}")
    bounce_rate = (events["event_type"] == "users.messages.pushnotification.Bounce").sum() / n_send
    check("Distributional", "bounce rate is a small single-digit share of sends (1-5%, higher than "
                          "email's -- push bounces (uninstalled app / revoked permission) are more common)",
          0.01 <= bounce_rate <= 0.05, detail=f"{bounce_rate:.1%}")
    n_triggered_campaigns = set(campaigns.loc[campaigns["campaign_type"] == "triggered", "campaign_id"])
    n_broadcast_campaigns = set(campaigns.loc[campaigns["campaign_type"] == "broadcast", "campaign_id"])
    check("Distributional", "sends exist for both triggered and broadcast campaign types",
          events["campaign_id"].isin(n_triggered_campaigns).any()
          and events["campaign_id"].isin(n_broadcast_campaigns).any())

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
