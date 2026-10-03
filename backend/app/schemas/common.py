from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel

T = TypeVar("T")

class APIResponse(BaseModel, Generic[T]):
    status: str = "success"
    message: Optional[str] = None
    data: Optional[T] = None
    meta: Optional[dict[str, Any]] = None

class HealthResponse(BaseModel):
    status: str
    app_name: str
    environment: str
    database_status: str
    models_ready: bool
