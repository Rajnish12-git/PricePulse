import re
from concurrent.futures import ThreadPoolExecutor
from blinkit import get_blinkit_products
from zepto_network import get_zepto_products
from instamart import get_instamart_products


# =========================================
# NORMALIZE SIZE
# =========================================

def normalize_size(text):

    if not text:
        return None

    text = text.lower()

    # -----------------------------------------
    # MILLILITRES
    # -----------------------------------------

    match = re.search(
        r'(\d+(?:\.\d+)?)\s*ml\b',
        text
    )

    if match:
        return {
            "amount": float(match.group(1)),
            "unit": "ml"
        }

    # -----------------------------------------
    # LITRES
    # -----------------------------------------

    match = re.search(
        r'(\d+(?:\.\d+)?)\s*(?:l|ltr|litre|liter)\b',
        text
    )

    if match:
        return {
            "amount": float(match.group(1)) * 1000,
            "unit": "ml"
        }

    # -----------------------------------------
    # GRAMS
    # -----------------------------------------

    match = re.search(
        r'(\d+(?:\.\d+)?)\s*g\b',
        text
    )

    if match:
        return {
            "amount": float(match.group(1)),
            "unit": "g"
        }

    # -----------------------------------------
    # KILOGRAMS
    # -----------------------------------------

    match = re.search(
        r'(\d+(?:\.\d+)?)\s*kg\b',
        text
    )

    if match:
        return {
            "amount": float(match.group(1)) * 1000,
            "unit": "g"
        }

        # -----------------------------------------
    # PIECES / QUANTITY
    # -----------------------------------------

    match = re.search(
        r'(\d+(?:\.\d+)?)\s*(?:pcs|pc|pieces|piece)\b',
        text
    )

    if match:
        return {
            "amount": float(match.group(1)),
            "unit": "pcs"
        }

    return None



# =========================================
# NORMALIZE NAME
# =========================================

def normalize_name(name):

    if not name:
        return ""

    name = name.lower()

    words_to_remove = [
        "fresh",
        "pouch",
        "pack",
        "packet",
        "tetra",
        "tetra pack"
    ]

    for word in words_to_remove:
        name = name.replace(word, " ")

    # Remove size
    name = re.sub(
        r'\d+(?:\.\d+)?\s*(?:ml|l|ltr|litre|liter|g|kg|pcs|pc|pieces|piece)\b',
        " ",
        name
    )

    # Remove punctuation
    name = re.sub(
        r'[^a-z0-9\s]',
        " ",
        name
    )

    # Remove extra spaces
    name = re.sub(
        r'\s+',
        " ",
        name
    )

    return name.strip()


# =========================================
# NAME MATCH
# =========================================

# =========================================
# NAME MATCH
# =========================================

def name_matches(product, query):

    query_name = normalize_name(query)
    product_name = normalize_name(
        product.get("name", "")
    )

    if not query_name or not product_name:
        return False

    query_words = query_name.split()
    product_words = set(product_name.split())

    # -----------------------------------------
    # REMOVE DUPLICATE QUERY WORDS
    # -----------------------------------------

    query_words = list(set(query_words))

    # -----------------------------------------
    # EXACT WORD MATCHING
    # -----------------------------------------

    matched_words = 0

    for word in query_words:

        if word in product_words:
            matched_words += 1

    # -----------------------------------------
    # CALCULATE MATCH RATIO
    # -----------------------------------------

    match_ratio = (
        matched_words / len(query_words)
    )

    # -----------------------------------------
    # STRICT MATCH FOR SPECIFIC QUERIES
    # -----------------------------------------

    if len(query_words) >= 3:

        return match_ratio >= 0.75

    # -----------------------------------------
    # BROAD QUERY
    # -----------------------------------------

    return match_ratio >= 0.5

# =========================================
# FIND NAME MATCHES
# =========================================

def find_name_matches(products, query):

    matches = []

    for product in products:

        if name_matches(product, query):
            matches.append(product)

    return matches


# =========================================
# GROUP BY SIZE
# =========================================


def group_by_size(products):

    grouped = {}

    for product in products:

        size = normalize_size(
            product.get("variant", "")
        )

        if size is None:
            continue

        key = (
            size["amount"],
            size["unit"]
        )

        if key not in grouped:
            grouped[key] = []

        grouped[key].append(product)

    return grouped


# =========================================
# FORMAT SIZE
# =========================================

def format_size(size):

    if size is None:
        return "Unknown"

    # group_by_size() returns:
    # (amount, unit)
    amount, unit = size

    if unit == "ml":

        if amount >= 1000:
            litres = amount / 1000

            if litres.is_integer():
                return f"{int(litres)} L"

            return f"{litres:g} L"

        return f"{int(amount)} ml"

    if unit == "g":

        if amount >= 1000:
            kg = amount / 1000

            if kg.is_integer():
                return f"{int(kg)} kg"

            return f"{kg:g} kg"

        return f"{int(amount)} g"

    if unit == "pcs":

        if amount.is_integer():
            return f"{int(amount)} pcs"

        return f"{amount:g} pcs"

    return "Unknown"


