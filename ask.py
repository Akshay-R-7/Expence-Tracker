import sqlite3
import sys
from datetime import date

import ollama
from pydantic import BaseModel

from categorizer import CATEGORY_HELP

MODEL = "qwen2.5vl:3b"
DB_URI = "file:expenses.db?mode=ro"   # ro = read-only: this connection can never change data
MAX_ROWS = 50
MAX_ATTEMPTS = 3

NOTHING_FOUND = "I couldn't find any matching expenses."
NOT_ALLOWED = "I can only look at your expenses, not change or delete them."
GAVE_UP = "Sorry, I couldn't work out how to answer that question."

SCHEMA_DESCRIPTION = """
Table receipts:
  id (integer), merchant (text), date (text, format YYYY-MM-DD),
  total_cents (integer, the receipt total in cents), currency (text),
  status (text: 'approved', 'needs_review' or 'rejected')
Table items:
  id (integer), receipt_id (integer, links to receipts.id),
  name (text, as printed on the receipt, often German and abbreviated),
  english_name (text, plain English description, e.g. 'whole milk'),
  category (text, one of the categories listed below),
  quantity (number), price_cents (integer, line total in cents)
"""


class SqlQuery(BaseModel):
    sql: str


class ForbiddenQuery(Exception):
    """The AI wrote something other than a SELECT. Retrying won't help."""


def known_merchants():
    """The store names that actually exist in the database."""
    conn = sqlite3.connect(DB_URI, uri=True)
    try:
        rows = conn.execute(
            "SELECT DISTINCT merchant FROM receipts "
            "WHERE merchant IS NOT NULL ORDER BY merchant LIMIT 50"
        ).fetchall()
    finally:
        conn.close()
    return [row[0] for row in rows]


def build_prompt(question):
    today = date.today()
    this_month = today.strftime("%Y-%m")
    merchants = ", ".join(known_merchants()) or "none yet"
    categories = "\n".join(f"  {name}: {help_text}" for name, help_text in CATEGORY_HELP.items())
    return f"""You write SQLite queries for a personal expense database.
{SCHEMA_DESCRIPTION}
Item categories:
{categories}

Rules:
- Store names (merchants) in the database: {merchants}.
  If the question mentions one of these stores, filter on receipts.merchant, not on item names.
- For spending questions, count only receipts with status = 'approved'.
- Money is stored in cents. Divide by 100.0 to return euros.
- For totals, use receipts.total_cents. Only join the items table for questions
  about individual items.
- Only filter by date if the question mentions a time period. Today's date is
  {today.isoformat()}. Use it only for relative periods like "this month".
- Compare text with LIKE and % wildcards, so upper and lower case don't matter.
- Product questions: use EITHER a category OR a name search, never both together.
  If the question names a whole group (like sweets, fruit, dairy, drinks or household
  items), filter only on i.category.
  If it names a specific product (like milk, bananas or coffee), search i.name and
  i.english_name.
- Write exactly one SELECT query. Never modify data.

Examples:
Question: How much did I spend in September 2026?
SQL: SELECT SUM(total_cents) / 100.0 AS total_euros FROM receipts WHERE status = 'approved' AND date LIKE '2026-09%'

Question: How much did I spend this month?
SQL: SELECT SUM(total_cents) / 100.0 AS total_euros FROM receipts WHERE status = 'approved' AND date LIKE '{this_month}%'

Question: How much did I spend at Rewe?
SQL: SELECT SUM(total_cents) / 100.0 AS total_euros FROM receipts WHERE status = 'approved' AND merchant LIKE '%rewe%'

Question: How much did I spend on milk?
SQL: SELECT SUM(i.price_cents) / 100.0 AS total_euros FROM items i JOIN receipts r ON i.receipt_id = r.id WHERE r.status = 'approved' AND (i.name LIKE '%milk%' OR i.english_name LIKE '%milk%')

Question: How much did I spend on drinks?
SQL: SELECT SUM(i.price_cents) / 100.0 AS total_euros FROM items i JOIN receipts r ON i.receipt_id = r.id WHERE r.status = 'approved' AND i.category = 'drinks'

Now write the query for this question.
Question: {question}"""


def generate_sql(question, previous_sql=None, error=None):
    """Step 1: the AI translates the question into SQL (and fixes it if it failed)."""
    prompt = build_prompt(question)
    if previous_sql is not None:
        prompt += f"""

Your previous query was:
{previous_sql}
It failed with this error:
{error}
Write a corrected query."""

    response = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        format=SqlQuery.model_json_schema(),
        options={"temperature": 0},
    )
    return SqlQuery.model_validate_json(response["message"]["content"]).sql


def run_sql(sql):
    """Step 2: run the query on a read-only connection."""
    if not sql.strip().lower().startswith(("select", "with")):
        raise ForbiddenQuery(sql)
    conn = sqlite3.connect(DB_URI, uri=True)
    try:
        cursor = conn.execute(sql)
        columns = [column[0] for column in cursor.description]
        rows = cursor.fetchmany(MAX_ROWS)
    finally:
        conn.close()
    return columns, rows


def is_empty(rows):
    """True if there are no rows, or every value in them is None."""
    return not rows or all(value is None for row in rows for value in row)


def phrase_answer(question, columns, rows):
    """Step 3: the AI turns a (non-empty) result into a short, friendly answer."""
    prompt = f"""A user asked about their expenses: {question}

The database returned these columns: {columns}
and these rows: {rows}

This result contains the answer. State it in one or two short, friendly sentences.
Amounts are in euros. Write amounts with two decimals, like 15.10 euros.
Use only the numbers in the result. Do not invent numbers."""

    response = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0},
    )
    return response["message"]["content"]


def ask(question):
    """Question -> SQL (with up to MAX_ATTEMPTS tries) -> result -> answer."""
    result = {"question": question, "sql": None, "columns": [], "rows": [],
              "attempts": 0, "error": None, "answer": None}
    sql, error = None, None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        result["attempts"] = attempt
        sql = generate_sql(question, sql, error)
        result["sql"] = sql
        try:
            columns, rows = run_sql(sql)
            break
        except ForbiddenQuery:
            result["error"] = "The AI wrote a query that would change data. Blocked."
            result["answer"] = NOT_ALLOWED
            return result
        except sqlite3.Error as e:
            error = str(e)
            result["error"] = error
    else:
        result["answer"] = GAVE_UP
        return result

    result["error"] = None
    result["columns"], result["rows"] = columns, rows

    if is_empty(rows):
        result["answer"] = NOTHING_FOUND      # decided by code, not by the AI
    else:
        result["answer"] = phrase_answer(question, columns, rows)
    return result


if __name__ == "__main__":
    question = " ".join(sys.argv[1:])
    result = ask(question)
    print("SQL:     ", result["sql"])
    print("Attempts:", result["attempts"])
    if result["error"]:
        print("Error:   ", result["error"])
    print("Rows:    ", result["rows"])
    print("Answer:  ", result["answer"])