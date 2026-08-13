"""
Validation for `braze_email_events` (Phase 6, table 2 of 4) --
pandas-based, same 5-layer approach (see validate_products.py's docstring
for why pandas instead of DuckDB).

Central cross-checks: every send_id has EXACTLY one Send event, and every
Open/Click/Bounce/Unsubscribe for that send_id occurs strictly after its
own Send (never before -- proves the funnel is internally consistent, not
just independently plausible timestamps); external_user_id is null ONLY
for the order_placed campaign's guest sends (every other campaign always
carries a real customer); order_placed's Send count exactly equals
orders.csv's own eligible (non-deleted-customer + guest) row count; and
payment_failed's Send count exactly equals subscription_events.csv's own
deduped payment_failed count.
"""
import pandas as pd

from params import SEED
import build_braze_email_events as bee

results = []


def check(layer, name, condition, detail=""):
    results.append((layer, name, bool(condition), detail))


def run():
    events = pd.read_csv("../data/braze_email_events.csv")
    campaigns = pd.read_csv("../data/braze_email_campaigns.csv")
    customers = pd.read_csv("../data/customers.csv")
    orders = pd.read_csv("../data/orders.csv")
    sub_events = pd.read_csv("../data/subscription_events.csv")

    events["occurred_at"] = pd.to_datetime(events["occurred_at"])

    # --- 1. Structural ---
    check("Structural", "event_id non-null and unique",
          events["event_id"].notna().all() and events["event_id"].is_unique)
    check("Structural", "send_id, campaign_id, event_type, occurred_at all non-null",
          events[["send_id", "campaign_id", "event_type", "occurred_at"]].notna().all().all())
    valid_types = {"users.messages.email.Send", "users.messages.email.Open", "users.messages.email.Click",
                   "users.messages.email.Bounce", "users.messages.email.Unsubscribe"}
    check("Structural", "event_type is always one of the 5 dot-path values", events["event_type"].isin(valid_types).all())
    check("Structural", "email_address is non-null on every row (Braze always has an address to send to)",
          events["email_address"].notna().all())

    # --- 2. Referential integrity ---
    check("Referential", "every campaign_id exists in braze_email_campaigns.csv",
          events["campaign_id"].isin(campaigns["campaign_id"]).all())
    non_deleted_ids = set(customers.loc[~customers["is_deleted"], "customer_id"])
    check("Referential", "every non-null external_user_id exists in customers.csv and is NOT soft-deleted",
          events.loc[events["external_user_id"].notna(), "external_user_id"].isin(non_deleted_ids).all())

    order_placed_id = campaigns.loc[campaigns["trigger_event"] == "order_placed", "campaign_id"].iloc[0]
    non_order_placed_null = events[(events["campaign_id"] != order_placed_id) & events["external_user_id"].isna()]
    check("Referential", "external_user_id is null ONLY for the order_placed campaign's guest sends "
                        "(every other campaign always has a real, identified customer)",
          len(non_order_placed_null) == 0)

    # --- 3. Temporal ordering ---
    send_times = events[events["event_type"] == "users.messages.email.Send"].set_index("send_id")["occurred_at"]
    check("Structural", "every send_id has EXACTLY one Send event",
          events["send_id"].isin(send_times.index).all()
          and (events[events["event_type"] == "users.messages.email.Send"]["send_id"].value_counts() == 1).all())
    non_send = events[events["event_type"] != "users.messages.email.Send"].copy()
    non_send["send_time"] = non_send["send_id"].map(send_times)
    check("Temporal", "every Open/Click/Bounce/Unsubscribe occurs strictly AFTER its own send_id's Send event",
          (non_send["occurred_at"] > non_send["send_time"]).all())

    # --- 4. Business-rule invariants ---
    n_order_sends = (events["campaign_id"] == order_placed_id).sum() and \
        len(events[(events["campaign_id"] == order_placed_id) & (events["event_type"] == "users.messages.email.Send")])
    expected_order_sends = len(orders[orders["customer_id"].isna() | orders["customer_id"].isin(non_deleted_ids)])
    check("Business rule", "order_placed's Send count exactly equals orders.csv's own eligible "
                          "(non-deleted-customer + guest) row count",
          n_order_sends == expected_order_sends, detail=f"{n_order_sends} vs {expected_order_sends}")

    payment_failed_id = campaigns.loc[campaigns["trigger_event"] == "payment_failed", "campaign_id"].iloc[0]
    n_pf_sends = len(events[(events["campaign_id"] == payment_failed_id) & (events["event_type"] == "users.messages.email.Send")])
    deduped_pf = sub_events.drop_duplicates(subset=["subscription_id", "event_type", "event_at"])
    expected_pf = deduped_pf[(deduped_pf["event_type"] == "payment_failed")
                              & deduped_pf["customer_id"].isin(non_deleted_ids)].shape[0]
    check("Business rule", "payment_failed's Send count exactly equals subscription_events.csv's own "
                          "deduped payment_failed count (for non-deleted customers)",
          n_pf_sends == expected_pf, detail=f"{n_pf_sends} vs {expected_pf}")

    # --- 5. Distributional sanity ---
    n_send = (events["event_type"] == "users.messages.email.Send").sum()
    n_open = (events["event_type"] == "users.messages.email.Open").sum()
    open_rate = n_open / n_send
    check("Distributional", "overall open rate lands in a plausible email-marketing range (20-45%)",
          0.20 <= open_rate <= 0.45, detail=f"{open_rate:.1%}")
    bounce_rate = (events["event_type"] == "users.messages.email.Bounce").sum() / n_send
    check("Distributional", "bounce rate is a small single-digit share of sends (0.5-4%)",
          0.005 <= bounce_rate <= 0.04, detail=f"{bounce_rate:.1%}")

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
