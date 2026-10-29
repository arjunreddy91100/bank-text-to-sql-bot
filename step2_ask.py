"""
STEP 2 - Ask the bank database a question in plain English
==========================================================
The flow, in plain words:
  1. The owner types a question:      "How many customers have a personal loan?"
  2. We show the AI the table layout (column names + example values).
  3. The AI writes ONE SQL query:     SELECT COUNT(*) FROM customers WHERE personal_loan = 'yes'
  4. The COMPUTER runs that query:    6248          <- exact, no guessing
  5. The AI turns the result into a sentence, using ONLY that result.

Why this avoids hallucination: the AI never invents numbers. It only translates
English -> SQL and result -> English. The database does the counting.

Run (Ollama must be running):
  python step2_ask.py "How many customers have a personal loan?"
  python step2_ask.py              # no question = keep asking in a loop

Switching to Azure OpenAI later: change the 3 settings in the CONFIG block.
"""

import re
import sqlite3
import sys

from openai import OpenAI

# ----------------------------- CONFIG ---------------------------------------
# Local and free: Ollama speaks the same API as OpenAI, at this address.
BASE_URL = "http://localhost:11434/v1"
API_KEY = "ollama"                 # Ollama ignores it, but the library needs a value
MODEL = "qwen2.5-coder:7b"         # change to a model from `ollama list`
# Azure OpenAI later (example):
#   BASE_URL = "https://<your-resource>.openai.azure.com/openai/v1/"
#   API_KEY  = "<your key>"         MODEL = "<your deployment name>"
# ----------------------------------------------------------------------------

DATABASE = "bank.db"
client = OpenAI(base_url=BASE_URL, api_key=API_KEY)


def describe_table(conn) -> str:
    """Build the 'map' of the table the AI needs: each column, its type, and
    example values. Example values matter: without them the AI might write
    personal_loan = 'Yes' or = 1, and the database stores 'yes'."""
    lines = ["Table: customers  (one row per bank customer)"]
    for _, name, col_type, *_ in conn.execute("PRAGMA table_info(customers)"):
        if name in ("first_name", "last_name", "email", "account_number", "routing_number"):
            lines.append(f"- {name} ({col_type})")
            continue
        values = [r[0] for r in conn.execute(
            f"SELECT DISTINCT {name} FROM customers WHERE {name} IS NOT NULL LIMIT 13")]
        if col_type == "TEXT" and len(values) <= 12:
            lines.append(f"- {name} (TEXT) allowed values: {values}")
        else:
            lo, hi = conn.execute(f"SELECT MIN({name}), MAX({name}) FROM customers").fetchone()
            lines.append(f"- {name} ({col_type}) e.g. {values[:3]} range {lo}..{hi}")
    return "\n".join(lines)


SQL_INSTRUCTIONS = """You turn a bank owner's question into ONE SQLite query.
Rules:
- Use only the table and columns listed below. Use the exact allowed values.
- Write a single SELECT statement. Never modify data.
- Reply with the SQL only. No explanation, no markdown.

{schema}"""

ANSWER_INSTRUCTIONS = """You explain a database result to a bank owner in one or two short sentences.
Use ONLY the numbers in the result. Do not add, estimate or round numbers that are not there.
If the result is empty, say no matching customers were found."""


def ask_ai(system: str, user: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        temperature=0,   # 0 = most predictable output, best for SQL
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
    )
    return response.choices[0].message.content.strip()


def clean_sql(text: str) -> str:
    """Models sometimes wrap SQL in ```sql fences - strip them."""
    text = re.sub(r"^```(?:sql)?\s*|\s*```$", "", text.strip(), flags=re.I)
    return text.strip().rstrip(";")


def answer(question: str) -> dict:
    # Read-only connection: even if the AI wrote DELETE, the database refuses.
    conn = sqlite3.connect(f"file:{DATABASE}?mode=ro", uri=True)
    try:
        sql = clean_sql(ask_ai(SQL_INSTRUCTIONS.format(schema=describe_table(conn)), question))
        rows = conn.execute(sql).fetchmany(20)
        columns = [d[0] for d in conn.execute(sql).description]
    finally:
        conn.close()
    result_text = f"columns: {columns}\nrows: {rows}"
    reply = ask_ai(ANSWER_INSTRUCTIONS, f"Question: {question}\nSQL used: {sql}\nResult:\n{result_text}")
    return {"question": question, "sql": sql, "rows": rows, "answer": reply}


def show(result: dict):
    print(f"\nQuestion: {result['question']}")
    print(f"SQL     : {result['sql']}")
    print(f"Result  : {result['rows'][:5]}{' ...' if len(result['rows']) > 5 else ''}")
    print(f"Answer  : {result['answer']}\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        show(answer(" ".join(sys.argv[1:])))
    else:
        while (q := input("Ask a question (or press Enter to quit): ").strip()):
            try:
                show(answer(q))
            except Exception as e:      # e.g. the AI wrote invalid SQL
                print(f"Sorry, that failed: {e}\n")