# =========================================
# UNIT PRICE
# =========================================

def unit_price(product):

    size = normalize_size(
        product.get("variant", "")
    )

    if size is None:
        return None

    if size["unit"] == "pcs":
            return None

    amount = size["amount"]

    if amount == 0:
        return None

    price = product.get("price")

    if price is None:
        return None

    # Price per 100 ml / 100 g
    return (price / amount) * 100


# =========================================
# PRINT PRODUCT
# =========================================

def print_product(product):

    print(
        f"{product['name']} | "
        f"{product['variant']} | "
        f"₹{product['price']}"
    )


def main():
    query = input(
        "Enter product to search: "
    )

    print("\nSearching Blinkit...")
    print("Searching Zepto...")
    print("Searching Instamart...")

    with ThreadPoolExecutor(max_workers=3) as executor:

        blinkit_future = executor.submit(get_blinkit_products, query)
        zepto_future = executor.submit(get_zepto_products, query)
        instamart_future = executor.submit(get_instamart_products, query)

        blinkit_products = blinkit_future.result()
        zepto_products = zepto_future.result()
        instamart_products = instamart_future.result()
    # =========================================
    # NAME MATCHING
    # =========================================

    blinkit_matches = find_name_matches(
        blinkit_products,
        query
    )

    zepto_matches = find_name_matches(
        zepto_products,
        query
    )

    instamart_matches = find_name_matches(
        instamart_products,
        query
    )


    # =========================================
    # GROUP BY SIZE
    # =========================================

    blinkit_by_size = group_by_size(
        blinkit_matches
    )

    zepto_by_size = group_by_size(
        zepto_matches
    )

    instamart_by_size = group_by_size(
        instamart_matches
    )

    # =========================================
    # COMMON SIZES
    # =========================================

    common_sizes = sorted(
        set(blinkit_by_size.keys())
        &
        set(zepto_by_size.keys())
        |
        (
            set(blinkit_by_size.keys())
            &
            set(instamart_by_size.keys())
        )
        |
        (
            set(zepto_by_size.keys())
            &
            set(instamart_by_size.keys())
        )
    )


    # =========================================
    # EXACT SIZE COMPARISON
    # =========================================

    print(
        "\n========== EXACT SIZE COMPARISON =========="
    )

    if not common_sizes:

        print(
            "No same-size product available."
        )

    else:

        for size in common_sizes:

            candidates = []

            if size in blinkit_by_size:

                product = min(
                    blinkit_by_size[size],
                    key=lambda x: x["price"]
                )

                candidates.append(
                    ("Blinkit", product)
                )

            if size in zepto_by_size:

                product = min(
                    zepto_by_size[size],
                    key=lambda x: x["price"]
                )

                candidates.append(
                    ("Zepto", product)
                )

            if size in instamart_by_size:

                product = min(
                    instamart_by_size[size],
                    key=lambda x: x["price"]
                )

                candidates.append(
                    ("Instamart", product)
                )

            print(
                f"\n--- {format_size(size)} ---"
            )

            # Print products
            for platform, product in candidates:

                print(f"\n{platform}:")
                print_product(product)

            # Find cheapest
            if len(candidates) >= 2:

                cheapest_platform, cheapest_product = min(
                    candidates,
                    key=lambda x: x[1]["price"]
                )

                highest_price = max(
                    product["price"]
                    for _, product in candidates
                )

                saving = (
                    highest_price
                    - cheapest_product["price"]
                )

                if saving > 0:

                    print(
                        f"\n🔥 {cheapest_platform} "
                        f"cheaper by ₹{saving:.2f}"
                    )

                else:

                    print(
                        "\n🤝 Same price"
                    )

    # =========================================
    # UNIT PRICE COMPARISON
    # =========================================

    print(
        "\n========== UNIT PRICE COMPARISON =========="
    )


    # Pick cheapest matching product from each platform
    # for unit-price comparison.

    best_blinkit_unit = None
    best_zepto_unit = None
    best_instamart_unit = None


    for product in blinkit_matches:

        unit = unit_price(product)

        if unit is None:
            continue

        if (
            best_blinkit_unit is None
            or unit < best_blinkit_unit[1]
        ):

            best_blinkit_unit = (
                product,
                unit
            )


    for product in zepto_matches:

        unit = unit_price(product)

        if unit is None:
            continue

        if (
            best_zepto_unit is None
            or unit < best_zepto_unit[1]
        ):

            best_zepto_unit = (
                product,
                unit
            )

    for product in instamart_matches:

        unit = unit_price(product)

        if unit is None:
            continue

        if (
            best_instamart_unit is None
            or unit < best_instamart_unit[1]
        ):

            best_instamart_unit = (
                product,
                unit
            )

    if best_blinkit_unit:

        product, unit = best_blinkit_unit

        print("\nBlinkit:")

        print(
            f"Product : {product['name']}"
        )

        print(
            f"Variant : {product['variant']}"
        )

        print(
            f"Price   : ₹{product['price']}"
        )

        size_info = normalize_size(product.get("variant", ""))

        if size_info and size_info.get("unit") == "g":
            unit_label = "100 g"
        else:
            unit_label = "100 ml"

        print(
        f"Unit    : ₹{unit:.2f} per {unit_label}"
        )


    else:

        print(
            "\nBlinkit: Unit price unavailable"
        )


    if best_zepto_unit:

        product, unit = best_zepto_unit

        print("\nZepto:")

        print(
            f"Product : {product['name']}"
        )

        print(
            f"Variant : {product['variant']}"
        )

        print(
            f"Price   : ₹{product['price']}"
        )

        size_info = normalize_size(product.get("variant", ""))

        if size_info and size_info.get("unit") == "g":
            unit_label = "100 g"
        else:
            unit_label = "100 ml"

        print(
            f"Unit    : ₹{unit:.2f} per {unit_label}"
        )


    else:

        print(
            "\nZepto: Unit price unavailable"
        )

    if best_instamart_unit:

        product, unit = best_instamart_unit

        print("\nInstamart:")

        print(
            f"Product : {product['name']}"
        )

        print(
            f"Variant : {product['variant']}"
        )

        print(
            f"Price   : ₹{product['price']}"
        )

        size_info = normalize_size(
            product.get("variant", "")
        )

        if size_info and size_info.get("unit") == "g":
            unit_label = "100 g"
        else:
            unit_label = "100 ml"

        print(
            f"Unit    : ₹{unit:.2f} per {unit_label}"
        )

    else:

        print(
            "\nInstamart: Unit price unavailable"
        )

    # =========================================
    # UNIT PRICE WINNER
    # =========================================

    unit_candidates = []

    if best_blinkit_unit:
        unit_candidates.append(
            ("Blinkit", best_blinkit_unit)
        )

    if best_zepto_unit:
        unit_candidates.append(
            ("Zepto", best_zepto_unit)
        )

    if best_instamart_unit:
        unit_candidates.append(
            ("Instamart", best_instamart_unit)
        )


    if len(unit_candidates) >= 2:

        print(
            "\n========== BETTER VALUE =========="
        )

        cheapest_platform, cheapest_data = min(
            unit_candidates,
            key=lambda x: x[1][1]
        )

        cheapest_unit = cheapest_data[1]

        other_units = [
            data[1]
            for platform, data in unit_candidates
            if platform != cheapest_platform
        ]

        highest_unit = max(other_units)

        difference = highest_unit - cheapest_unit

        if difference > 0:

            print(
                f"🔥 {cheapest_platform} "
                f"has the better unit price"
            )

            size_info = normalize_size(
                cheapest_data[0].get("variant", "")
            )

            if size_info and size_info.get("unit") == "g":
                unit_label = "g"
            else:
                unit_label = "ml"

            print(
            f"Saves ₹{difference:.2f} "
            f"per 100 {unit_label}"
            )

        else:

            print(
                "🤝 Same unit price"
            )


    # =========================================
    # PLATFORM AVAILABILITY
    # =========================================

    print(
        "\n========== PLATFORM AVAILABILITY =========="
    )


    # All sizes available on each platform
    all_blinkit_sizes = set(
        blinkit_by_size.keys()
    )

    all_zepto_sizes = set(
        zepto_by_size.keys()
    )

    all_instamart_sizes = set(
        instamart_by_size.keys()
    )


    # =========================================
    # BLINKIT ONLY
    # =========================================

    blinkit_only = (
        all_blinkit_sizes
        - all_zepto_sizes
        - all_instamart_sizes
    )

    if blinkit_only:

        print(
            "\nBlinkit only:"
        )

        for size in sorted(blinkit_only):

            product = min(
                blinkit_by_size[size],
                key=lambda x: x["price"]
            )

            print(
                f"{format_size(size)} → "
                f"₹{product['price']}"
            )


    # =========================================
    # ZEPTO ONLY
    # =========================================

    zepto_only = (
        all_zepto_sizes
        - all_blinkit_sizes
        - all_instamart_sizes
    )

    if zepto_only:

        print(
            "\nZepto only:"
        )

        for size in sorted(zepto_only):

            product = min(
                zepto_by_size[size],
                key=lambda x: x["price"]
            )

            print(
                f"{format_size(size)} → "
                f"₹{product['price']}"
            )


    # =========================================
    # INSTAMART ONLY
    # =========================================

    instamart_only = (
        all_instamart_sizes
        - all_blinkit_sizes
        - all_zepto_sizes
    )

    if instamart_only:

        print(
            "\nInstamart only:"
        )

        for size in sorted(instamart_only):

            product = min(
                instamart_by_size[size],
                key=lambda x: x["price"]
            )

            print(
                f"{format_size(size)} → "
                f"₹{product['price']}"
            )


if __name__ == "__main__":
    main()
