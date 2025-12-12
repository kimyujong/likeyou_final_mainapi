"""
M4 낙상 감지기
"""

import cv2
import numpy as np
from datetime import datetime

from .constants import FallStatus, DEFAULT_CONFIRM_FRAMES
from .utils import is_fallen


class FallDetector:
    """
    낙상 감지 시스템 (연속 프레임 검증 포함)
    """
    def __init__(self, model, confirm_frames=DEFAULT_CONFIRM_FRAMES, 
                 fall_threshold=0.30):
        """
        Args:
            model: YOLOPoseModel 인스턴스
            confirm_frames: 낙상 확정을 위한 연속 프레임 수
            fall_threshold: 낙상 판별 임계값
        """
        self.model = model
        self.confirm_frames = confirm_frames
        self.fall_threshold = fall_threshold
        
        # 상태 변수
        self.consecutive_fall_frames = 0
        self.total_fall_count = 0
        self.current_status = FallStatus.NORMAL
        self.fall_events = []  # 낙상 이벤트 기록
        
        print(f"FallDetector 초기화:")
        print(f"  확정 프레임 수: {confirm_frames}")
        print(f"  낙상 임계값: {fall_threshold}")
    
    def detect_frame(self, frame):
        """
        단일 프레임에서 낙상 감지
        
        Args:
            frame: OpenCV BGR 이미지
        
        Returns:
            dict: {
                'status': FallStatus,
                'fall_detected': bool,
                'fall_count': int,
                'fallen_persons': list,
                'keypoints': list
            }
        """
        h, w = frame.shape[:2]
        
        # YOLO 추론
        results = self.model.predict(frame, conf=0.25, verbose=False)
        
        # 키포인트 추출
        keypoints_list = self.model.get_keypoints(results)
        
        # 낙상 여부 확인
        fall_detected_now = False
        fallen_persons = []
        
        for idx, kp in enumerate(keypoints_list):
            if is_fallen(kp, h, threshold=self.fall_threshold):
                fall_detected_now = True
                fallen_persons.append({
                    'person_id': idx,
                    'keypoints': kp
                })
        
        # 연속 프레임 검증 (오탐 방지)
        if fall_detected_now:
            self.consecutive_fall_frames += 1
            status = FallStatus.SUSPECTED
        else:
            self.consecutive_fall_frames = 0
            status = FallStatus.NORMAL
        
        # 낙상 확정
        fall_confirmed = False
        if self.consecutive_fall_frames >= self.confirm_frames:
            status = FallStatus.FALLEN
            fall_confirmed = True
            
            # 새로운 낙상 이벤트 기록 (처음 확정된 순간만)
            if self.consecutive_fall_frames == self.confirm_frames:
                self.total_fall_count += 1
                self.fall_events.append({
                    'timestamp': datetime.now(),
                    'fall_id': self.total_fall_count,
                    'persons_count': len(fallen_persons)
                })
        
        self.current_status = status
        
        return {
            'status': status,
            'fall_detected': fall_confirmed,
            'fall_count': self.total_fall_count,
            'fallen_persons': fallen_persons,
            'consecutive_frames': self.consecutive_fall_frames,
            'keypoints': keypoints_list,
            'results': results  # YOLO 원본 결과
        }
    
    def reset(self):
        """감지 상태 초기화"""
        self.consecutive_fall_frames = 0
        self.total_fall_count = 0
        self.current_status = FallStatus.NORMAL
        self.fall_events = []
    
    def get_fall_events(self):
        """낙상 이벤트 기록 반환"""
        return self.fall_events

