from fastapi import APIRouter, HTTPException, Query
from .service import get_risk_by_hour
from .schemas import RiskResponse

router = APIRouter(prefix="/m1", tags=["m1"])

@router.get("/risk", response_model=RiskResponse)
async def get_road_risk(hour: int = Query(..., ge=0, le=23, description="조회할 시간대 (0~23)")):
    """
    특정 시간대의 도로별 위험도와 좌표 정보를 조회합니다.
    """
    try:
        data = get_risk_by_hour(hour)
        
        return {
            "hour": hour,
            "count": len(data) if data else 0,
            "data": data if data else []
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@router.get("/")
def m1_info():
    return {
        "message": "M1 Module is data-ready.",
        "note": "Please query 'COM_Location' table directly from Spring Boot."
    }
