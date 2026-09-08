import re
from concurrent.futures import ThreadPoolExecutor

from blinkit import get_blinkit_products
from zepto_network import get_zepto_products
from instamart import get_instamart_products


# Keep quantity parsing separate from product-identity matching.
_QUANTITY_UNITS = r"ml|ltr|litres?|liter(?:s)?|l|kg|g|pcs|pc|pieces?|units?"
_PACKAGING_WORDS = {
    "pack", "packet", "package", "pouch", "bottle", "can", "jar",
    "box", "carton", "sachet", "container", "tetra",
}


def _normalise_quantity(amount, unit):
    amount = float(amount)
    unit = unit.lower()
    if unit in {"l", "ltr", "litre", "litres", "liter", "liters"}:
        return amount * 1000, "ml"
    if unit == "kg":
        return amount * 1000, "g"
    if unit in {"pc", "piece", "pieces", "unit", "units"}:
        return amount, "pcs"
    return amount, unit


def normalize_size(text):
    """Return per-item size, pack count, and total size from retail text."""
    if not text:
        return None

    text = text.lower()
    number = r"\d+(?:\.\d+)?"
    patterns = (
        rf"(?P<count>{number})\s*(?:x|\u00d7)\s*(?P<amount>{number})\s*(?P<unit>{_QUANTITY_UNITS})\b",
        rf"(?P<amount>{number})\s*(?P<unit>{_QUANTITY_UNITS})\b\s*(?:x|\u00d7)\s*(?P<count>{number})\b",
    )
    match = None
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            break

    if match:
        pack_count = float(match.group("count"))
        amount, unit = _normalise_quantity(match.group("amount"), match.group("unit"))
    else:
        match = re.search(rf"(?P<amount>{number})\s*(?P<unit>{_QUANTITY_UNITS})\b", text)
        if not match:
            return None
        amount, unit = _normalise_quantity(match.group("amount"), match.group("unit"))
        pack_match = re.search(
            rf"\b(?:pack|packet|package|box|carton)\s*(?:of\s*)?(?P<count>{number})\b",
            text,
        )
        pack_count = float(pack_match.group("count")) if pack_match else 1.0

    if amount <= 0 or pack_count <= 0:
        return None
    return {
        "amount": amount,
        "unit": unit,
        "pack_count": pack_count,
        "total_amount": amount * pack_count,
    }


def normalize_name(name):
    """Normalize text without discarding product/variant descriptors."""
    if not name:
        return ""

    name = name.lower()
    name = re.sub(
        r"\b\d+(?:\.\d+)?\s*(?:days?|months?|years?)\s+shelf\s+life\b",
        " ",
        name,
    )
    # Strip full multi-pack expressions before removing their component size.
    name = re.sub(
        rf"\d+(?:\.\d+)?\s*(?:x|\u00d7)\s*\d+(?:\.\d+)?\s*(?:{_QUANTITY_UNITS})\b",
        " ", name,
    )
    name = re.sub(
        rf"\d+(?:\.\d+)?\s*(?:{_QUANTITY_UNITS})\b\s*(?:x|\u00d7)\s*\d+(?:\.\d+)?\b",
        " ", name,
    )
    name = re.sub(rf"\d+(?:\.\d+)?\s*(?:{_QUANTITY_UNITS})\b", " ", name)
    name = re.sub(
        r"\b(?:pack|packet|package|box|carton)\s*(?:of\s*)?\d+(?:\.\d+)?\b",
        " ", name,
    )
    name = re.sub(
        r"\b\d+(?:\.\d+)?\s*(?:pack|packet|package|box|carton|pouch|bottle|can|jar|sachet|container)\b",
        " ", name,
    )
    name = re.sub(r"[^a-z0-9\s]", " ", name)
    return " ".join(word for word in name.split() if word not in _PACKAGING_WORDS)


def get_product_identity(name, variant=""):
    """Return a conservative category-agnostic identity.

    All product, brand, variant, flavour, and type words are retained. Unknown
    differences therefore prevent a comparison instead of becoming a false
    positive. Only physical quantities and generic package presentation are
    excluded.
    """
    words = " ".join([normalize_name(name), normalize_name(variant)]).split()
    return " ".join(dict.fromkeys(words))


def _identity_signature(identity):
    """Use order-independent equality only for an already exact token set."""
    return frozenset(identity.split())


def name_matches(product, query):
    """Use the search query only to filter candidates, never as identity."""
    query_name = normalize_name(query)
    product_name = normalize_name(product.get("name", ""))
    if not query_name or not product_name:
        return False
    query_words = set(query_name.split())
    product_words = set(product_name.split())
    return (next(iter(query_words)) in product_words if len(query_words) == 1
            else query_words.issubset(product_words))


def find_name_matches(products, query):
    return [product for product in products if name_matches(product, query)]


def get_product_size(product):
    """Parse both fields so title-level pack counts are retained."""
    return normalize_size(f"{product.get('variant', '')} {product.get('name', '')}")


