import json
import sqlite3
from datetime import datetime

DB_PATH = "expenses.db"
VALID_STATUSES = ["needs_review", "approved", "rejected"]


def get_connection():
    """Open a connection to the database file (it is created if it doesn't exist)."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_tables():
    """Create the tables if they don't exist yet, then upgrade older databases."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS receipts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                image       TEXT NOT NULL,
                file_hash   TEXT,
                merchant    TEXT,
                date        TEXT,
                date_raw    TEXT,
                total_cents INTEGER,
                currency    TEXT,
                flags       TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'needs_review',
                created_at  TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_id   INTEGER NOT NULL REFERENCES receipts(id),
                name         TEXT,
                english_name TEXT,
                category     TEXT,
                quantity     REAL,
                price_cents  INTEGER
            )
        """)
        migrate(conn)


def column_names(conn, table):
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]


def migrate(conn):
    """Upgrade a database created by an older version of this code, without losing data."""
    if "status" not in column_names(conn, "receipts"):
        conn.execute(
            "ALTER TABLE receipts ADD COLUMN status TEXT NOT NULL DEFAULT 'needs_review'"
        )
        conn.execute("UPDATE receipts SET status = 'approved' WHERE flags = '[]'")

    item_columns = column_names(conn, "items")
    if "english_name" not in item_columns:
        conn.execute("ALTER TABLE items ADD COLUMN english_name TEXT")
    if "category" not in item_columns:
        conn.execute("ALTER TABLE items ADD COLUMN category TEXT")


def to_cents(amount):
    """15.1 -> 1510. Money is stored as whole cents to avoid float errors."""
    if amount is None:
        return None
    return round(amount * 100)


def to_iso_date(date_text):
    """'03.09.26' -> '2026-09-03', a format that sorts and groups correctly."""
    if date_text is None:
        return None
    try:
        return datetime.strptime(date_text, "%d.%m.%y").strftime("%Y-%m-%d")
    except ValueError:
        return None


def save_result(result):
    """Save one pipeline result (receipt + its items) and return the new receipt id."""
    data = result["data"]
    status = "needs_review" if result["flags"] else "approved"
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO receipts
                (image, file_hash, merchant, date, date_raw, total_cents,
                 currency, flags, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result["image"],
                result.get("file_hash"),
                data.get("merchant"),
                to_iso_date(data.get("date")),
                data.get("date"),
                to_cents(data.get("total")),
                data.get("currency"),
                json.dumps(result["flags"], ensure_ascii=False),
                status,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        receipt_id = cursor.lastrowid

        for item in data.get("items") or []:
            conn.execute(
                """
                INSERT INTO items
                    (receipt_id, name, english_name, category, quantity, price_cents)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    receipt_id,
                    item.get("name"),
                    item.get("english_name"),
                    item.get("category"),
                    item.get("quantity"),
                    to_cents(item.get("price")),
                ),
            )
    return receipt_id


def find_by_hash(file_hash):
    """Return the id of a receipt with this exact file, or None."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM receipts WHERE file_hash = ?", (file_hash,)
        ).fetchone()
    return row[0] if row else None


def find_similar(merchant, date, total_cents):
    """Return ids of non-rejected receipts with the same merchant, date and total."""
    if merchant is None or date is None or total_cents is None:
        return []
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id FROM receipts
            WHERE merchant = ? AND date = ? AND total_cents = ? AND status != 'rejected'
            """,
            (merchant, date, total_cents),
        ).fetchall()
    return [row[0] for row in rows]


def set_status(receipt_id, status):
    """Mark a receipt as approved, rejected or needs_review."""
    if status not in VALID_STATUSES:
        raise ValueError(f"Unknown status: {status}")
    with get_connection() as conn:
        conn.execute(
            "UPDATE receipts SET status = ? WHERE id = ?", (status, int(receipt_id))
        )


def items_without_category():
    """Items saved before categories existed (or where categorizing failed)."""
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, name FROM items WHERE category IS NULL AND name IS NOT NULL"
        ).fetchall()


def set_item_category(item_id, english_name, category):
    with get_connection() as conn:
        conn.execute(
            "UPDATE items SET english_name = ?, category = ? WHERE id = ?",
            (english_name, category, int(item_id)),
        )


def clear_categories():
    """Remove all categories, so they can be re-labelled (e.g. after improving the prompt)."""
    with get_connection() as conn:
        conn.execute("UPDATE items SET english_name = NULL, category = NULL")