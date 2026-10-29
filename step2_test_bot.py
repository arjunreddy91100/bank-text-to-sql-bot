"""
STEP 2 test - Does the bot match the answer key?
================================================
Asks the bot each answer-key question, runs the TRUE SQL ourselves,
and compares. This is your proof that the bot does not hallucinate.

Run:  python step2_test_bot.py
"""

import sqlite3

from check_answer_key import QUESTIONS
from step2_ask import answer

def same_answer(expected, got) -> bool:
    """Compare the main answer value (first value of the first row).
    Numbers may differ by 0.1, so AVG = 40.02 still matches 40.0."""
    if not expected or not got:
        return expected == got
    e, g = expected[0][0], got[0][0]
    if isinstance(e, (int, float)) and isinstance(g, (int, float)):
        return abs(e - g) <= 0.1
    return str(e).strip().lower() == str(g).strip().lower()


passed = 0
with sqlite3.connect("bank.db") as conn:
    for question, true_sql in QUESTIONS:
        expected = conn.execute(true_sql).fetchall()
        try:
            result = answer(question)
            got = result["rows"]
            ok = same_answer(expected, got)
        except Exception as e:
            ok, got = False, f"error: {e}"
        passed += ok
        print(f"{'PASS' if ok else 'FAIL'}  {question}")
        if not ok:
            print(f"      expected {expected}\n      got      {got}")

print(f"\n{passed}/{len(QUESTIONS)} questions answered correctly")
