import json
import time
from urllib.parse import quote_plus

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def get_blinkit_products(product_name):

    # Convert product name into URL format
    encoded_query = quote_plus(product_name)

    options = webdriver.ChromeOptions()

    options.set_capability(
        "goog:loggingPrefs",
        {"performance": "ALL"}
    )

    driver = webdriver.Chrome(options=options)

    try:
        driver.get("https://blinkit.com/")

        wait = WebDriverWait(driver, 10)

        # --------------------------------
        # 1. Select delivery location
        # --------------------------------

        location_box = wait.until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    'input[placeholder="search delivery location"]'
                )
            )
        )

        location_box.send_keys("110001")

        new_delhi = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//*[contains(text(), 'New Delhi')]"
                )
            )
        )

        new_delhi.click()

        # Wait for homepage
        time.sleep(3)

        # --------------------------------
        # 2. Find search bar
        # --------------------------------

        search_text = wait.until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    '[class*="SearchBar__AnimationText"]'
                )
            )
        )

        search_bar = search_text.find_element(
            By.XPATH,
            ".."
        )

        # --------------------------------
        # 3. Click search bar
        # --------------------------------

        search_bar.click()

        # --------------------------------
        # 4. Find actual search input
        # --------------------------------

        search_input = wait.until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    'input[placeholder^="Search for"]'
                )
            )
        )

        # --------------------------------
        # 5. Type product name
        # --------------------------------

        search_input.send_keys(product_name)

        print(f"Searching Blinkit for: {product_name}")

        # Give Blinkit time to send request
        time.sleep(3)

        # --------------------------------
        # 6. Capture network logs
        # --------------------------------

        logs = driver.get_log("performance")

        products = []

        for log in logs:

            message = json.loads(
                log["message"]
            )["message"]

            if message["method"] != "Network.responseReceived":
                continue

            response = message["params"]["response"]

            url = response["url"]

            # Only Blinkit search requests
            if "/v1/layout/search" not in url:
                continue

            # Ignore auto-suggest requests
            if "type_to_search" not in url:
                continue

            # Only accept the EXACT search query
            if f"q={encoded_query.lower()}" not in url.lower():
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

                snippets = data[
                    "response"
                ]["snippets"]

                # --------------------------------
                # 7. Extract product information
                # --------------------------------

                for snippet in snippets:

                    product = snippet.get(
                        "data",
                        {}
                    )

                    name = product.get(
                        "name",
                        {}
                    ).get("text")

                    variant = product.get(
                        "variant",
                        {}
                    ).get("text")

                    price_text = product.get(
                        "normal_price",
                        {}
                    ).get("text")

                    inventory = product.get(
                        "inventory"
                    )

                    if name and price_text:

                        price = float(
                            price_text
                            .replace("₹", "")
                            .replace(",", "")
                        )

                        products.append(
                            {
                                "name": name,
                                "variant": variant,
                                "price": price,
                                "stock": inventory
                            }
                        )

            except Exception as e:

                print(
                    "Could not process response:",
                    e
                )

        return products

    finally:

        driver.quit()


def get_blinkit_price(product_query):

    # For now, use the first word as the brand
    brand = product_query.split()[0]

    # Search Blinkit broadly using the brand
    products = get_blinkit_products(brand)

    query_words = product_query.lower().split()

    for product in products:

        product_text = (
            product["name"] + " " + product["variant"]
        ).lower()

        # Check whether all requested words
        # appear in the product information
        if all(word in product_text for word in query_words):

            return product

    return None