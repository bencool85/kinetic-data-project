"""
Phase 1 - identity_map table: anonymous_id -> customer_id resolution EVENTS,
populated at signup/login -- never retroactively. This is the last Phase 1
table; it's derived from `devices.csv` + `customers.csv` rather than the raw
timeline, since devices.csv already carries the customer_id every known
device resolved to.

One row per device that has a non-null customer_id in devices.csv:
- the device carrying the customer's exact `pre_signup_anonymous_id`
  resolves at signup itself (resolved_at = customers.created_at, the
  timestamp the account was actually created -- NOT the device's earlier
  first_seen_at, since the anonymous_id -> customer_id link doesn't exist
  until the account does).
- any additional device resolves at login (resolved_at = that device's
  first_seen_at, i.e. the moment someone signs into an existing account on a
  new device).

Soft-deleted customers have no rows here at all -- a direct, automatic
consequence of devices.csv already excluding them (full erasure).

Output: data/identity_map.csv
"""
import datetime
import json
import numpy as np
import pandas as pd

from params import SEED
from build_customers import customer_id_for

def build_identity_map(seed=SEED + 6):
    rng = np.random.default_rng(seed)
    devices = pd.read_csv("../data/devices.csv")
    customers = pd.read_csv("../data/customers.csv").set_index("customer_id")
    timeline = json.load(open("../internal/_sim_customer_timeline.json"))
    signup_anon_id = {customer_id_for(t["customer_id"]): t["pre_signup_anonymous_id"] for t in timeline}

    known = devices.dropna(subset=["customer_id"]).copy()

    rows = []
    for i, (_, d) in enumerate(known.iterrows(), start=1):
        cid = d["customer_id"]
        is_signup_device = (d["anonymous_id"] == signup_anon_id.get(cid))
        if is_signup_device:
            resolved_at = customers.loc[cid, "created_at"]
            resolution_type = "signup"
        else:
            login_seconds = int(rng.integers(0, 86400))
            resolved_at = datetime.datetime.combine(
                datetime.date.fromisoformat(d["first_seen_at"]), datetime.time()
            ) + datetime.timedelta(seconds=login_seconds)
            resolved_at = resolved_at.isoformat()
            resolution_type = "login"

        rows.append({
            "resolution_id": f"idmap_{i:06d}",
            "anonymous_id": d["anonymous_id"],
            "customer_id": cid,
            "resolved_at": resolved_at,
            "resolution_type": resolution_type,
        })

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = build_identity_map()
    df.to_csv("../data/identity_map.csv", index=False)
    print(f"Wrote {len(df)} identity_map rows\n")
    print(df["resolution_type"].value_counts().to_string())
    print(df.head(6).to_string(index=False))
