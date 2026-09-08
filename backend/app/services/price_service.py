import os
import sys
import asyncio
from typing import Dict, Any, List, Optional

# Ensure project root and scraper directory are in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
SCRAPER_DIR = os.path.join(BASE_DIR, "scraper")
for path in (BASE_DIR, SCRAPER_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

from compare_prices import (
    normalize_size,
    normalize_name,
    find_name_matches,
    group_by_size,
    format_size,
    unit_price
)
from blinkit import get_blinkit_products
from zepto_network import get_zepto_products
from instamart import get_instamart_products

from app.schemas.search import (
    SearchResponse,
    ProductItem,
    PlatformProductMatch,
    SizeComparisonGroup,
    PlatformUnitPrice,
    UnitPriceComparison
)


def parse_product_item(prod: dict) -> ProductItem:
    """Helper to convert raw product dictionary to ProductItem schema safely."""
    return ProductItem(
        name=prod.get("name", "Unknown"),
        variant=prod.get("variant") or "",
        price=float(prod.get("price", 0.0)),
        mrp=float(prod["mrp"]) if prod.get("mrp") is not None else None,
        stock=prod.get("stock"),
        out_of_stock=bool(prod.get("out_of_stock", False))
    )


async def fetch_platform_products(query: str) -> Dict[str, List[dict]]:
    """Fetch products from all platforms concurrently using threads to avoid blocking asyncio event loop."""
    loop = asyncio.get_running_loop()

    def safe_get_blinkit():
        try:
            return get_blinkit_products(query) or []
        except Exception as e:
            print(f"[Blinkit Error]: {e}")
            return []

    def safe_get_zepto():
        try:
            return get_zepto_products(query) or []
        except Exception as e:
            print(f"[Zepto Error]: {e}")
            return []

    def safe_get_instamart():
        try:
            return get_instamart_products(query) or []
        except Exception as e:
            print(f"[Instamart Error]: {e}")
            return []

    blinkit_task = loop.run_in_executor(None, safe_get_blinkit)
    zepto_task = loop.run_in_executor(None, safe_get_zepto)
    instamart_task = loop.run_in_executor(None, safe_get_instamart)

    blinkit_prods, zepto_prods, instamart_prods = await asyncio.gather(
        blinkit_task, zepto_task, instamart_task
    )

    return {
        "Blinkit": blinkit_prods,
        "Zepto": zepto_prods,
        "Instamart": instamart_prods
    }


async def compare_prices_service(query: str) -> SearchResponse:
    raw_results = await fetch_platform_products(query)

    blinkit_matches = find_name_matches(raw_results.get("Blinkit", []), query)
    zepto_matches = find_name_matches(raw_results.get("Zepto", []), query)
    instamart_matches = find_name_matches(raw_results.get("Instamart", []), query)

    blinkit_by_size = group_by_size(blinkit_matches)
    zepto_by_size = group_by_size(zepto_matches)
    instamart_by_size = group_by_size(instamart_matches)

    # All unique sizes across platforms
    all_sizes = sorted(
        set(blinkit_by_size.keys()) | set(zepto_by_size.keys()) | set(instamart_by_size.keys())
    )

    exact_matches: List[SizeComparisonGroup] = []

    for size in all_sizes:
        candidates: List[tuple[str, dict]] = []

        if size in blinkit_by_size and blinkit_by_size[size]:
            best_p = min(blinkit_by_size[size], key=lambda x: x.get("price", 0.0))
            candidates.append(("Blinkit", best_p))

        if size in zepto_by_size and zepto_by_size[size]:
            best_p = min(zepto_by_size[size], key=lambda x: x.get("price", 0.0))
            candidates.append(("Zepto", best_p))

        if size in instamart_by_size and instamart_by_size[size]:
            best_p = min(instamart_by_size[size], key=lambda x: x.get("price", 0.0))
            candidates.append(("Instamart", best_p))

        if not candidates:
            continue

        size_label = format_size(size)
        _, amount, unit, _ = size

        matches_list = [
            PlatformProductMatch(
                platform=platform,
                product=parse_product_item(prod)
            )
            for platform, prod in candidates
        ]

        cheapest_platform: Optional[str] = None
        savings = 0.0
        is_equal = False

        if len(candidates) >= 2:
            cheapest_platform, cheapest_prod = min(candidates, key=lambda x: x[1].get("price", 0.0))
            highest_price = max(prod.get("price", 0.0) for _, prod in candidates)
            savings = round(highest_price - float(cheapest_prod.get("price", 0.0)), 2)
            if savings == 0:
                is_equal = True

        exact_matches.append(
            SizeComparisonGroup(
                size_label=size_label,
                amount=amount,
                unit=unit,
                products=matches_list,
                cheapest_platform=cheapest_platform,
                savings=savings,
                is_equal_price=is_equal
            )
        )

    # Unit price analysis
    unit_candidates = []
    unit_items: List[PlatformUnitPrice] = []

    for platform, matches in [
        ("Blinkit", blinkit_matches),
        ("Zepto", zepto_matches),
        ("Instamart", instamart_matches)
    ]:
        best_unit_data = None
        for prod in matches:
            u_price = unit_price(prod)
            if u_price is None:
                continue
            if best_unit_data is None or u_price < best_unit_data[1]:
                best_unit_data = (prod, u_price)

        if best_unit_data:
            prod, u_price = best_unit_data
            size_info = normalize_size(prod.get("variant", ""))
            unit_lbl = "100 g" if size_info and size_info.get("unit") == "g" else "100 ml"

            p_unit = PlatformUnitPrice(
                platform=platform,
                product=parse_product_item(prod),
                unit_price=round(u_price, 2),
                unit_label=unit_lbl
            )
            unit_items.append(p_unit)
            unit_candidates.append((platform, u_price, size_info))

    unit_analysis = None
    if unit_candidates:
        best_value_platform = None
        savings_100 = 0.0
        if len(unit_candidates) >= 2:
            cheapest_plat, cheapest_u, _ = min(unit_candidates, key=lambda x: x[1])
            other_units = [x[1] for x in unit_candidates if x[0] != cheapest_plat]
            if other_units:
                highest_u = max(other_units)
                best_value_platform = cheapest_plat
                savings_100 = round(highest_u - cheapest_u, 2)
        elif len(unit_candidates) == 1:
            best_value_platform = unit_candidates[0][0]
            savings_100 = 0.0

        unit_analysis = UnitPriceComparison(
            items=unit_items,
            best_value_platform=best_value_platform,
            savings_per_100_units=savings_100
        )

    raw_matches_dict = {
        platform: [parse_product_item(p) for p in prods]
        for platform, prods in raw_results.items()
    }

    return SearchResponse(
        query=query,
        exact_matches=exact_matches,
        unit_price_analysis=unit_analysis,
        all_raw_matches=raw_matches_dict
    )
