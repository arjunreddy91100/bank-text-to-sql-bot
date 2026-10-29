"""
STEP 1 - Build the bank's customer database
===========================================
What this does, in plain words:
  1. Reads the Kaggle bank file (41,188 customers).
  2. Keeps only the columns about the customer, drops the 5 economy columns.
  3. Renames columns to plain English, so both people and the AI understand them.
  4. Gives every customer a MADE-UP name, email, account number and routing number.
  5. Saves everything into one database file: bank.db (SQLite).

Nothing here is real personal data:
  - Names come from the Faker library (random fake names).
  - Emails use example.com, a domain reserved for examples - it can't reach anyone.
  - Account numbers are random 10-digit numbers.
  - The routing number deliberately FAILS the US bank checksum, so it can
    never match a real bank.

Run:  python step1_build_database.py
"""

import random
import sqlite3

import pandas as pd
from faker import Faker

SOURCE_CSV = "data/bank-direct-marketing-campaigns.csv"
DATABASE = "bank.db"
SEED = 42  # same seed = same fake names every run, so results are repeatable

# Old Kaggle column name  ->  plain-English name
RENAME = {
    "age": "age",
    "job": "job",
    "marital": "marital_status",
    "education": "education",
    "default": "credit_default",          # 'default' is a reserved word in SQL
    "housing": "housing_loan",
    "loan": "personal_loan",
    "contact": "contact_method",
    "month": "last_contact_month",
    "day_of_week": "last_contact_day",
    "campaign": "calls_this_campaign",
    "pdays": "days_since_previous_campaign",
    "previous": "previous_campaign_calls",
    "poutcome": "previous_campaign_outcome",
    "y": "opened_term_deposit",           # the campaign's result
}


def fake_routing_number(rng: random.Random) -> str:
    """A 9-digit number that FAILS the ABA checksum, so it is never a real bank."""
    while True:
        digits = [rng.randint(0, 9) for _ in range(9)]
        checksum = (3 * (digits[0] + digits[3] + digits[6])
                    + 7 * (digits[1] + digits[4] + digits[7])
                    + 1 * (digits[2] + digits[5] + digits[8]))
        if checksum % 10 != 0:
            return "".join(map(str, digits))


def main():
    # 1. Read the file
    df = pd.read_csv(SOURCE_CSV)
    print(f"Read {len(df):,} customers, {len(df.columns)} columns")

    # 2 + 3. Keep and rename the customer columns
    df = df[list(RENAME)].rename(columns=RENAME)

    # 999 in this column means "never contacted before" - store it as empty instead
    df["days_since_previous_campaign"] = df["days_since_previous_campaign"].replace(999, None)

    # 4. Made-up identities
    fake = Faker("en_US")
    Faker.seed(SEED)
    rng = random.Random(SEED)

    first, last = [], []
    for _ in range(len(df)):
        first.append(fake.first_name())
        last.append(fake.last_name())

    df.insert(0, "customer_id", [f"C{i:05d}" for i in range(1, len(df) + 1)])
    df.insert(1, "first_name", first)
    df.insert(2, "last_name", last)
    df.insert(3, "email", [f"{f.lower()}.{l.lower()}{i}@example.com"
                           for i, (f, l) in enumerate(zip(first, last), 1)])

    # One small local bank = one routing number for everyone
    routing = fake_routing_number(rng)
    accounts, seen = [], set()
    while len(accounts) < len(df):
        number = str(rng.randint(10**9, 10**10 - 1))
        if number not in seen:          # keep numbers unique
            seen.add(number)
            accounts.append(number)     # a list keeps a fixed order
    df.insert(4, "account_number", accounts)
    df.insert(5, "routing_number", routing)

    # 5. Save to the database
    with sqlite3.connect(DATABASE) as conn:
        df.to_sql("customers", conn, if_exists="replace", index=False)
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_customer_id ON customers(customer_id)")

    print(f"Saved table 'customers' to {DATABASE}: {len(df):,} rows, {len(df.columns)} columns")
    print("\nFirst 3 customers:")
    print(df.head(3)[["customer_id", "first_name", "last_name", "email",
                      "account_number", "routing_number", "age", "job",
                      "personal_loan", "housing_loan"]].to_string(index=False))


if __name__ == "__main__":
    main()
