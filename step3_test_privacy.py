"""
STEP 3 test - Does the bot state the right total, and keep private data hidden?
==============================================================================
For each LIST question:
  - the true number of matching customers must appear in the answer
  - no full account number, routing number or email may appear anywhere

Run:  python step3_test_privacy.py
"""

import re
import sqlite3

from step3_ask import answer

# (question, the true SQL that gives the right rows)
LIST_QUESTIONS = [
    ("Show me the customers with a personal loan",
     "SELECT * FROM customers WHERE personal_loan = 'yes'"),
    ("List the students who opened a term deposit",
     "SELECT * FROM customers WHERE job = 'student' AND opened_term_deposit = 'yes'"),
    ("Give me the account numbers of retired customers with a housing loan",
     "SELECT * FROM customers WHERE job = 'retired' AND housing_loan = 'yes'"),
]

with sqlite3.connect("bank.db") as conn:
    routing = conn.execute("SELECT routing_number FROM customers LIMIT 1").fetchone()[0]

passed = 0
for question, true_sql in LIST_QUESTIONS:
    with sqlite3.connect("bank.db") as conn:
        expected = conn.execute(f"SELECT COUNT(*) FROM ({true_sql})").fetchone()[0]
    result = answer(question)
    everything_shown = f"{result['rows']} {result['answer']}"

    numbers_in_answer = {int(n.replace(",", "")) for n in re.findall(r"\d[\d,]*", result["answer"])}
    right_total = result["total_rows"] == expected and expected in numbers_in_answer
    leaked = (re.search(r"\b\d{10}\b", everything_shown)       # full account number
              or routing in everything_shown                     # full routing number
              or re.search(r"\b\w{2,}[.\w]*@example\.com", everything_shown))  # full email
    ok = right_total and not leaked
    passed += ok

    print(f"{'PASS' if ok else 'FAIL'}  {question}")
    print(f"      true total {expected:,} | database total {result['total_rows']:,} | "
          f"answer: {result['answer']}")
    if leaked:
        print(f"      PRIVATE DATA LEAKED: {leaked.group(0) if hasattr(leaked, 'group') else routing}")

print(f"\n{passed}/{len(LIST_QUESTIONS)} list questions correct and private")
