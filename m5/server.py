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
from m5.router import router as m5_router
from dotenv import load_dotenv

# [환경변수 설정]
# 현재 파일(server.py)이 있는 폴더 기준으로 절대 경로 설정
current_file = Path(__file__).resolve()
base_dir = current_file.parent

# .env 로드 (상위 폴더)
env_path = Path("/home/ubuntu/main-api/.env")
load_dotenv(dotenv_path=env_path)

# [수정] 환경변수가 있으면 우선 사용하고, 없으면 기본값 사용
os.environ["M5_MODEL_DIR"] = os.getenv("M5_MODEL_DIR", str(base_dir / "saved_models"))
os.environ["M5_WEATHER_DATA"] = os.getenv("M5_WEATHER_DATA", str(base_dir / "total_weather.xlsx"))

# 기상청 API 키
os.environ["WEATHER_API_KEY"] = os.getenv("WEATHER_API_KEY", "")

# [DB 설정] Supabase 정보 로드
os.environ["SUPABASE_URL"] = os.getenv("SUPABASE_URL", "")
os.environ["SUPABASE_KEY"] = os.getenv("SUPABASE_KEY", "")

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
    uvicorn.run("m5.server:app", host="0.0.0.0", port=8005)

