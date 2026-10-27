from datetime import datetime

EMPTY_VALUES = ["null", "none", "", "n/a"]


# ---------- Cleaning ----------

def clean_value(value):
    """Turn the AI's text versions of 'nothing' into a real None."""
    if isinstance(value, str) and value.strip().lower() in EMPTY_VALUES:
        return None
    return value


def clean_data(data):
    """Clean every field and drop placeholder items with no name and no price."""
    for field in ["merchant", "address", "date", "currency", "total"]:
        data[field] = clean_value(data.get(field))
    cleaned_items = []
    for item in data.get("items") or []:
        name = clean_value(item.get("name"))
        price = clean_value(item.get("price"))
        if name is None and not price:
            continue
        cleaned_items.append({
            "name": name,
            "quantity": clean_value(item.get("quantity")),
            "price": price,
        })
    data["items"] = cleaned_items
    return data


# ---------- Checks ----------

def check_is_receipt(data, flags):
    if data.get("is_receipt") is False:
        flags.append("This image does not appear to be a receipt")
    elif data.get("readable") is False:
        flags.append("The receipt is not readable")
    elif not data.get("items") and data.get("total") is None:
        flags.append("No items and no total found: this image may not be a receipt")


def check_missing_fields(data, flags):
    for field in ["merchant", "date", "total"]:
        if data.get(field) is None:
            flags.append(f"Missing {field}: the AI could not read it")
    if not data.get("items"):
        flags.append("No items found: the AI could not read any line items")
    total = data.get("total")
    if total is not None and total <= 0:
        flags.append(f"Total is {total:.2f}: a real receipt should have a positive total")


def check_total(data, flags):
    if data.get("total") is None:
        return
    items = data.get("items")
    if not items:
        return
    items_sum_cents = 0
    for item in items:
        price = item.get("price")
        if price is None:
            flags.append("Could not verify the total because at least one price is missing")
            return
        items_sum_cents += round(price * 100)
    total_cents = round(data["total"] * 100)
    if items_sum_cents != total_cents:
        flags.append(
            f"Items add up to {items_sum_cents / 100:.2f}, "
            f"but the total says {total_cents / 100:.2f}"
        )


def check_date(data, flags):
    date_text = data.get("date")
    if date_text is None:
        return
    try:
        date = datetime.strptime(date_text, "%d.%m.%y")
    except ValueError:
        flags.append(f"Date '{date_text}' is not in the expected format DD.MM.YY")
        return
    if date > datetime.now():
        flags.append(f"Date {date_text} is in the future")


def check_prices(data, flags):
    items = data.get("items")
    if not items:
        return
    for item in items:
        price = item.get("price")
        if price is None:
            flags.append(f"Price missing for '{item.get('name')}'")
        elif price <= 0:
            flags.append(f"Price for '{item.get('name')}' is zero or negative: {price}")
        elif price > 100:
            flags.append(f"Price for '{item.get('name')}' looks unusually high: {price:.2f}")


# ---------- Run everything ----------

def run_checks(data):
    """Run all checks and return the list of flags."""
    flags = []
    check_is_receipt(data, flags)
    if not flags:
        check_missing_fields(data, flags)
        check_total(data, flags)
        check_date(data, flags)
        check_prices(data, flags)
    return flags