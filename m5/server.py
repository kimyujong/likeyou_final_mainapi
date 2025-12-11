import uvicorn
import os
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가 (package 모듈 인식을 위해)
current_file = Path(__file__).resolve()
project_root = current_file.parents[2]  # .../Model
sys.path.append(str(project_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from main_package.m5.router import router as m5_router

# [환경변수 설정]
# 현재 파일(server.py)이 있는 폴더 기준으로 절대 경로 설정
base_dir = current_file.parent
os.environ["M5_MODEL_DIR"] = str(base_dir / "saved_models")
os.environ["M5_WEATHER_DATA"] = str(base_dir / "total_weather.xlsx")

# 기상청 API 키 (디코딩된 키) - 필요시 수정하세요
os.environ["WEATHER_API_KEY"] = "LV9VqydlVHSgjsUjQBB6HzhTyR6Z4XkSzqIfmQzuZaigTc8H5u2iPf7kpxA79doaQq16dxnNCknCZFIxJLftwQ=="

# [DB 설정] 아래 값을 실제 Supabase 정보로 교체해주세요!
os.environ["SUPABASE_URL"] = "https://pvuucwvtvszmyfyxoomh.supabase.co"
os.environ["SUPABASE_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB2dXVjd3Z0dnN6bXlmeXhvb21oIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjI4NDE5NzgsImV4cCI6MjA3ODQxNzk3OH0.9VlllrEPo7Qb6cZYY4BAUzb5PT4TxqbyYgZZxKV7qp0"

app = FastAPI()

# CORS 설정 (프론트엔드 연동 테스트용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(m5_router)

@app.get("/")
def root():
    return {"message": "M5 Prediction API Server is Running!"}

if __name__ == "__main__":
    print("🚀 Starting M5 Server...")
    # M5 Port: 8004 (Changed from 8000)
    print("📄 Swagger UI: http://localhost:8005/docs")
    uvicorn.run(app, host="0.0.0.0", port=8005)

