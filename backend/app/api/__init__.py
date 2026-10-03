from fastapi import APIRouter
from .routes_health import router as health_router
from .routes_ingest import router as ingest_router
from .routes_nlp import router as nlp_router
from .routes_portfolio import router as portfolio_router
from .routes_stress import router as stress_router

from .routes_risk import router as risk_router
from .routes_rebalancer import router as rebalancer_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router, tags=["Health"])
api_router.include_router(risk_router, tags=["Risk Signals"])
api_router.include_router(rebalancer_router, tags=["Module A: Rebalancer"])
api_router.include_router(ingest_router, tags=["Data Ingestion"])
api_router.include_router(nlp_router, tags=["NLP Risk Engine"])
api_router.include_router(portfolio_router, tags=["Portfolio"])
api_router.include_router(stress_router, tags=["Module B: Stress Testing"])

__all__ = ["api_router", "risk_router", "rebalancer_router"]
