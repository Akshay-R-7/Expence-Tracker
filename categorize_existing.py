import sys

from categorizer import categorize_items
from database import clear_categories, create_tables, items_without_category, set_item_category

create_tables()   # also runs the migration that adds the new columns

if "--all" in sys.argv:
    clear_categories()
    print("Cleared all existing categories, re-labelling everything")

rows = items_without_category()
print(f"{len(rows)} items without a category")

items = [{"id": item_id, "name": name} for item_id, name in rows]
items = categorize_items(items)

for item in items:
    print(f"{item['name']:<22} -> {item['english_name']}  ({item['category']})")
    if item["category"] is not None:
        set_item_category(item["id"], item["english_name"], item["category"])

print("Done")