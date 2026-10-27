import json
import time
import ollama

image_path = "receipts/blank.jpg"

prompt = """Read this receipt and return ONLY a JSON object with these fields:
{
  "merchant": "store name",
  "date": "date as printed on the receipt",
  "items": [{"name": "item name", "price": 0.00}],
  "total": 0.00,
  "currency": "EUR"
}
Use a dot as the decimal point in numbers. If you cannot read a field, use null."""

start = time.time()
response = ollama.chat(
    model="qwen2.5vl:3b",
    messages=[{"role": "user", "content": prompt, "images": [image_path]}],
    format="json",
)
print(f"Took {time.time() - start:.1f} seconds")

raw = response["message"]["content"]
print("Raw reply from AI:\n", raw)

data = json.loads(raw)
print("Merchant:", data["merchant"])
print("Total:", data["total"])
print("Number of items:", len(data["items"]))
with open("receipts/blank_result.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
print("Saved to receipts/blank_result.json")