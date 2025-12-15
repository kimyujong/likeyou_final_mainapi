"""
영상 처리 모듈 (M4)

영상 파일에서 프레임을 추출하고 YOLO-Pose 모델로 분석
주기적 구간 감시 (Periodic Interval Monitoring) 전략 사용
"""

import cv2
import os
import logging
import asyncio
from typing import Optional
from .database import save_fall_event

logger = logging.getLogger(__name__)


class VideoProcessorM4:
    """M4 영상 처리 및 분석 클래스"""
    
    def __init__(self, api_instance):
        """
        Args:
            api_instance: M4FallDetectionAPI 인스턴스
        """
        self.api = api_instance
        self.stop_event = asyncio.Event()
    
    async def process_stream_simulation(
        self,
        video_path: str,
        cctv_no: str,
        interval_seconds: int = 10,
        analysis_duration: int = 3
    ):
        """
        영상 스트리밍 시뮬레이션 (무한 루프 + 주기적 구간 분석)
        
        Args:
            video_path: 영상 파일 경로
            cctv_no: CCTV 식별자
            interval_seconds: 분석 주기 (초) - 기본 10초
            analysis_duration: 분석할 구간 길이 (초) - 기본 3초 (약 90프레임)
        """
        if not os.path.exists(video_path):
            logger.error(f"영상 파일을 찾을 수 없습니다: {video_path}")
            return
            
        logger.info(f"🚀 M4 시뮬레이션 시작: {cctv_no}")
        logger.info(f"   설정: {interval_seconds}초마다 {analysis_duration}초씩 분석")
        logger.info(f"📂 영상 소스: {video_path}")
        
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0: fps = 30  # FPS 정보 없으면 기본 30 가정
        
        frames_to_analyze = int(fps * analysis_duration)  # 분석할 총 프레임 수
        
        try:
            while not self.stop_event.is_set():
                logger.info(f"👁️ 감시 시작 ({analysis_duration}초 구간 분석)")
                
                detected_in_cycle = False
                
                # 1. 구간 집중 분석
                for _ in range(frames_to_analyze):
                    if not cap.isOpened():
                        cap = cv2.VideoCapture(video_path)
                    
                    ret, frame = cap.read()
                    
                    # 영상 끝이면 처음으로 되감기
                    if not ret:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, frame = cap.read()
                        if not ret: break
                    
                    # 분석
                    try:
                        result = self.api.detector.detect_frame(frame)
                        should_alert, alert_msg = self.api.alert_system.check_alert(result)
                        
                        # 낙상 감지 시 (이번 주기 내)
                        if should_alert and not detected_in_cycle:
                            logger.warning(f"🚨 낙상 감지! ({cctv_no}): {len(result['fallen_persons'])}명")
                            detected_in_cycle = True
                            
                            # DB 저장
                            try:
                                result_db = await save_fall_event(cctv_no=cctv_no)
                                if result_db:
                                    logger.info(f"💾 낙상 이벤트 DB 저장 완료")
                                else:
                                    logger.warning(f"⚠️ 낙상 이벤트 DB 저장 실패 (리턴값 None)")
                            except Exception as e:
                                logger.error(f"DB 저장 실패: {e}")
                                
                    except Exception as e:
                        logger.error(f"프레임 분석 실패: {e}")
                    
                    # 프레임 간 딜레이 (실제 재생 속도 시뮬레이션)
                    # 너무 빠르면 CPU 점유율이 튀므로 약간 조절
                    await asyncio.sleep(0.005)
                
                # 2. 휴식 (Sleep) 및 영상 시간 건너뛰기
                logger.info(f"💤 {interval_seconds}초 대기 (영상도 {interval_seconds}초 건너뜀)...")
                
                # 영상 프레임 포인터 이동 (실시간성 시뮬레이션)
                current_pos = cap.get(cv2.CAP_PROP_POS_FRAMES)
                skip_frames = int(fps * interval_seconds)
                new_pos = current_pos + skip_frames
                
                # 영상 길이 초과 시 처음부터 계산
                total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                if new_pos >= total_frames:
                    new_pos = new_pos % total_frames
                    
                cap.set(cv2.CAP_PROP_POS_FRAMES, new_pos)
                
                await asyncio.sleep(interval_seconds)
                
        finally:
            cap.release()
            logger.info(f"🛑 M4 시뮬레이션 종료: {cctv_no}")

    def stop(self):
        """시뮬레이션 중지 신호"""
        self.stop_event.set()
