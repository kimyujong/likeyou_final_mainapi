from fastapi import APIRouter, HTTPException, Depends
from typing import List
from .schemas import (
    RouteRequest, RouteResponse, 
    HeatmapResponse, CCTVResponse,
    RouteInfo, LatLng
)
from .service import M2Service

router = APIRouter(
    prefix="/m2",
    tags=["m2-safe-route"]
)

# Singleton Instance
m2_service = None

def get_service():
    global m2_service
    if m2_service is None:
        m2_service = M2Service()
    return m2_service

@router.on_event("startup")
async def startup_event():
    """서버 시작 시 무거운 데이터 로드"""
    get_service()

@router.post("/route", response_model=RouteResponse)
async def calculate_safe_route(req: RouteRequest, service: M2Service = Depends(get_service)):
    """
    [안심 경로] 출발지/도착지를 받아 밀집도를 피하는 최적 경로를 반환합니다.
    """
    try:
        path, dist, duration = service.find_shortest_path(
            req.origin.lat, req.origin.lng,
            req.destination.lat, req.destination.lng
        )
        
        # Pydantic 모델 변환
        path_objs = [LatLng(lat=p['lat'], lng=p['lng']) for p in path]
        
        return RouteResponse(
            success=True,
            path=path_objs,
            info=RouteInfo(distance=dist, duration_min=duration)
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return RouteResponse(success=False, path=[], info=RouteInfo(distance=0), error=str(e))

@router.get("/heatmap", response_model=HeatmapResponse)
async def get_heatmap(service: M2Service = Depends(get_service)):
    """
    [히트맵] 현재 계산된 밀집도 히트맵 데이터를 반환합니다.
    """
    data = service.get_heatmap_list()
    return HeatmapResponse(success=True, data=data)

@router.get("/cctv", response_model=CCTVResponse)
async def get_cctv(service: M2Service = Depends(get_service)):
    """
    [CCTV] 필터링된 CCTV 위치 및 밀집도 정보를 반환합니다.
    """
    data = service.get_cctv_list()
    return CCTVResponse(success=True, data=data)

