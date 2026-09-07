from fastapi import APIRouter
from app.api.v1.search import router as search_router

api_v1_router = APIRouter()
api_v1_router.include_router(search_router, prefix="", tags=["Search & Price Comparison"])
