import re

from blinkit import get_blinkit_products
from zepto_network import get_zepto_products


# =========================================
# NORMALIZE SIZE
# =========================================

def normalize_size(text):

    if not text:
        return None

    text = text.lower()

    # litres
    match = re.search(
        r'(\d+(?:\.\d+)?)\s*(?:l|ltr|litre|liter)\b',
        text
    )

    if match:
        return int(float(match.group(1)) * 1000)

    # millilitres
    match = re.search(
        r'(\d+(?:\.\d+)?)\s*ml\b',
        text
    )

    if match:
        return int(float(match.group(1)))

    # kilograms
    match = re.search(
        r'(\d+(?:\.\d+)?)\s*kg\b',
        text
    )

    if match:
        return int(float(match.group(1)) * 1000)

    # grams
    match = re.search(
        r'(\d+(?:\.\d+)?)\s*g\b',
        text
    )

    if match:
        return int(float(match.group(1)))

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
        r'\d+(?:\.\d+)?\s*(?:ml|l|ltr|litre|liter|g|kg)\b',
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

def name_matches(product, query):

    query_name = normalize_name(query)

    product_name = normalize_name(
        product.get("name", "")
    )

    query_words = query_name.split()

    product_words = product_name.split()

    for word in query_words:

        if word not in product_words:
            return False

    return True


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

        if size not in grouped:
            grouped[size] = []

        grouped[size].append(product)

    return grouped


# =========================================
# FORMAT SIZE
# =========================================

def format_size(size):

    if size >= 1000:

        litres = size / 1000

        if litres.is_integer():
            return f"{int(litres)} L"

        return f"{litres:g} L"

    return f"{size} ml"


# =========================================
# UNIT PRICE
# =========================================

def unit_price(product):

    size = normalize_size(
        product.get("variant", "")
    )

    if size is None or size == 0:
        return None

    price = product.get("price")

    if price is None:
        return None

    # Price per 100 ml / 100 g
    return (price / size) * 100


# =========================================
# PRINT PRODUCT
# =========================================

def print_product(product):

    print(
        f"{product['name']} | "
        f"{product['variant']} | "
        f"₹{product['price']}"
    )


# =========================================
# MAIN
# =========================================

query = input(
    "Enter product to search: "
)


# =========================================
# BLINKIT
# =========================================

print("\nSearching Blinkit...")

blinkit_products = get_blinkit_products(
    query
)


# =========================================
# ZEPTO
# =========================================

print("\nSearching Zepto...")

zepto_products = get_zepto_products(
    query
)


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


# =========================================
# GROUP BY SIZE
# =========================================

blinkit_by_size = group_by_size(
    blinkit_matches
)

zepto_by_size = group_by_size(
    zepto_matches
)


# =========================================
# COMMON SIZES
# =========================================

common_sizes = sorted(
    set(blinkit_by_size.keys())
    &
    set(zepto_by_size.keys())
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

        blinkit_product = min(
            blinkit_by_size[size],
            key=lambda x: x["price"]
        )

        zepto_product = min(
            zepto_by_size[size],
            key=lambda x: x["price"]
        )

        print(
            f"\n--- {format_size(size)} ---"
        )

        print("\nBlinkit:")
        print_product(
            blinkit_product
        )

        print("\nZepto:")
        print_product(
            zepto_product
        )

        if (
            blinkit_product["price"]
            <
            zepto_product["price"]
        ):

            saving = (
                zepto_product["price"]
                -
                blinkit_product["price"]
            )

            print(
                f"\n🔥 Blinkit cheaper by ₹{saving:.2f}"
            )

        elif (
            zepto_product["price"]
            <
            blinkit_product["price"]
        ):

            saving = (
                blinkit_product["price"]
                -
                zepto_product["price"]
            )

            print(
                f"\n🔥 Zepto cheaper by ₹{saving:.2f}"
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

    print(
        f"Unit    : ₹{unit:.2f} per 100 ml/g"
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

    print(
        f"Unit    : ₹{unit:.2f} per 100 ml/g"
    )


else:

    print(
        "\nZepto: Unit price unavailable"
    )


# =========================================
# UNIT PRICE WINNER
# =========================================

if (
    best_blinkit_unit
    and best_zepto_unit
):

    blinkit_unit = best_blinkit_unit[1]
    zepto_unit = best_zepto_unit[1]

    print(
        "\n========== BETTER VALUE =========="
    )

    if blinkit_unit < zepto_unit:

        difference = (
            zepto_unit
            - blinkit_unit
        )

        print(
            "🔥 Blinkit has the better unit price"
        )

        print(
            f"Saves ₹{difference:.2f} "
            f"per 100 ml/g"
        )

    elif zepto_unit < blinkit_unit:

        difference = (
            blinkit_unit
            - zepto_unit
        )

        print(
            "🔥 Zepto has the better unit price"
        )

        print(
            f"Saves ₹{difference:.2f} "
            f"per 100 ml/g"
        )

    else:

        print(
            "🤝 Same unit price"
        )


# =========================================
# PLATFORM-ONLY SIZES
# =========================================

blinkit_only = sorted(
    set(blinkit_by_size.keys())
    -
    set(zepto_by_size.keys())
)

zepto_only = sorted(
    set(zepto_by_size.keys())
    -
    set(blinkit_by_size.keys())
)


if blinkit_only:

    print(
        "\n========== BLINKIT ONLY =========="
    )

    for size in blinkit_only:

        product = min(
            blinkit_by_size[size],
            key=lambda x: x["price"]
        )

        print(
            f"{format_size(size)} → "
            f"₹{product['price']}"
        )


if zepto_only:

    print(
        "\n========== ZEPTO ONLY =========="
    )

    for size in zepto_only:

        product = min(
            zepto_by_size[size],
            key=lambda x: x["price"]
        )

        print(
            f"{format_size(size)} → "
            f"₹{product['price']}"
        )