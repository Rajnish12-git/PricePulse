import subprocess
import json
import os
import shutil
from dotenv import load_dotenv

load_dotenv()
# Your authenticated Instamart address
ADDRESS_ID = os.getenv("INSTAMART_ADDRESS_ID")


def get_instamart_products(product_name):
    swiggy_path = os.getenv("SWIGGY_PATH")
    if not swiggy_path or not os.path.exists(swiggy_path):
        swiggy_path = shutil.which("swiggy") or "swiggy"

    command = [
        swiggy_path,
        "instamart",
        "search",
        "--query",
        product_name,
        "--address-id",
        ADDRESS_ID,
        "--json"
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8"
        )

        if result.returncode != 0:
            print("Instamart command failed")
            print("Return code:", result.returncode)
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return []

        data = json.loads(result.stdout)

    except Exception as e:
        print("Failed to get Instamart data:", e)
        return []

    products = []

    # Instamart response contains products in different possible
    # structures depending on the MCP response.
    def process_product(product):

        name = product.get("displayName")

        if not name:
            return

        brand = product.get("brand")

        if brand and brand.lower() not in name.lower():
            name = f"{brand} {name}"

        variations = product.get(
            "variations",
            []
        )

        for variation in variations:

            variant = variation.get(
                "quantityDescription"
            )

            price_data = variation.get(
                "price",
                {}
            )

            price = price_data.get(
                "offerPrice"
            )

            mrp = price_data.get(
                "mrp"
            )

            in_stock = variation.get(
                "isInStockAndAvailable",
                product.get("inStock", False)
            )

            if name and price is not None:

                products.append(
                    {
                        "name": name,
                        "variant": variant,
                        "price": float(price),
                        "mrp": float(mrp)
                        if mrp is not None
                        else None,
                        "stock": None,
                        "out_of_stock": not in_stock
                    }
                )

    # ------------------------------------------------
    # Try common response structures
    # ------------------------------------------------

    def walk(obj):

        if isinstance(obj, dict):

            # Product object
            if (
                "displayName" in obj
                and (
                    "variations" in obj
                    or "inStock" in obj
                )
            ):
                process_product(obj)

            for value in obj.values():
                walk(value)

        elif isinstance(obj, list):

            for item in obj:
                walk(item)

    walk(data)

    # ------------------------------------------------
    # Remove duplicates
    # ------------------------------------------------

    unique_products = []

    seen = set()

    for product in products:

        key = (
            product["name"],
            product["variant"],
            product["price"]
        )

        if key not in seen:

            seen.add(key)

            unique_products.append(product)

    return unique_products


# ------------------------------------------------
# TEST
# ------------------------------------------------

if __name__ == "__main__":

    product_name = input(
        "Enter product to search: "
    )

    products = get_instamart_products(
        product_name
    )

    print(
        f"\nTotal Instamart products: {len(products)}\n"
    )

    for product in products:
        print(product)