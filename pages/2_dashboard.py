import pandas as pd
import streamlit as st

from database import create_tables, get_connection

st.title("Spending dashboard")
create_tables()

# ---------- Load approved data only ----------

with get_connection() as conn:
    receipts = pd.read_sql_query(
        """
        SELECT id, merchant, date, total_cents
        FROM receipts
        WHERE status = 'approved' AND total_cents IS NOT NULL
        """,
        conn,
    )
    items = pd.read_sql_query(
        """
        SELECT r.date, i.name, i.english_name, i.category, i.price_cents
        FROM items i JOIN receipts r ON i.receipt_id = r.id
        WHERE r.status = 'approved' AND i.price_cents IS NOT NULL
        """,
        conn,
    )

if receipts.empty:
    st.info("No approved receipts yet. Scan and approve some receipts first.")
    st.stop()

# Cents -> euros only for display; "2026-09-03" -> "2026-09" for grouping by month
receipts["total"] = receipts["total_cents"] / 100
receipts["month"] = receipts["date"].str[:7]
items["price"] = items["price_cents"] / 100
items["month"] = items["date"].str[:7]

# ---------- Period filter ----------

months = sorted(receipts["month"].dropna().unique(), reverse=True)
period = st.selectbox("Period", ["All time"] + list(months))
if period != "All time":
    receipts = receipts[receipts["month"] == period]
    items = items[items["month"] == period]

# ---------- Key numbers ----------

left, middle, right = st.columns(3)
left.metric("Total spent", f"{receipts['total'].sum():.2f} EUR")
middle.metric("Receipts", len(receipts))
right.metric("Average receipt", f"{receipts['total'].mean():.2f} EUR")

# ---------- Charts ----------

st.subheader("Spending per month")
st.bar_chart(receipts.groupby("month")["total"].sum(), y_label="EUR")

st.subheader("Spending per category")
per_category = items.groupby(items["category"].fillna("uncategorized"))["price"].sum()
st.bar_chart(per_category.sort_values(ascending=False), y_label="EUR")

st.subheader("Spending per store")
per_store = receipts.groupby(receipts["merchant"].fillna("unknown"))["total"].sum()
st.bar_chart(per_store.sort_values(ascending=False), y_label="EUR")

st.subheader("Top 10 items")
item_label = items["english_name"].fillna(items["name"])
top_items = items.groupby(item_label)["price"].sum().sort_values(ascending=False).head(10)
st.dataframe(top_items.rename("spent (EUR)").round(2))