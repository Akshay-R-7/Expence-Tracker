import json

with open("receipts/receipt1_result.json", encoding="utf-8") as f:
    data = json.load(f)

flags = []

items_sum_cents = 0
for item in data["items"]:
    items_sum_cents += round(item["price"] * 100)

total_cents = round(data["total"] * 100)

print(f"Sum of items: {items_sum_cents / 100:.2f}")
print(f"Total on receipt: {total_cents / 100:.2f}")

if items_sum_cents != total_cents:
    flags.append(f"Items add up to {items_sum_cents / 100:.2f}, but the total says {total_cents / 100:.2f}")

if flags:
    for flag in flags:
        print("FLAG:", flag)
else:
    print("No problems found")