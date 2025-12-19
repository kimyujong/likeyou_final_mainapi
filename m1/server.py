import uvicorn
import sys
import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드 (상위 폴더)
# env_path = Path(__file__).resolve().parent.parent / '.env'
env_path = Path("/home/ubuntu/main-api/.env")
load_dotenv(dotenv_path=env_path)

from fastapi import FastAPI
# from fastapi.responses import FileResponse  # [테스트용] 주석 처리
from fastapi.middleware.cors import CORSMiddleware

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# 모듈 import
try:
    from router import router as m1_router
except ImportError:
    from m1.router import router as m1_router

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

@app.on_event("startup")
async def startup_event():
    """
    서버 시작 시 실행되는 이벤트입니다.
    """
    print("\n[Startup] 서버 시작!")

@app.get("/")
def root():
    return {"message": "M1 Module is running!", "docs": "/docs"}

# /health 엔드포인트
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "M1 Road Risk API",
        "model_loaded": True
    }

# if __name__ == "__main__":
#     print("Starting M1 Server...")
#     # reload=True는 개발 중에 코드 변경 시 자동 재시작
#     # M1 Port: 8001
#     uvicorn.run("m1.server:app", host="0.0.0.0", port=8001, reload=True)


