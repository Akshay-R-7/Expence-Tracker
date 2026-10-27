import json
import time
from typing import Optional

import ollama
from pydantic import BaseModel
import sys
from PIL import Image, ImageStat


class Item(BaseModel):
    name: Optional[str]
    quantity: Optional[float]
    price: Optional[float]


class Receipt(BaseModel):
    is_receipt: bool
    readable: bool
    merchant: Optional[str]
    address: Optional[str]
    date: Optional[str]
    items: list[Item]
    total: Optional[float]
    currency: Optional[str]


IMAGE_PATH = "receipts/bmv_small.jpg"
OUTPUT_PATH = "receipts/receiptBMV_results.json"



gray = Image.open(IMAGE_PATH).convert("L")
contrast = ImageStat.Stat(gray).stddev[0]
print(f"Image contrast: {contrast:.1f}")

if contrast < 10:
    print("FLAG: The image looks blank. Skipping the AI.")
    empty = Receipt(
        is_receipt=False, readable=False,
        merchant=None, address=None, date=None,
        items=[], total=None, currency=None,
    )
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(empty.model_dump(), f, indent=2, ensure_ascii=False)
    sys.exit()

prompt = """Extract the data from this receipt.
- merchant: the store name only, without the address
- address: the store's street and city
- date: exactly as printed on the receipt
- items: every purchased item. price is the line total for that item. quantity is how many were bought (1 if no quantity is shown)
- total: the final amount paid
- currency: only if it is printed on the receipt
Use a dot as the decimal point. If something is not visible on the receipt, use null. Never guess or invent values."""

start = time.time()
response = ollama.chat(
    model="qwen2.5vl:3b",
    messages=[{"role": "user", "content": prompt, "images": [IMAGE_PATH]}],
    format=Receipt.model_json_schema(),
    options={"temperature": 0},
)
print(f"Took {time.time() - start:.1f} seconds")

raw = response["message"]["content"]
print("Raw reply from AI:\n", raw)

receipt = Receipt.model_validate_json(raw)

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(receipt.model_dump(), f, indent=2, ensure_ascii=False)
print("Saved to", OUTPUT_PATH)