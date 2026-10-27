from typing import Optional

import ollama
from pydantic import BaseModel

MODEL = "qwen2.5vl:3b"


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


PROMPT = """First decide two things:
- is_receipt: true only if the image clearly shows a shopping receipt or invoice.
- readable: true only if you can actually read the text on it.
If either is false, set every other field to null and items to an empty list.

Then extract the data from the receipt:
- merchant: the store name only, without the address
- address: the store's street and city
- date: exactly as printed on the receipt
- items: every purchased item. price is the line total for that item. quantity is how many were bought (1 if no quantity is shown)
- total: the final amount paid
- currency: only if it is printed on the receipt
Use a dot as the decimal point. If something is not visible on the receipt, use null. Never guess or invent values."""


def extract_receipt(image_path):
    """Send the image to the local model and return a checked Receipt object."""
    response = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT, "images": [image_path]}],
        format=Receipt.model_json_schema(),
        options={"temperature": 0, "num_ctx": 8192},
    )
    return Receipt.model_validate_json(response["message"]["content"])