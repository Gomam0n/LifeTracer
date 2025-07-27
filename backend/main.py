from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
from services.biography_service import BiographyService
from models.response_models import (
    BiographyResponse,
)
app = FastAPI(
    title="LifeTracer API",
    description="历史名人生平足迹可视化API",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # need to change in production 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化服务
biography_service = BiographyService()

class PersonRequest(BaseModel):
    name: str
    language: Optional[str] = "zh"  # 默认中文
    detail_level: Optional[str] = "medium"  # basic, medium, detailed

class LocationRequest(BaseModel):
    locations: List[str]
    country: Optional[str] = None
    historical_period: Optional[str] = None

@app.get("/")
async def root():
    return {"message": "LifeTracer API is running"}

@app.post("/api/biography", response_model=BiographyResponse)
async def get_biography(request: PersonRequest):
    """
    获取历史人物的生平信息
    """
    try:
        #return get_test_biography("苏轼")
        biography_data = await biography_service.get_biography(
            name=request.name,
            language=request.language,
            detail_level=request.detail_level
        )
        return BiographyResponse(
            success=True,
            data=biography_data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """
    健康检查接口
    """
    return {"status": "healthy", "service": "LifeTracer API"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )