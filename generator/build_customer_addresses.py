"""
Phase 1 - customer_addresses table.

Who gets an address:
- billing: every customer who ever needed to provide a payment method --
  subscriber-path customers (a trial requires a card up front, even if they
  never converted) OR anyone with at least one order (course or merch).
- shipping: additionally, anyone with at least one *merch* order (courses are
  digital, nothing to ship).
- soft-deleted customers get ZERO address rows -- full erasure, stricter than
  the name/email scrub in `customers` (address has no downstream revenue-table
  dependency the way order/subscription history does, so there's no
  referential-integrity reason to keep it around).

Obviously-fake addresses (mirrors the "fake" email-domain approach): every
street address is guaranteed non-existent by construction -- "<number> Fake
<word> <suffix>" (e.g. "482 Fake Oak Street"). No real street is named "Fake
___", so the full address can never resolve to an actual deliverable
location, regardless of how realistic the city/state/zip look. City/state/zip
are drawn from a small set of real U.S. metros (for plausible geographic
variety in later analytics) -- that's safe to keep realistic because a
city/state/zip alone identifies no one; only the (fake, guaranteed-impossible)
street makes the full address non-deliverable.

Output: data/customer_addresses.csv
"""
import datetime
import json
import numpy as np
import pandas as pd

from params import SEED
from build_customers import customer_id_for

CITIES = [
    ("Chicago", "IL", "60601"), ("Austin", "TX", "78701"), ("Denver", "CO", "80202"),
    ("Seattle", "WA", "98101"), ("Portland", "OR", "97201"), ("Nashville", "TN", "37201"),
    ("Atlanta", "GA", "30301"), ("Phoenix", "AZ", "85001"), ("San Diego", "CA", "92101"),
    ("Minneapolis", "MN", "55401"), ("Charlotte", "NC", "28202"), ("Columbus", "OH", "43215"),
    ("Boston", "MA", "02108"), ("Dallas", "TX", "75201"), ("Raleigh", "NC", "27601"),
    ("Tampa", "FL", "33602"), ("Salt Lake City", "UT", "84101"), ("Kansas City", "MO", "64105"),
    ("Indianapolis", "IN", "46204"), ("Sacramento", "CA", "95814"), ("Orlando", "FL", "32801"),
    ("Pittsburgh", "PA", "15222"), ("Milwaukee", "WI", "53202"), ("Richmond", "VA", "23219"),
    ("Boise", "ID", "83702"),
]
STREET_WORDS = ["Oak", "Maple", "Cedar", "Pine", "Elm", "Birch", "Willow", "Sunset",
                 "Meadow", "River", "Highland", "Lake", "Forest", "Spring", "Ridge",
                 "Valley", "Prairie", "Harbor", "Canyon", "Summit"]
STREET_SUFFIXES = ["Street", "Avenue", "Road", "Drive", "Lane", "Boulevard", "Way", "Court", "Place", "Trail"]

SAME_AS_BILLING_RATE = 0.70   # of customers needing shipping, % whose ship-to matches their billing address
UNIT_RATE = 0.25               # % of addresses that include an apartment/suite unit


def _fake_address(rng):
    house_number = int(rng.integers(100, 9999))
    word = rng.choice(STREET_WORDS)
    suffix = rng.choice(STREET_SUFFIXES)
    street = f"{house_number} Fake {word} {suffix}"
    unit = None
    if rng.random() < UNIT_RATE:
        kind = rng.choice(["Apt", "Suite"])
        unit = f"{kind} {int(rng.integers(1, 400))}"
    city, state, zip_code = CITIES[rng.integers(0, len(CITIES))]
    return {"street_address": street, "unit": unit, "city": city, "state": state,
            "zip_code": zip_code, "country": "US"}


def build_customer_addresses(seed=SEED + 4):
    rng = np.random.default_rng(seed)
    timeline = json.load(open("../internal/_sim_customer_timeline.json"))
    customers = pd.read_csv("../data/customers.csv").set_index("customer_id")

    rows = []
    addr_num = 0
    for t in timeline:
        cid = customer_id_for(t["customer_id"])
        if customers.loc[cid, "is_deleted"]:
            continue  # full erasure -- no address rows for deleted accounts

        merch_dates = sorted(o["date"] for o in t["order_events"] if o["order_type"] == "merch")
        needs_billing = (t["account_type"] == "subscriber") or (len(t["order_events"]) > 0)
        needs_shipping = len(merch_dates) > 0

        billing_addr = None
        if needs_billing:
            addr_num += 1
            billing_addr = _fake_address(rng)
            billing_created_at = t["signup_date"] if t["account_type"] == "subscriber" else t["order_events"][0]["date"]
            rows.append({
                "address_id": f"addr_{addr_num:05d}",
                "customer_id": cid,
                "address_type": "billing",
                "created_at": billing_created_at,
                **billing_addr,
            })

        if needs_shipping:
            addr_num += 1
            if billing_addr is not None and rng.random() < SAME_AS_BILLING_RATE:
                ship_addr = billing_addr
            else:
                ship_addr = _fake_address(rng)
            rows.append({
                "address_id": f"addr_{addr_num:05d}",
                "customer_id": cid,
                "address_type": "shipping",
                "created_at": merch_dates[0],
                **ship_addr,
            })

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = build_customer_addresses()
    df.to_csv("../data/customer_addresses.csv", index=False)
    print(f"Wrote {len(df)} addresses for {df['customer_id'].nunique()} customers\n")
    print(df["address_type"].value_counts().to_string())
    print(df.head(6).to_string(index=False))
