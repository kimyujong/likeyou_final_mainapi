from pydantic import BaseModel
from typing import List, Optional, Dict, Any

# --- 요청 모델 ---
class LatLng(BaseModel):
    lat: float
    lng: float

class RouteRequest(BaseModel):
    origin: LatLng
    destination: LatLng

# --- 응답 모델 ---
class HeatmapPoint(BaseModel):
    lat: float
    lon: float
    density: int

class CCTVPoint(BaseModel):
    cctv_no: str
    lat: float
    lon: float
    density: int

class RouteInfo(BaseModel):
    distance: float
    duration_min: int

class RouteResponse(BaseModel):
    success: bool
    path: List[LatLng]
    info: RouteInfo
    error: Optional[str] = None

class HeatmapResponse(BaseModel):
    success: bool
    data: List[HeatmapPoint]

class CCTVResponse(BaseModel):
    success: bool
    data: List[CCTVPoint]

