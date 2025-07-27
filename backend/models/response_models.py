from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

class BaseResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    timestamp: datetime = datetime.now()

class ErrorResponse(BaseResponse):
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class BiographyData(BaseModel):
    name: str
    coordinates: List[List[float]] = []  # 坐标数组，每个元素为[经度, 纬度]
    descriptions: List[str] = []  # 对应坐标的事件描述数组

class BiographyResponse(BaseResponse):
    data: Optional[BiographyData] = None

class HealthStatus(BaseModel):
    status: str
    service: str
    version: str = "1.0.0"
    uptime: Optional[str] = None
    dependencies: Optional[Dict[str, str]] = None

class HealthResponse(BaseResponse):
    data: HealthStatus