"""
STEP 3 - Fix the hallucination + protect private data
=====================================================
The bug we found in Step 2:
  Question: "Show me the customers with a personal loan"
  The database found 6,248 customers, but we only showed the AI 20 rows.
  The AI counted the rows itself and said "22". Wrong - a hallucination.

Two fixes in this file:
  FIX 1 - The DATABASE counts, never the AI.
          We run  SELECT COUNT(*) FROM (<the AI's query>)  to get the true total,
          and tell the AI: "the result has exactly 6,248 rows - use this number."
  FIX 2 - Private data is MASKED before anyone sees it, including the AI.
          account 3410529190 -> ******9190    email robert.johnson5@example.com -> r***@example.com
          last name Johnson  -> J.            routing 104332181 -> *****2181

Run:
  python step3_ask.py "Show me the customers with a personal loan"
  python step3_ask.py              # no question = keep asking in a loop
"""

import re
import sqlite3
import sys

# Reuse the pieces from Step 2 that already work
from step2_ask import DATABASE, SQL_INSTRUCTIONS, ask_ai, clean_sql, describe_table

ROWS_SHOWN_TO_AI = 20

# ----------------------------- FIX 2: masking --------------------------------
def mask_value(column: str, value):
    """Hide private data. Checks the column NAME and the VALUE's shape,
    so it still works if the AI renames a column (e.g. 'account_number AS acct')."""
    if value is None:
        return value
    text = str(value)
    col = column.lower()
    if "email" in col or re.fullmatch(r"[^@\s]+@[^@\s]+", text):
        return text[0] + "***@" + text.split("@")[-1]
    if "account" in col or "routing" in col or re.fullmatch(r"\d{9,10}", text):
        return "*" * (len(text) - 4) + text[-4:]
    if col == "last_name":
        return text[0] + "."
    return value


def mask_rows(columns, rows):
    return [tuple(mask_value(c, v) for c, v in zip(columns, row)) for row in rows]


# ----------------------------- the answer step -------------------------------
ANSWER_INSTRUCTIONS = """You explain a database result to a bank owner in one or two short sentences.
Rules:
- The result has EXACTLY the number of rows given in "total_rows". If you mention how many
  customers or rows there are, use total_rows. NEVER count the sample rows yourself.
- You only see a SAMPLE of the rows. Do not describe the sample as if it were everything.
- Use only numbers that appear in the result. Do not estimate or invent numbers.
- Private fields are masked (***). Never try to guess or restore them.
- If total_rows is 0, say no matching customers were found."""


def answer(question: str) -> dict:
    # Read-only connection: even if the AI wrote DELETE, the database refuses.
    conn = sqlite3.connect(f"file:{DATABASE}?mode=ro", uri=True)
    try:
        sql = clean_sql(ask_ai(SQL_INSTRUCTIONS.format(schema=describe_table(conn)), question))
        cursor = conn.execute(sql)
        columns = [d[0] for d in cursor.description]
        rows = cursor.fetchmany(ROWS_SHOWN_TO_AI)
        # FIX 1: the database counts the full result
        total_rows = conn.execute(f"SELECT COUNT(*) FROM ({sql})").fetchone()[0]
    finally:
        conn.close()

    rows = mask_rows(columns, rows)        # FIX 2: mask BEFORE the AI sees anything
    result_text = (f"total_rows: {total_rows}\n"
                   f"columns: {columns}\n"
                   f"sample rows (first {len(rows)} of {total_rows}): {rows}")
    reply = ask_ai(ANSWER_INSTRUCTIONS,
                   f"Question: {question}\nSQL used: {sql}\nResult:\n{result_text}")
    return {"question": question, "sql": sql, "columns": columns, "rows": rows,
            "total_rows": total_rows, "answer": reply}


def show(result: dict):
    print(f"\nQuestion: {result['question']}")
    print(f"SQL     : {result['sql']}")
    print(f"Rows    : {result['total_rows']:,} total (counted by the database)")
    print(f"Columns : {result['columns']}")
    for row in result["rows"][:5]:
        print(f"          {row}")
    if result["total_rows"] > 5:
        print(f"          ... {result['total_rows'] - 5:,} more")
    print(f"Answer  : {result['answer']}\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        show(answer(" ".join(sys.argv[1:])))
    else:
        while (q := input("Ask a question (or press Enter to quit): ").strip()):
            try:
                show(answer(q))
            except Exception as e:
                print(f"Sorry, that failed: {e}\n")
