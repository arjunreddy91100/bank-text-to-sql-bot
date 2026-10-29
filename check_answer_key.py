"""
Answer key: questions the bank owner might ask, with the exact SQL and the
true answer straight from the database. Later, the bot must match these.

Run:  python check_answer_key.py
"""

import sqlite3

QUESTIONS = [
    ("How many customers do we have?",
     "SELECT COUNT(*) FROM customers"),
    ("How many customers have a personal loan?",
     "SELECT COUNT(*) FROM customers WHERE personal_loan = 'yes'"),
    ("How many customers have a housing loan?",
     "SELECT COUNT(*) FROM customers WHERE housing_loan = 'yes'"),
    ("How many customers have BOTH a personal and a housing loan?",
     "SELECT COUNT(*) FROM customers WHERE personal_loan = 'yes' AND housing_loan = 'yes'"),
    ("How many customers opened a term deposit?",
     "SELECT COUNT(*) FROM customers WHERE opened_term_deposit = 'yes'"),
    ("How many students do we have?",
     "SELECT COUNT(*) FROM customers WHERE job = 'student'"),
    ("What is the average customer age?",
     "SELECT ROUND(AVG(age), 1) FROM customers"),
    ("Which job has the most personal loans?",
     "SELECT job, COUNT(*) FROM customers WHERE personal_loan = 'yes' "
     "GROUP BY job ORDER BY COUNT(*) DESC LIMIT 1"),
]

if __name__ == "__main__":   # print only when run directly, not when imported
    with sqlite3.connect("bank.db") as conn:
        for question, sql in QUESTIONS:
            answer = conn.execute(sql).fetchone()
            answer = answer[0] if len(answer) == 1 else answer
            print(f"Q: {question}\n   SQL: {sql}\n   Answer: {answer}\n")
