"""
M4 시스템 설정
"""

import os


class M4Config:
    """M4 낙상 감지 시스템 설정 클래스"""
    
    # 경로 설정
    BASE_DIR = 'C:/Users/user/m3_p2pnet'  # 또는 적절한 경로
    MODEL_PATH = './251125/training/fall_detection/weights/best.pt'  # 학습된 모델
    
    # 모델 설정
    DEVICE = 'cuda'
    CONFIDENCE = 0.25  # YOLO 신뢰도 임계값
    
    # 낙상 감지 설정
    FALL_THRESHOLD = 0.30  # 어깨-엉덩이 거리 비율
    CONFIRM_FRAMES = 10  # 낙상 확정 연속 프레임 수
    
    # 경보 설정
    ALERT_COOLDOWN = 5  # 경보 쿨다운 (초)
    
    # 비디오 처리 설정
    PROCESS_EVERY_N_FRAMES = 1  # 모든 프레임 처리 (실시간)
    
    # 출력 설정
    OUTPUT_DIR = './fall_detection_outputs'
    LOG_DIR = './fall_detection_logs'
    
    @classmethod
    def get_model_config(cls):
        """모델 설정 딕셔너리 반환"""
        return {
            'model_path': cls.MODEL_PATH,
            'device': cls.DEVICE,
            'confirm_frames': cls.CONFIRM_FRAMES,
            'fall_threshold': cls.FALL_THRESHOLD,
            'alert_cooldown': cls.ALERT_COOLDOWN
        }

