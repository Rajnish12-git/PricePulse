from fastapi import APIRouter, HTTPException, Query
from app.schemas.search import SearchResponse
from app.services.price_service import compare_prices_service

router = APIRouter()

@router.get("/search", response_model=SearchResponse, summary="Search and compare grocery product prices across Blinkit, Zepto, and Instamart")
async def search_products(
    q: str = Query(..., min_length=2, description="Product query term (e.g. 'Amul Milk', 'Lays Chips')")
):
    """
    Scrapes live product listings from quick-commerce platforms (Blinkit, Zepto, Instamart),
    normalizes weights/volumes, finds exact size matches, and calculates unit price value metrics.
    """
    try:
        results = await compare_prices_service(q)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error scraping product prices: {str(e)}")