def group_by_size(products):
    """Exact groups require identity, per-item size, unit, and pack count."""
    grouped = {}
    for product in products:
        size = get_product_size(product)
        identity = product.get("identity") or get_product_identity(
            product.get("name", ""), product.get("variant", "")
        )
        if identity and size:
            key = (_identity_signature(identity), size["amount"], size["unit"], size["pack_count"])
            grouped.setdefault(key, []).append(product)
    return grouped


def unit_price(product):
    size = get_product_size(product)
    price = product.get("price")
    if not size or price is None or size["unit"] == "pcs":
        return None
    return (price / size["total_amount"]) * 100


def group_by_identity_and_unit(products):
    """Unit-price groups require exact product identity and physical unit."""
    grouped = {}
    for product in products:
        size = get_product_size(product)
        price_per_100 = unit_price(product)
        identity = product.get("identity") or get_product_identity(
            product.get("name", ""), product.get("variant", "")
        )
        if identity and size and price_per_100 is not None:
            grouped.setdefault((_identity_signature(identity), size["unit"]), []).append((product, price_per_100))
    return grouped


def format_size(size):
    if size is None:
        return "Unknown"
    _, amount, unit, pack_count = size
    if unit == "ml":
        label = f"{amount / 1000:g} L" if amount >= 1000 else f"{amount:g} ml"
    elif unit == "g":
        label = f"{amount / 1000:g} kg" if amount >= 1000 else f"{amount:g} g"
    elif unit == "pcs":
        label = f"{amount:g} pcs"
    else:
        return "Unknown"
    return label if pack_count == 1 else f"{pack_count:g} x {label}"


def print_product(product):
    print(f"{product['name']} | {product['variant']} | Rs.{product['price']}")


def shared_keys(*groups):
    """Return keys represented by at least two platforms."""
    all_keys = set().union(*(group.keys() for group in groups))
    return sorted(
        (key for key in all_keys if sum(key in group for group in groups) >= 2),
        key=str,
    )


def main():
    query = input("Enter product to search: ")
    print("\nSearching Blinkit...")
    print("Searching Zepto...")
    print("Searching Instamart...")

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            "Blinkit": executor.submit(get_blinkit_products, query),
            "Zepto": executor.submit(get_zepto_products, query),
            "Instamart": executor.submit(get_instamart_products, query),
        }
        sources = {platform: future.result() for platform, future in futures.items()}

    matches = {platform: find_name_matches(products, query) for platform, products in sources.items()}
    for products in matches.values():
        for product in products:
            product["identity"] = get_product_identity(product.get("name", ""), product.get("variant", ""))

    print("\n========== PRODUCT IDENTITIES ==========")
    for platform, products in matches.items():
        print(f"\n--- {platform} ---")
        for product in products:
            print(f"{product['name']} | {product['variant']} | identity = {product['identity']}")

    by_size = {platform: group_by_size(products) for platform, products in matches.items()}
    common_sizes = shared_keys(*by_size.values())
    print("\n========== EXACT SIZE COMPARISON ==========")
    if not common_sizes:
        print("No same-identity, same-size product available.")
    for key in common_sizes:
        candidates = []
        for platform, groups in by_size.items():
            if key in groups:
                product = min(groups[key], key=lambda item: item["price"])
                candidates.append((platform, product))
        print(f"\n--- {format_size(key)} | {candidates[0][1]['identity']} ---")
        for platform, product in candidates:
            print(f"{platform}: ", end="")
            print_product(product)
        winner, cheapest = min(candidates, key=lambda item: item[1]["price"])
        difference = max(product["price"] for _, product in candidates) - cheapest["price"]
        print(f"Best: {winner}" + (f" (saves Rs.{difference:.2f})" if difference else " (same price)"))

    unit_groups = {platform: group_by_identity_and_unit(products) for platform, products in matches.items()}
    comparable_units = shared_keys(*unit_groups.values())
    print("\n========== UNIT PRICE COMPARISON ==========")
    if not comparable_units:
        print("No comparable product identity available for unit-price comparison.")
    for identity_key, unit in comparable_units:
        candidates = []
        for platform, groups in unit_groups.items():
            if (identity_key, unit) in groups:
                product, value = min(groups[(identity_key, unit)], key=lambda item: item[1])
                candidates.append((platform, product, value))
        print(f"\n--- {candidates[0][1]['identity']} ({unit}) ---")
        for platform, product, value in candidates:
            print(f"{platform}: {product['name']} | Rs.{value:.2f} per 100 {unit}")
        winner, _, best_value = min(candidates, key=lambda item: item[2])
        difference = max(value for _, _, value in candidates) - best_value
        print(f"Best value: {winner}" + (f" (saves Rs.{difference:.2f} per 100 {unit})" if difference else " (same unit price)"))

    print("\n========== PLATFORM AVAILABILITY ==========")
    platform_keys = {platform: set(groups) for platform, groups in by_size.items()}
    for platform, groups in by_size.items():
        other_keys = set().union(*(keys for other, keys in platform_keys.items() if other != platform))
        exclusive = sorted(platform_keys[platform] - other_keys)
        if exclusive:
            print(f"\n{platform} only:")
            for key in exclusive:
                product = min(groups[key], key=lambda item: item["price"])
                print(f"{product['name']} | {format_size(key)} -> Rs.{product['price']}")


if __name__ == "__main__":
    main()
