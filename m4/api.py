"""
M4 통합 API (FastAPI 연동용)
"""

import cv2
import numpy as np
import asyncio
import os

from .model import YOLOPoseModel
from .detector import FallDetector
from .alert import FallAlertSystem
from .constants import DEFAULT_CONFIRM_FRAMES
from .database import save_fall_event
from .processor import VideoProcessorM4


class M4FallDetectionAPI:
    """
    FastAPI 서버에서 사용할 M4 낙상 감지 API
    """
    def __init__(self, model_path, device='cuda', 
                 confirm_frames=DEFAULT_CONFIRM_FRAMES,
                 fall_threshold=0.30,
                 alert_cooldown=5):
        """
        Args:
            model_path: YOLO 모델 파일 경로 (.pt)
            device: 'cuda' 또는 'cpu'
            confirm_frames: 낙상 확정 프레임 수
            fall_threshold: 낙상 판별 임계값
            alert_cooldown: 경보 쿨다운 (초)
        """
        # YOLO 모델 로드
        self.yolo_model = YOLOPoseModel(model_path, device)
        
        # 낙상 감지기
        self.detector = FallDetector(
            model=self.yolo_model,
            confirm_frames=confirm_frames,
            fall_threshold=fall_threshold
        )
        
        # 경보 시스템
        self.alert_system = FallAlertSystem(alert_cooldown=alert_cooldown)
        
        # 백그라운드 프로세서 초기화
        self.processor = VideoProcessorM4(self)
        
        print(f"✅ M4FallDetectionAPI 초기화 완료")
        
    def start_background_task(self, video_path, cctv_no):
        """백그라운드 분석 시작"""
        if not os.path.exists(video_path):
            print(f"⚠️ 영상 파일 없음: {video_path}")
            return
            
        asyncio.create_task(
            self.processor.process_stream_simulation(
                video_path=video_path,
                cctv_no=cctv_no,
                interval_seconds=10,    # 10초 주기
                analysis_duration=3     # 3초 구간 분석
            )
        )
    
    async def analyze_image_bytes(self, image_bytes, cctv_no="CCTV-01"):
        """
        바이트 데이터에서 낙상 분석 (FastAPI용)
        
        Args:
            image_bytes: 이미지 바이너리 데이터
            cctv_no: CCTV 식별자 (DB 저장용)
        
        Returns:
            dict: 분석 결과
        """
        # 이미지 디코딩
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # 감지
        result = self.detector.detect_frame(frame)
        
        # 경보 체크
        should_alert, alert_msg = self.alert_system.check_alert(result)
        
        # 낙상 발생 시 DB 저장 (비동기)
        if should_alert:
            # 백그라운드 태스크로 처리하거나 await로 대기
            # 여기서는 await로 처리 (확실한 저장을 위해)
            try:
                await save_fall_event(cctv_no=cctv_no)
            except Exception as e:
                print(f"❌ 낙상 이벤트 DB 저장 실패: {e}")
        
        return {
            'fall_detected': result['fall_detected'],
            'status': result['status'].korean,
            'status_en': result['status'].name,
            'fall_count': result['fall_count'],
            'persons_count': len(result['fallen_persons']),
            'consecutive_frames': result['consecutive_frames'],
            'alert': should_alert,
            'alert_message': alert_msg if should_alert else None
        }
    
    def analyze_frame(self, frame):
        """
        OpenCV 프레임에서 낙상 분석
        
        Args:
            frame: OpenCV BGR 이미지
        
        Returns:
            dict: 분석 결과
        """
        return self.detector.detect_frame(frame)
    
    def reset(self):
        """감지 상태 초기화"""
        self.detector.reset()
    
    def get_fall_events(self):
        """낙상 이벤트 기록 반환"""
        return self.detector.get_fall_events()
    
    def get_alert_history(self):
        """경보 기록 반환"""
        return self.alert_system.get_alert_history()

