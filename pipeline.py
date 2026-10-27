import json
import sys
import time

from image_prep import prepare_image, file_hash
from extractor import Receipt, extract_receipt
from checks import clean_data, run_checks
from categorizer import categorize_items
from database import (
    create_tables, save_result, find_by_hash, find_similar, to_cents, to_iso_date,
)

CONTRAST_THRESHOLD = 10


def process_receipt(image_path):
    """One image in, one complete result (data + flags) out."""
    resized_path, contrast = prepare_image(image_path)

    if contrast < CONTRAST_THRESHOLD:
        receipt = Receipt(
            is_receipt=False, readable=False,
            merchant=None, address=None, date=None,
            items=[], total=None, currency=None,
        )
        data = receipt.model_dump()
        flags = [f"The image looks blank (contrast {contrast:.1f}), so the AI was skipped"]
    else:
        receipt = extract_receipt(resized_path)
        data = clean_data(receipt.model_dump())
        flags = run_checks(data)

        # Optional enrichment: if it fails, keep the receipt without categories
        try:
            data["items"] = categorize_items(data["items"])
        except Exception as error:
            print("Categorizing failed, continuing without categories:", error)

    return {
        "image": image_path,
        "contrast": round(contrast, 1),
        "data": data,
        "flags": flags,
    }


def handle_receipt(image_path):
    """The full workflow for one uploaded file.

    Returns (receipt_id, result).
    If the exact file was processed before, result is None and receipt_id is the old id.
    """
    create_tables()

    # Level 1: exactly the same file uploaded again -> skip before the AI runs
    fingerprint = file_hash(image_path)
    existing_id = find_by_hash(fingerprint)
    if existing_id is not None:
        return existing_id, None

    result = process_receipt(image_path)
    result["file_hash"] = fingerprint

    # Level 2: a different file showing the same purchase -> flag it, let the user decide
    data = result["data"]
    similar_ids = find_similar(
        data.get("merchant"), to_iso_date(data.get("date")), to_cents(data.get("total"))
    )
    for other_id in similar_ids:
        result["flags"].append(
            f"Possible duplicate of receipt #{other_id}: same merchant, date and total"
        )

    output_path = image_path.rsplit(".", 1)[0] + "_result.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    receipt_id = save_result(result)
    return receipt_id, result


if __name__ == "__main__":
    start = time.time()
    receipt_id, result = handle_receipt(sys.argv[1])

    if result is None:
        print(f"This exact file was already processed as receipt #{receipt_id}. Skipping.")
        sys.exit()

    print(f"Took {time.time() - start:.1f} seconds")
    print("Saved to database with id", receipt_id)
    for flag in result["flags"]:
        print("FLAG:", flag)
    if not result["flags"]:
        print("No problems found")