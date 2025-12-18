import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드
# env_path = Path(__file__).resolve().parent.parent / '.env'
env_path = Path("/home/ubuntu/main-api/.env")
load_dotenv(dotenv_path=env_path)

# 현재 파일의 위치: .../package/m2/server.py
# 패키지 루트(.../package 의 상위)를 sys.path에 추가해야 'package.m2' 모듈을 찾을 수 있음
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_dir)) # package/m2 -> package -> root
sys.path.append(root_dir)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from m2.router import router as m2_router
import uvicorn

app = FastAPI(title="M2 Module Server")

# 1. CORS 설정 (모든 곳에서 접근 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. M2 라우터 등록
app.include_router(m2_router)

# 3. 테스트용 HTML 파일 서빙
# http://localhost:8003/view/test_view.html 로 접속 가능하게 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
M2_DIR = BASE_DIR # 현재 파일이 m2 폴더 안에 있으므로 BASE_DIR이 곧 M2_DIR

if os.path.exists(M2_DIR):
    app.mount("/view", StaticFiles(directory=M2_DIR), name="view")

if __name__ == "__main__":
    print("================================================================")
    print("🚀 M2 서버가 시작됩니다!")
    print("👉 API 문서: http://localhost:8002/docs")
    print("👉 테스트 화면: http://localhost:8002/view/test_view.html")
    print("================================================================")
    
    # Reload 옵션은 개발 시 코드 수정하면 자동 재시작
    # M2 Port: 8003 (Changed from 8000)
    uvicorn.run("m2.server:app", host="0.0.0.0", port=8002, reload=False)

