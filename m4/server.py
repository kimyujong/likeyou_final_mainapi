"""
M4 낙상 감지 API 서버 (단독 실행용)

- 낙상 감지 모델 로드
- 백그라운드 영상 분석 시뮬레이션
- Supabase DB 연동
"""

import os
import sys
import logging
from typing import Optional
from datetime import datetime
import traceback

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# M4 모듈 import
# 현재 위치(package/M4)가 아닌 상위 패키지 접근을 위해 sys.path 설정 필요
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .api import M4FallDetectionAPI
from .database import get_db

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 환경변수 로드
# 현재 패키지(m4)의 상위 폴더(main_package)에 있는 .env 로드
from pathlib import Path
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# FastAPI 앱 생성
app = FastAPI(
    title="M4 Fall Detection API",
    description="CCTV 낙상 감지 및 경보 시스템",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 변수
m4_api: Optional[M4FallDetectionAPI] = None


@app.on_event("startup")
async def startup_event():
    """서버 시작 시 실행"""
    global m4_api
    
    try:
        logger.info("🚀 M4 낙상 감지 API 서버 시작 중...")
        
        # 1. 모델 설정
        model_path = os.getenv('M4_MODEL_PATH', 'best.pt')  # .env 변수명 변경 (MODEL_PATH -> M4_MODEL_PATH)
        
        if not os.path.exists(model_path):
            # 절대 경로로 시도하거나 경고
            current_dir = os.path.dirname(os.path.abspath(__file__))
            model_path = os.path.join(current_dir, 'best.pt')
            
        logger.info(f"📍 모델 경로: {model_path}")
        
        # 2. M4 API 초기화
        m4_api = M4FallDetectionAPI(
            model_path=model_path,
            device='cuda',
            confirm_frames=30,  # 30프레임(약 1초) 이상 유지 시 확정
            fall_threshold=0.30
        )
        
        logger.info("✅ M4 API 초기화 완료!")
        
        # 3. Supabase 연결 확인
        db = get_db()
        if db.is_enabled():
            logger.info("✅ Supabase 연결 완료!")
        else:
            logger.warning("⚠️ Supabase 미연결 (DB 기능 비활성화)")
            
        # 4. [시뮬레이션] 백그라운드 분석 시작
        # TODO: 실제 시연용 영상 파일 경로로 수정 필수
        # 예: "C:/Users/kyj/Videos/fall_test.mp4"
        test_video_path = os.getenv('M4_TEST_VIDEO_PATH', 'test_file/M4_test01.mp4')
        
        # [수정] 파일 경로 확인 강화
        if not os.path.exists(test_video_path):
            current_dir = os.path.dirname(os.path.abspath(__file__))
            abs_path = os.path.join(current_dir, test_video_path)
            if os.path.exists(abs_path):
                test_video_path = abs_path
            else:
                logger.warning(f"⚠️ Test video not found at: {test_video_path}")
        
        logger.info(f"🎥 Test Video Path: {test_video_path}")
        
        # DB에서 유효한 CCTV ID 조회
        cctv_no = "CCTV-03" # 기본값 (DB 연결 실패 시)
        if db.is_enabled():
            from .database import get_test_cctv_no
            fetched_id = await get_test_cctv_no()
            if fetched_id:
                cctv_no = fetched_id
                logger.info(f"✅ DB에서 테스트용 CCTV ID 확보: {cctv_no}")
            else:
                logger.warning("⚠️ COM_CCTV 테이블이 비어있거나 조회 실패. 테스트용 ID 'CCTV-03'을 사용하지만 DB 저장 시 오류가 발생할 수 있습니다.")
            
        # [수정] 서버 시작 시 자동 실행 제거 (제어 API로 시작)
        # m4_api.start_background_task(test_video_path, cctv_no)
        
        logger.info("✅ M4 API 초기화 완료! (분석 대기 중: /control/start 호출 필요)")
        
    except Exception as e:
        logger.error(f"❌ 서버 시작 실패: {str(e)}")
        logger.error(traceback.format_exc())
        # 시연을 위해 에러가 나도 서버는 죽지 않게 함 (선택 사항)
        # raise


@app.post("/control/start")
async def start_analysis(cctv_no: str, video_path: Optional[str] = None):
    """
    특정 CCTV 낙상 감지 시작 (On-Demand)
    """
    if m4_api is None:
        raise HTTPException(status_code=503, detail="모델이 로드되지 않았습니다.")
    
    # 임시: video_path가 없으면 기본 테스트 영상 사용
    if not video_path:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        video_path = os.path.join(current_dir, 'test_file/M4_test01.mp4')
        
    m4_api.start_background_task(video_path=video_path, cctv_no=cctv_no)
    
    logger.info(f"▶️ 낙상 감지 시작 요청: {cctv_no} (Source: {video_path})")
    return {"status": "started", "cctv_no": cctv_no, "source": video_path}


@app.post("/control/stop")
async def stop_analysis(cctv_no: str):
    """
    분석 중지 (On-Demand)
    """
    if m4_api and hasattr(m4_api, 'processor'):
        m4_api.processor.stop()
        logger.info(f"⏹️ 분석 중지 요청: {cctv_no}")
        return {"status": "stopped", "cctv_no": cctv_no}
    
    return {"status": "error", "message": "Processor not active"}


@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 실행"""
    logger.info("🛑 M4 서버 종료 중...")
    if m4_api and hasattr(m4_api, 'processor'):
        m4_api.processor.stop()


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "service": "M4 Fall Detection API",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
async def health_check():
    """헬스체크"""
    if m4_api is None:
        return {"status": "starting", "model_loaded": False}
    return {"status": "healthy", "model_loaded": True}


@app.get("/events")
async def get_recent_events(limit: int = 10, cctv_no: Optional[str] = None):
    """최근 낙상 이벤트 조회"""
    try:
        from .database import get_events
        events = await get_events(limit=limit, cctv_no=cctv_no)
        return {"count": len(events), "data": events}
    except Exception as e:
        logger.error(f"이벤트 조회 실패: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn
    # M4는 8002번 포트 사용 (M3는 8001번)
    # 모듈 실행(python -m m4.server) 시 앱 경로를 패키지 경로(m4.server:app)로 지정
    uvicorn.run("m4.server:app", host="0.0.0.0", port=8004, reload=True)


