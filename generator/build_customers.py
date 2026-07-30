"""
Phase 1 - customers table: one row per simulated customer, derived directly
from the Phase 0 master timeline (`_sim_customer_timeline.json`).

customer_id mapping convention (used by every later table that references a
customer): the timeline's integer customer_id N maps to the shipped
`cust_{N:05d}`. Defined once here in `customer_id_for()` and imported by every
later builder so the mapping never drifts between tables.

Deliberately NOT included here: account_type, trial/subscription/churn
fields. Those live in the timeline for generation purposes, but a real
customers table wouldn't carry them directly -- subscription status is a
`subscriptions` table concern (Phase 2), not an identity-table concern. This
also matches the design note in generation_plan.md: downstream phases must key
off actual subscription/trial state, not account_type.

Output: data/customers.csv
"""
import datetime
import json
import numpy as np
import pandas as pd

from params import SEED, EMAIL_OPT_IN_RATE, PUSH_OPT_IN_RATE, IS_DELETED_RATE

FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
    "David", "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
    "Matthew", "Margaret", "Anthony", "Betty", "Mark", "Sandra", "Donald", "Ashley",
    "Steven", "Dorothy", "Andrew", "Kimberly", "Paul", "Emily", "Joshua", "Donna",
    "Kenneth", "Michelle", "Kevin", "Carol", "Brian", "Amanda", "George", "Melissa",
    "Timothy", "Deborah", "Ronald", "Stephanie", "Edward", "Rebecca", "Jason", "Sharon",
    "Jeffrey", "Laura", "Ryan", "Cynthia", "Jacob", "Kathleen", "Gary", "Amy",
    "Nicholas", "Angela", "Eric", "Shirley", "Jonathan", "Anna", "Stephen", "Brenda",
    "Larry", "Pamela", "Justin", "Emma", "Scott", "Nicole", "Brandon", "Helen",
    "Benjamin", "Samantha", "Samuel", "Katherine", "Gregory", "Christine", "Alexander", "Debra",
    "Frank", "Rachel", "Patrick", "Carolyn", "Raymond", "Janet", "Jack", "Maria",
    "Dennis", "Heather", "Jerry", "Diane",
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas",
    "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White",
    "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker", "Young",
    "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
    "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
    "Carter", "Roberts", "Gomez", "Phillips", "Evans", "Turner", "Diaz", "Parker",
    "Cruz", "Edwards", "Collins", "Reyes", "Stewart", "Morris", "Morales", "Murphy",
    "Cook", "Rogers", "Gutierrez", "Ortiz", "Morgan", "Cooper", "Peterson", "Bailey",
    "Reed", "Kelly", "Howard", "Ramos", "Kim", "Cox", "Ward", "Richardson",
]
EMAIL_DOMAINS = ["gmail.com", "yahoo.com", "icloud.com", "outlook.com", "hotmail.com",
                  "aol.com", "comcast.net", "protonmail.com"]
EMAIL_DOMAIN_WEIGHTS = [0.40, 0.15, 0.15, 0.10, 0.08, 0.04, 0.05, 0.03]


def customer_id_for(sim_customer_id):
    """The single source of truth for the integer-timeline-id -> shipped-id
    mapping. Every later table that references a customer must import this
    rather than reinventing the format."""
    return f"cust_{sim_customer_id:05d}"


def build_customers(seed=SEED + 3):
    rng = np.random.default_rng(seed)
    timeline = json.load(open("../internal/_sim_customer_timeline.json"))

    used_emails = set()
    rows = []
    for t in timeline:
        sim_id = t["customer_id"]
        customer_id = customer_id_for(sim_id)
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        domain = rng.choice(EMAIL_DOMAINS, p=EMAIL_DOMAIN_WEIGHTS)

        base_local = f"{first.lower()}.{last.lower()}"
        email = f"{base_local}@{domain}"
        suffix = 1
        while email in used_emails:
            suffix += 1
            email = f"{base_local}{suffix}@{domain}"
        used_emails.add(email)

        signup_date = datetime.date.fromisoformat(t["signup_date"])
        signup_seconds = int(rng.integers(0, 86400))
        created_at = datetime.datetime.combine(signup_date, datetime.time()) + datetime.timedelta(seconds=signup_seconds)

        is_deleted = bool(rng.random() < IS_DELETED_RATE)
        if is_deleted:
            first_name, last_name = "Deleted", "User"
            email = f"deleted_user_{sim_id:05d}@deleted.kinetic.invalid"
            email_opt_in, push_opt_in = False, False
        else:
            first_name, last_name = first, last
            email_opt_in = bool(rng.random() < EMAIL_OPT_IN_RATE)
            push_opt_in = bool(rng.random() < PUSH_OPT_IN_RATE)

        rows.append({
            "customer_id": customer_id,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "created_at": created_at.isoformat(),
            "signup_source": t["signup_source"],
            "email_opt_in": email_opt_in,
            "push_opt_in": push_opt_in,
            "is_deleted": is_deleted,
        })

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = build_customers()
    df.to_csv("../data/customers.csv", index=False)
    print(f"Wrote {len(df)} customers\n")
    print(df.head(8).to_string(index=False))
    print(f"\nis_deleted: {df['is_deleted'].sum()} ({df['is_deleted'].mean():.1%})")
    print(f"email_opt_in: {df['email_opt_in'].mean():.1%}, push_opt_in: {df['push_opt_in'].mean():.1%}")
