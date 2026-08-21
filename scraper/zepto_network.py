import json
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys


def get_zepto_products(product_name):

    options = webdriver.ChromeOptions()

    options.set_capability(
        "goog:loggingPrefs",
        {"performance": "ALL"}
    )

    driver = webdriver.Chrome(options=options)

    products = []

    try:

        # -----------------------------------------
        # OPEN ZEPTO
        # -----------------------------------------

        driver.execute_cdp_cmd(
            "Network.enable",
            {}
        )

        driver.get(
            "https://www.zeptonow.com/"
        )

        time.sleep(3)

        # -----------------------------------------
        # CLICK SEARCH BAR
        # -----------------------------------------

        search_text = driver.find_element(
            By.XPATH,
            "//span[contains(text(), 'Search for')]"
        )

        search_text.click()

        print("Search bar clicked!")

        time.sleep(1)

        # -----------------------------------------
        # FIND REAL SEARCH INPUT
        # -----------------------------------------

        search_box = driver.find_element(
            By.CSS_SELECTOR,
            'input[placeholder="Search for over 70,000 products"]'
        )

        # -----------------------------------------
        # TYPE PRODUCT
        # -----------------------------------------

        search_box.click()

        search_box.send_keys(
            product_name
        )

        print(
            f"Searching Zepto for: {product_name}"
        )

        # Press Enter to perform search
        search_box.send_keys(
            Keys.ENTER
        )

        # Give Zepto time to make API request
        time.sleep(5)

        # -----------------------------------------
        # CAPTURE NETWORK LOGS
        # -----------------------------------------

        logs = driver.get_log(
            "performance"
        )

        for log in logs:

            message = json.loads(
                log["message"]
            )["message"]

            if message["method"] != "Network.responseReceived":
                continue

            response = message["params"]["response"]

            url = response["url"]

            # Only Zepto search API
            if "/user-search-service/api/v3/search" not in url:
                continue

            if response["status"] != 200:
                continue

            request_id = message["params"]["requestId"]

            try:

                body = driver.execute_cdp_cmd(
                    "Network.getResponseBody",
                    {
                        "requestId": request_id
                    }
                )

                data = json.loads(
                    body["body"]
                )

                layout = data.get(
                    "layout",
                    []
                )

                # -----------------------------------------
                # FIND PRODUCT WIDGETS
                # -----------------------------------------

                for widget in layout:

                    widget_name = widget.get(
                        "widgetName"
                    )

                    if not widget_name:
                        continue

                    if not widget_name.startswith(
                        "SEARCHED_PRODUCTS_"
                    ):
                        continue

                    data_section = widget.get(
                        "data",
                        {}
                    )

                    resolver = data_section.get(
                        "resolver",
                        {}
                    )

                    resolver_data = resolver.get(
                        "data",
                        {}
                    )

                    items = resolver_data.get(
                        "items",
                        []
                    )

                    # -----------------------------------------
                    # EXTRACT PRODUCTS
                    # -----------------------------------------

                    for item in items:

                        product_response = item.get(
                            "productResponse",
                            {}
                        )

                        product = product_response.get(
                            "product",
                            {}
                        )

                        variant = product_response.get(
                            "productVariant",
                            {}
                        )

                        name = product.get(
                            "name"
                        )

                        pack_size = variant.get(
                            "formattedPacksize"
                        )

                        price = product_response.get(
                            "discountedSellingPrice"
                        )

                        mrp = product_response.get(
                            "mrp"
                        )

                        stock = product_response.get(
                            "availableQuantity"
                        )

                        out_of_stock = product_response.get(
                            "outOfStock"
                        )

                        if name and price is not None:

                            products.append(
                                {
                                    "name": name,
                                    "variant": pack_size,
                                    "price": price / 100,
                                    "mrp": (
                                        mrp / 100
                                        if mrp is not None
                                        else None
                                    ),
                                    "stock": stock,
                                    "out_of_stock": out_of_stock
                                }
                            )

            except Exception:
                continue

        # -----------------------------------------
        # REMOVE DUPLICATES
        # -----------------------------------------

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

                unique_products.append(
                    product
                )

        return unique_products

    finally:

        driver.quit()




