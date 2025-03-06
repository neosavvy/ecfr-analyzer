from fastapi import APIRouter

from app.api.endpoints import agencies, documents, metrics

api_router = APIRouter()
api_router.include_router(agencies.router, prefix="/agencies", tags=["agencies"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(metrics.router, prefix="/metrics", tags=["metrics"]) 