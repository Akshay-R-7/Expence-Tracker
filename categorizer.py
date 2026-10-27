import re
import sys

# What each category means. ask.py reuses this, so both always agree.
CATEGORY_HELP = {
    "fruit_vegetables": "fresh fruit, vegetables, salad, herbs",
    "dairy_eggs": "milk, yogurt, cheese, butter and spreads, puddings, eggs",
    "meat_fish": "meat, sausage, ham, fish",
    "bread_bakery": "bread, rolls, wraps and tortillas, cakes",
    "snacks_sweets": "chips, chocolate, cookies and biscuits, candy, nuts",
    "drinks": "water, juice, soda, coffee, tea, beer, wine",
    "pantry": "pasta, rice, flour, sugar, salt, spices, oil, sauces, canned food",
    "frozen": "frozen food, ice cream",
    "household": "cleaning products, paper towels, bags, batteries",
    "personal_care": "soap, shampoo, toothpaste, cosmetics",
    "other": "anything that fits nowhere else",
}
CATEGORIES = list(CATEGORY_HELP)

# (keyword, english_name, category)
# The FIRST matching rule wins, so specific or tricky rules must come before general ones.
# A keyword with spaces around it (" tk ") only matches a whole word.
RULES = [
    # Frozen first: "TK Pizza Salami" is frozen food, not meat
    (" tk ", "frozen food", "frozen"),
    ("tiefkuehl", "frozen food", "frozen"),
    ("speiseeis", "ice cream", "frozen"),

    # Personal care before pantry: "Zahnpasta" is toothpaste, not pasta
    ("zahnpasta", "toothpaste", "personal_care"),
    ("zahncreme", "toothpaste", "personal_care"),
    ("duschgel", "shower gel", "personal_care"),
    ("shampoo", "shampoo", "personal_care"),
    ("seife", "soap", "personal_care"),
    (" deo", "deodorant", "personal_care"),

    # Household
    ("kuechenrolle", "paper towels", "household"),
    ("toilettenpapier", "toilet paper", "household"),
    ("spuel", "dish soap", "household"),
    ("waschmittel", "laundry detergent", "household"),
    ("muellbeutel", "bin bags", "household"),

    # Snacks and sweets before meat/dairy: "Lays KFC Chicken" is chips, "Milchschokolade" is chocolate
    ("lays", "chips", "snacks_sweets"),
    ("chips", "chips", "snacks_sweets"),
    ("salzstangen", "pretzel sticks", "snacks_sweets"),
    ("milka", "chocolate", "snacks_sweets"),
    ("schoko", "chocolate", "snacks_sweets"),
    ("keks", "cookies", "snacks_sweets"),
    ("haribo", "gummy candy", "snacks_sweets"),
    ("gummi", "gummy candy", "snacks_sweets"),
    ("nuesse", "nuts", "snacks_sweets"),

    # Dairy and eggs
    ("eier", "eggs", "dairy_eggs"),
    ("joghurt", "yogurt", "dairy_eggs"),
    ("pudding", "pudding", "dairy_eggs"),
    ("pud", "pudding", "dairy_eggs"),
    ("streichfett", "spread", "dairy_eggs"),
    ("butter", "butter", "dairy_eggs"),
    ("milch", "milk", "dairy_eggs"),
    ("kaese", "cheese", "dairy_eggs"),
    ("gouda", "cheese", "dairy_eggs"),
    ("quark", "quark", "dairy_eggs"),
    ("sahne", "cream", "dairy_eggs"),

    # Meat and fish before drinks: "Schweinefilet" contains "wein" (wine)
    ("haehnchen", "chicken", "meat_fish"),
    ("schwein", "pork", "meat_fish"),
    ("rind", "beef", "meat_fish"),
    ("hack", "minced meat", "meat_fish"),
    ("salami", "salami", "meat_fish"),
    ("schinken", "ham", "meat_fish"),
    ("wurst", "sausage", "meat_fish"),
    ("lachs", "salmon", "meat_fish"),
    ("thunfisch", "tuna", "meat_fish"),

    # Pantry before vegetables: "Tom.sauce" is tomato sauce, not tomatoes
    ("sauce", "sauce", "pantry"),
    ("ketchup", "ketchup", "pantry"),
    ("salz", "salt", "pantry"),
    ("zucker", "sugar", "pantry"),
    ("mehl", "flour", "pantry"),
    ("nudel", "pasta", "pantry"),
    ("spaghetti", "pasta", "pantry"),
    ("penne", "pasta", "pantry"),
    ("pasta", "pasta", "pantry"),
    (" reis ", "rice", "pantry"),
    ("oel", "oil", "pantry"),

    # Fruit and vegetables
    ("gurke", "cucumber", "fruit_vegetables"),
    ("tomate", "tomatoes", "fruit_vegetables"),
    ("kiwi", "kiwi", "fruit_vegetables"),
    ("apfel", "apples", "fruit_vegetables"),
    ("banane", "bananas", "fruit_vegetables"),
    ("kartoffel", "potatoes", "fruit_vegetables"),
    ("zwiebel", "onions", "fruit_vegetables"),
    ("paprika", "bell pepper", "fruit_vegetables"),
    ("karotte", "carrots", "fruit_vegetables"),
    ("moehre", "carrots", "fruit_vegetables"),
    ("salat", "salad", "fruit_vegetables"),

    # Bread and bakery
    ("tortilla", "tortillas", "bread_bakery"),
    ("toast", "toast bread", "bread_bakery"),
    ("broetchen", "bread rolls", "bread_bakery"),
    ("brot", "bread", "bread_bakery"),
    ("kuchen", "cake", "bread_bakery"),

    # Drinks
    ("wasser", "water", "drinks"),
    ("saft", "juice", "drinks"),
    (" cola ", "cola", "drinks"),
    ("kaffee", "coffee", "drinks"),
    (" tee ", "tea", "drinks"),
    ("bier", "beer", "drinks"),
    ("wein", "wine", "drinks"),
]

# Safety check: every rule must use a category that exists
for _keyword, _english, _category in RULES:
    assert _category in CATEGORY_HELP, f"Unknown category in rule: {_category}"


def normalize(name):
    """'K.Mischstreichfett' -> ' k mischstreichfett ' (lowercase, no umlauts, no punctuation)."""
    text = name.lower()
    for umlaut, replacement in {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}.items():
        text = text.replace(umlaut, replacement)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return f" {text.strip()} "


def categorize_name(name):
    """Return (english_name, category) for one item name. Unknown items -> (None, 'other')."""
    text = normalize(name)
    for keyword, english_name, category in RULES:
        if keyword in text:
            return english_name, category
    return None, "other"


def categorize_items(items):
    """Add 'english_name' and 'category' to each item dict."""
    for item in items:
        if item.get("name"):
            item["english_name"], item["category"] = categorize_name(item["name"])
        else:
            item["english_name"], item["category"] = None, None
    return items


if __name__ == "__main__":
    for name in sys.argv[1:]:
        english_name, category = categorize_name(name)
        print(f"{name:<22} -> {english_name}  ({category})")