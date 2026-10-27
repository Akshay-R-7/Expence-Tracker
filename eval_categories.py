import json
import time

from categorizer import categorize_items

LABELS_FILE = "eval/category_labels.json"


def main():
    with open(LABELS_FILE, encoding="utf-8") as f:
        labels = json.load(f)

    items = [{"name": label["name"]} for label in labels]

    start = time.time()
    categorize_items(items)
    elapsed = time.time() - start

    correct = 0
    for expected, item in zip(labels, items):
        is_correct = item["category"] == expected["category"]
        correct += is_correct
        mark = "OK " if is_correct else "XX "
        print(
            f"{mark} {item['name']:<22} expected {expected['category']:<17} "
            f"got {str(item['category']):<17} ({item['english_name']})"
        )

    print()
    print(f"Accuracy: {correct}/{len(labels)} = {correct / len(labels):.0%}")
    print(f"Time:     {elapsed:.3f} seconds")


if __name__ == "__main__":
    main()