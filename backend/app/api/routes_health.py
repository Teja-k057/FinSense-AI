from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.database.connection import get_db
from backend.app.schemas.common import HealthResponse, APIResponse
from backend.app.config.settings import settings

router = APIRouter()

@router.get("/health", response_model=APIResponse[HealthResponse])
def get_system_health(db: Session = Depends(get_db)):
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    health_info = HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        app_name=settings.APP_NAME,
        environment=settings.APP_ENV,
        database_status=db_status,
        models_ready=True
    )
    return APIResponse(status="success", data=health_info)
