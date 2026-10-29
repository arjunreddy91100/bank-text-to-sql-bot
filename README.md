# Bank Text-to-SQL Bot

Ask a bank's customer database questions in plain English and get exact answers, with no hallucinated numbers.

The bot runs on a **local large language model (LLM)**: **`qwen2.5-coder:7b`**, served by **[Ollama](https://ollama.com)** on my own PC. No API key, no cloud, no cost, and customer data never leaves the machine.

```
Question: How many customers have a personal loan?
SQL     : SELECT COUNT(*) FROM customers WHERE personal_loan = 'yes'
Answer  : 6248 customers have a personal loan.
```

---

## The LLM

| | |
| --- | --- |
| **Model** | `qwen2.5-coder:7b` (Qwen 2.5 Coder, 7 billion parameters, ~4.7 GB) |
| **Runs on** | Ollama, locally on my Windows PC |
| **Connected through** | Ollama's OpenAI-compatible API at `http://localhost:11434/v1`, using the `openai` Python library |
| **Temperature** | `0`, for predictable output and consistent SQL |

**Why this model?** It is trained heavily on code, including SQL, so it writes correct queries reliably. It is small enough to run on a normal laptop. I compared it with the other models I had installed:

| Model | Decision |
| --- | --- |
| `gemma3:270m` | Too small to write SQL reliably |
| `phi3` | General-purpose, weaker at code |
| `gpt-oss:120b-cloud` | Strong, but runs on Ollama's servers, so customer data would leave the machine |
| **`qwen2.5-coder:7b`** | **Chosen:** code-specialized, fully local |

**What the LLM does, and what it does not do.** The LLM is used twice per question, and only to translate:

1. **English to SQL.** It reads the question plus a map of the table and writes one SQL query.
2. **Result to English.** It turns the database's result into one short sentence.

It **never calculates**. Every count, average and total comes from the database. This is the main design decision of the project, and the reason it does not hallucinate numbers (see [the bug the tests caught](#a-bug-the-tests-caught)).

Switching to a cloud model later (for example Azure OpenAI) is a three-line change to `BASE_URL`, `API_KEY` and `MODEL` in `step2_ask.py`.

---

## How it works

Three pieces work together:

| Piece | Role | Good at | Bad at |
| --- | --- | --- | --- |
| **`bank.db`** (SQLite) | Stores 41,188 customers | Exact counting | Understanding English |
| **LLM** (`qwen2.5-coder:7b`) | Translator | Understanding English, writing SQL | Counting |
| **Python** | Connects the two | Glue, masking, testing | |

One question, start to finish:

```
1. Bank owner types:  "How many customers have a personal loan?"
2. Python sends the LLM:  instructions + a map of the table + the question
3. LLM replies:  SELECT COUNT(*) FROM customers WHERE personal_loan = 'yes'
4. Python runs that SQL on bank.db (read-only), and the database counts:  6248
5. Python sends 6248 back to the LLM:  "explain this in one sentence"
6. Owner sees:  "6248 customers have a personal loan."
```

**The table map is what makes the SQL accurate.** Python sends the LLM every column name, its type, and its allowed values, for example `personal_loan (TEXT) allowed values: ['no', 'yes', 'unknown']`. Without it, the model might write `'Yes'` with a capital Y and the database would match nothing.

---

## Safety and accuracy

- **No AI arithmetic.** Totals come from `SELECT COUNT(*)` on the database, never from the model counting rows.
- **Private data masked** before it is shown *or sent to the LLM*:

  | Field | Stored | Shown |
  | --- | --- | --- |
  | Last name | Johnson | J. |
  | Email | robert.johnson5@example.com | r***@example.com |
  | Account number | 3410529190 | ******9190 |
  | Routing number | 104332181 | *****2181 |

  Masking checks both column names and value patterns, so a renamed column (`account_number AS acct`) is still caught.
- **Read-only database connection.** If the model ever wrote `DELETE`, SQLite refuses.
- **Local model.** Customer data is never sent to an outside service.

---

## Results

Tested on Windows with Python 3.13.1, Ollama 0.40.13 and `qwen2.5-coder:7b`.

| Test | What it checks | Score |
| --- | --- | --- |
| `step2_test_bot.py` | 8 counting questions vs. a ground-truth answer key | **8/8** |
| `step3_test_privacy.py` | 3 list questions: correct total and no leaked private data | **3/3** |

### A bug the tests caught

The first version passed 8/8 counting questions. Then a list question exposed a hallucination:

| | Step 2 (before) | Step 3 (after) |
| --- | --- | --- |
| "Show me the customers with a personal loan" | "There are **22** customers" | "There are **6248** customers" |
| Who counted | The LLM, from a 20-row sample | The database, all rows |
| Account number shown | `3410529190` | `******9190` |

**Cause:** the LLM was shown only 20 sample rows and counted them itself.
**Fix:** the database counts the full result with `SELECT COUNT(*) FROM (<query>)`, and the LLM is told to use that number and never count by itself. Private fields are masked before the LLM sees them.

---

## Run it

Requirements: Python 3.10+ and [Ollama](https://ollama.com).

```bash
ollama pull qwen2.5-coder:7b
pip install -r requirements.txt

python step1_build_database.py      # builds bank.db from the CSV (one time)
python check_answer_key.py          # true answers, straight from the database

python step3_ask.py "How many students opened a term deposit?"
python step3_ask.py                 # interactive mode

python step2_test_bot.py            # counting accuracy test
python step3_test_privacy.py        # list + privacy test
```

`bank.db` is not committed. `step1_build_database.py` rebuilds the exact same file every time (fixed random seed).

---

## Files

| File | Purpose |
| --- | --- |
| `step1_build_database.py` | Loads the CSV, renames columns to plain English, adds synthetic identities, saves `bank.db` |
| `check_answer_key.py` | Ground-truth answers for the test questions |
| `step2_ask.py` | First version of the bot (kept to show the bug) |
| `step2_test_bot.py` | Tests the bot against the answer key |
| `step3_ask.py` | Fixed bot: database-computed totals + private data masking |
| `step3_test_privacy.py` | Tests list questions for correct totals and leaks |

---

## Data

Customer attributes come from the [Bank Marketing dataset](https://archive.ics.uci.edu/dataset/222/bank+marketing) (Moro et al., 2014, UCI Machine Learning Repository), via Kaggle.

Names, emails, account numbers and the routing number are **synthetic**. Names come from the Faker library, emails use the reserved `example.com` domain, and the routing number deliberately fails the ABA checksum, so it cannot match a real bank.

---

## Next steps

- Refuse off-topic or unanswerable questions instead of guessing
- Add policy documents and route each question to SQL or to document search (RAG)
- Simple web chat interface

## License

MIT
