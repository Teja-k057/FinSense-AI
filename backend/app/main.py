import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config.settings import settings
from backend.app.database.connection import init_db
from backend.app.api import api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing S&P Global x CRISIL Risk Engine & Stress Testing System...")
    init_db()
    logger.info("Database schemas verified.")
    yield
    logger.info("Shutting down Risk Engine services.")

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Production AI/NLP Risk Engine & Downstream Strategic Portfolio Stress Testing System "
        "built for the S&P Global x CRISIL Phase III Case Study Competition. "
        "Features GDELT & Kaggle ingestion, FinBERT directional sentiment [-1, 1], "
        "8-class financial risk taxonomy, calibrated impact score [1, 10], "
        "and Module B Portfolio Stress Testing using yfinance market data."
    ),
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from backend.app.api.routes_risk import router as root_risk_router

# Mount API
app.include_router(api_router)
app.include_router(root_risk_router, tags=["Root Endpoints"])

@app.get("/")
def root():
    return {
        "status": "online",
        "service": settings.APP_NAME,
        "docs_url": "/docs",
        "api_v1": "/api/v1"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
