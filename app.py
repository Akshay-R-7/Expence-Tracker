import json
from pathlib import Path

import pandas as pd
import streamlit as st

from database import create_tables, get_connection, set_status
from pipeline import handle_receipt

UPLOAD_DIR = Path("receipts/uploads")

st.title("AI Expense Tracker")
create_tables()

# ---------- 1. Upload ----------

st.subheader("Scan a receipt")
uploaded = st.file_uploader("Upload a receipt image", type=["jpg", "jpeg", "png", "pdf"])

if uploaded is not None and st.button("Scan receipt"):
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    save_path = UPLOAD_DIR / uploaded.name
    save_path.write_bytes(uploaded.getvalue())

    with st.spinner("Reading the receipt... this can take a minute"):
        receipt_id, result = handle_receipt(str(save_path))

    if result is None:
        st.info(f"This exact file was already processed as receipt #{receipt_id}.")
    elif result["flags"]:
        st.warning(f"Saved as receipt #{receipt_id}. It has flags, so it needs your review below.")
    else:
        st.success(f"Saved as receipt #{receipt_id}. No problems found.")

# ---------- 2. Review flagged receipts ----------

with get_connection() as conn:
    to_review = pd.read_sql_query(
        """
        SELECT id, image, merchant, date, total_cents, flags
        FROM receipts WHERE status = 'needs_review' ORDER BY id
        """,
        conn,
    )

st.subheader(f"Needs review ({len(to_review)})")
if to_review.empty:
    st.write("Nothing to review.")

for row in to_review.itertuples():
    total = f"{row.total_cents / 100:.2f} EUR" if pd.notna(row.total_cents) else "no total"
    label = f"#{row.id}  {row.merchant or 'Unknown'}  {row.date or ''}  {total}"

    with st.expander(label):
        for flag in json.loads(row.flags):
            st.write("- " + flag)
        if Path(row.image).exists():
            st.image(row.image, width=300)

        left, right = st.columns(2)
        if left.button("Approve", key=f"approve_{row.id}"):
            set_status(row.id, "approved")
            st.rerun()
        if right.button("Reject", key=f"reject_{row.id}"):
            set_status(row.id, "rejected")
            st.rerun()

# ---------- 3. All receipts ----------

with get_connection() as conn:
    receipts = pd.read_sql_query(
        "SELECT id, merchant, date, total_cents, status, flags FROM receipts ORDER BY id",
        conn,
    )

receipts["total"] = receipts["total_cents"] / 100
receipts["flags"] = receipts["flags"].apply(lambda text: len(json.loads(text)))

st.subheader("All receipts")
st.dataframe(
    receipts[["id", "merchant", "date", "total", "status", "flags"]],
    hide_index=True,
    column_config={"total": st.column_config.NumberColumn(format="%.2f")},
)

approved_total = receipts.loc[receipts["status"] == "approved", "total"].sum()
st.metric("Total spent (approved receipts only)", f"{approved_total:.2f} EUR")