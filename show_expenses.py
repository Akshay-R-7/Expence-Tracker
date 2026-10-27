import json
import sqlite3

conn = sqlite3.connect("expenses.db")

print("=== All receipts ===")
rows = conn.execute(
    "SELECT id, merchant, date, total_cents, flags FROM receipts ORDER BY id"
).fetchall()
for receipt_id, merchant, date, total_cents, flags in rows:
    total = f"{total_cents / 100:.2f}" if total_cents is not None else "-"
    flag_count = len(json.loads(flags))
    print(f"#{receipt_id}  {merchant or '-':<12} {date or '-':<11} {total:>8}  flags: {flag_count}")

print("\n=== Items on receipt #1 ===")
items = conn.execute(
    "SELECT name, quantity, price_cents FROM items WHERE receipt_id = 1"
).fetchall()
for name, quantity, price_cents in items:
    print(f"{name:<22} x{quantity:g}  {price_cents / 100:.2f}")

conn.close()