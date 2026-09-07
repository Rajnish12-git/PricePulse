from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ProductItem(BaseModel):
    name: str
    variant: Optional[str] = ""
    price: float
    mrp: Optional[float] = None
    stock: Optional[Any] = None
    out_of_stock: Optional[bool] = False

class PlatformProductMatch(BaseModel):
    platform: str
    product: ProductItem

class SizeComparisonGroup(BaseModel):
    size_label: str
    amount: float
    unit: str
    products: List[PlatformProductMatch]
    cheapest_platform: Optional[str] = None
    savings: Optional[float] = 0.0
    is_equal_price: bool = False

class PlatformUnitPrice(BaseModel):
    platform: str
    product: ProductItem
    unit_price: float
    unit_label: str

class UnitPriceComparison(BaseModel):
    items: List[PlatformUnitPrice]
    best_value_platform: Optional[str] = None
    savings_per_100_units: Optional[float] = 0.0

class SearchResponse(BaseModel):
    query: str
    exact_matches: List[SizeComparisonGroup] = []
    unit_price_analysis: Optional[UnitPriceComparison] = None
    all_raw_matches: Dict[str, List[ProductItem]] = {}
