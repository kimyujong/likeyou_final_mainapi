from fastapi import APIRouter, HTTPException, Query
from .service import get_risk_by_hour
from .schemas import RiskResponse

router = APIRouter(prefix="/m1", tags=["m1"])

# [2024-12-09 수정] 
# M1 모듈의 데이터 조회(Read) 기능은 Spring Boot에서 DB(COM_Location 테이블)를 직접 조회하도록 이관되었습니다.
# 따라서 아래 API는 더 이상 사용되지 않으므로 주석 처리하거나, 테스트 용도로만 남겨둡니다.

# @router.get("/risk", response_model=RiskResponse)
# async def get_road_risk(hour: int = Query(..., ge=0, le=23, description="조회할 시간대 (0~23)")):
#     """
#     (Deprecated) Spring Boot에서 직접 DB를 조회하세요.
#     특정 시간대의 도로별 위험도와 좌표 정보를 조회합니다.
#     """
#     try:
#         data = get_risk_by_hour(hour)
#         
#         if not data:
#             return {
#                 "hour": hour,
#                 "count": 0,
#                 "data": []
#             }
#             
#         return {
#             "hour": hour,
#             "count": len(data),
#             "data": data
#         }
#     except Exception as e:
#         import traceback
#         traceback.print_exc()
#         raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@router.get("/")
def m1_info():
    return {
        "message": "M1 Module is data-ready.",
        "note": "Please query 'COM_Location' table directly from Spring Boot."
    }
