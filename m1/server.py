import uvicorn
import sys
import os
import asyncio
from fastapi import FastAPI
# from fastapi.responses import FileResponse  # [테스트용] 주석 처리
from fastapi.middleware.cors import CORSMiddleware

# 현재 디렉토리를 sys.path에 추가하여 같은 폴더의 모듈 import 가능하게 함
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# 모듈 import
try:
    from router import router as m1_router
    # from save_to_db import save_to_supabase  # [참고] 초기 DB 데이터 적재가 필요할 때 test/save_to_db.py를 사용하세요.
except ImportError:
    from .router import router as m1_router
    # from .save_to_db import save_to_supabase

app = FastAPI(title="M1 Road Risk API", version="1.0.0")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(m1_router)

# [테스트용] HTML 시각화 페이지 서빙 (배포 시 주석 처리 권장)
# @app.get("/test", response_class=FileResponse)
# def test_view():
#     """
#     지도 시각화 테스트 페이지를 반환합니다.
#     """
#     # 현재 파일(main.py) 기준 상대 경로로 HTML 파일 찾기
#     html_path = os.path.join(current_dir, "test", "test_m1_view.html")
#     return html_path

@app.on_event("startup")
async def startup_event():
    """
    서버 시작 시 실행되는 이벤트입니다.
    """
    print("\n[Startup] 서버 시작!")
    # [참고] 아래 코드는 서버 시작 시 자동으로 DB 데이터를 동기화하는 로직이었습니다.
    # save_to_db.py 파일이 test/ 폴더로 이동되었으므로, 데이터 적재가 필요한 경우 해당 스크립트를 직접 실행하세요.
    # 
    # try:
    #     print("[Startup] save_to_supabase() 호출...")
    #     save_to_supabase()
    #     print("[Startup] DB 동기화 완료 작업 끝.")
    # except Exception as e:
    #     print(f"[Startup] DB 동기화 중 오류 발생 (서버는 계속 실행됨): {e}")

@app.get("/")
def root():
    return {"message": "M1 Module is running!", "docs": "/docs"}

if __name__ == "__main__":
    print("Starting M1 Server...")
    # reload=True는 개발 중에 코드 변경 시 자동 재시작
    # M1 Port: 8001
    uvicorn.run("server:app", host="0.0.0.0", port=8001, reload=True)

