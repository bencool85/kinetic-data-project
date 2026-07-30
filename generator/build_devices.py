"""
Phase 1 - devices table: device_id, customer_id (nullable -- devices can be
anonymous), anonymous_id, device_type, first_seen_at, last_seen_at.

Two populations get device rows:
1. Known customers (non-deleted): a primary device carrying their EXACT
   `pre_signup_anonymous_id` from the master timeline (this is the device
   `identity_map` will resolve next). ~20% also get a 2nd device (customer_id
   already populated -- this project isn't modeling web/app sessions yet, so
   a second device's own identity-resolution *event* isn't separately tracked
   until a phase that needs that granularity).
2. The anonymous ghost population (17,050 people who never converted):
   one device each, customer_id always null, anonymous_id = their own
   anon_id from `_sim_anonymous_population.csv`.

Soft-deleted customers get ZERO device rows, same full-erasure treatment as
`customer_addresses`.

Output: data/devices.csv
"""
import datetime
import hashlib
import json
import numpy as np
import pandas as pd

from params import SEED, SECOND_DEVICE_RATE, DEVICE_TYPE_WEIGHTS, END_DATE
from build_customers import customer_id_for

DEVICE_TYPES = list(DEVICE_TYPE_WEIGHTS.keys())
DEVICE_TYPE_P = list(DEVICE_TYPE_WEIGHTS.values())


def _last_activity_date(t):
    """Latest date anything happens in this customer's timeline; END_DATE
    itself if they're a currently-active subscriber (still using the app)."""
    dates = [t["signup_date"]]
    if t["trial"]:
        dates.append(t["trial"]["end"])
    for iv in t["subscription_intervals"]:
        dates.append(iv["start"])
        if iv["end"]:
            dates.append(iv["end"])
    for e in t["subscription_events"]:
        dates.append(e["event_at"])
    for o in t["order_events"]:
        dates.append(o["date"])
    for r in t["reactivations"]:
        dates.append(r["reactivated_at"])
    max_date = max(datetime.date.fromisoformat(d) for d in dates)
    is_active_sub = any(iv["end"] is None for iv in t["subscription_intervals"])
    if is_active_sub:
        return END_DATE
    # A trial_in_progress customer's recorded trial "end" is up to TRIAL_DAYS
    # past END_DATE (the trial simply hadn't resolved yet when the dataset
    # window closed) -- clip to END_DATE so nothing here can ever be "seen"
    # after the dataset's own observation window ends.
    return min(max_date, END_DATE)


def build_devices(seed=SEED + 5):
    rng = np.random.default_rng(seed)
    timeline = json.load(open("../internal/_sim_customer_timeline.json"))
    customers = pd.read_csv("../data/customers.csv").set_index("customer_id")
    anon = pd.read_csv("../internal/_sim_anonymous_population.csv")

    rows = []
    device_num = 0

    for t in timeline:
        cid = customer_id_for(t["customer_id"])
        if customers.loc[cid, "is_deleted"]:
            continue

        first_seen = datetime.date.fromisoformat(t["pre_signup_first_seen"])
        signup_date = datetime.date.fromisoformat(t["signup_date"])
        last_activity = _last_activity_date(t)

        device_num += 1
        rows.append({
            "device_id": f"dev_{device_num:06d}",
            "customer_id": cid,
            "anonymous_id": t["pre_signup_anonymous_id"],
            "device_type": str(rng.choice(DEVICE_TYPES, p=DEVICE_TYPE_P)),
            "first_seen_at": first_seen.isoformat(),
            "last_seen_at": max(first_seen, last_activity).isoformat(),
        })

        if rng.random() < SECOND_DEVICE_RATE:
            span_days = max(1, (last_activity - signup_date).days)
            second_first_seen = signup_date + datetime.timedelta(days=int(rng.integers(0, span_days + 1)))
            device_num += 1
            rows.append({
                "device_id": f"dev_{device_num:06d}",
                "customer_id": cid,
                # Deterministic (hash of device_num), not uuid.uuid4() -- see
                # the identical fix + rationale in simulate_customers.py's
                # pre_signup_anon_id.
                "anonymous_id": "anon_" + hashlib.md5(f"seconddevice_{device_num}".encode()).hexdigest()[:16],
                "device_type": str(rng.choice(DEVICE_TYPES, p=DEVICE_TYPE_P)),
                "first_seen_at": second_first_seen.isoformat(),
                "last_seen_at": max(second_first_seen, last_activity).isoformat(),
            })

    for _, ghost in anon.iterrows():
        first_seen = datetime.date.fromisoformat(ghost["first_seen_date"])
        if bool(ghost["is_guest_purchaser"]):
            last_seen = datetime.date.fromisoformat(ghost["guest_purchase_date"])
        else:
            span = int(rng.integers(0, 14))
            last_seen = min(first_seen + datetime.timedelta(days=span), END_DATE)
        device_num += 1
        rows.append({
            "device_id": f"dev_{device_num:06d}",
            "customer_id": None,
            "anonymous_id": ghost["anonymous_id"],
            "device_type": str(rng.choice(DEVICE_TYPES, p=DEVICE_TYPE_P)),
            "first_seen_at": first_seen.isoformat(),
            "last_seen_at": max(first_seen, last_seen).isoformat(),
        })

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = build_devices()
    df.to_csv("../data/devices.csv", index=False)
    print(f"Wrote {len(df)} devices\n")
    print(f"With customer_id: {df['customer_id'].notna().sum()}, anonymous-only: {df['customer_id'].isna().sum()}")
    print(df["device_type"].value_counts(normalize=True).round(3).to_string())
    print(df.head(6).to_string(index=False))
