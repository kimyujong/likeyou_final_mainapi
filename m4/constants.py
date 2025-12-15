"""
M4 시스템 상수 정의
"""

from enum import Enum


class FallStatus(Enum):
    """낙상 상태"""
    NORMAL = ("정상", (0, 255, 0))      # 녹색
    SUSPECTED = ("의심", (255, 255, 0))  # 노란색
    FALLEN = ("낙상", (0, 0, 255))       # 빨간색
    
    def __init__(self, korean, color):
        self.korean = korean
        self.color = color  # BGR 색상


# COCO Pose 키포인트 인덱스
KEYPOINT_INDICES = {
    'nose': 0,
    'left_eye': 1,
    'right_eye': 2,
    'left_ear': 3,
    'right_ear': 4,
    'left_shoulder': 5,
    'right_shoulder': 6,
    'left_elbow': 7,
    'right_elbow': 8,
    'left_wrist': 9,
    'right_wrist': 10,
    'left_hip': 11,
    'right_hip': 12,
    'left_knee': 13,
    'right_knee': 14,
    'left_ankle': 15,
    'right_ankle': 16
}

# 기본 설정값
DEFAULT_FALL_THRESHOLD = 0.30  # 어깨-엉덩이 거리 비율 (낮을수록 쓰러진 상태)
DEFAULT_CONFIRM_FRAMES = 10  # 낙상 확정을 위한 연속 프레임 수
DEFAULT_CONFIDENCE = 0.25  # YOLO 신뢰도 임계값
DEFAULT_ALERT_COOLDOWN = 5  # 경보 쿨다운 (초)

# CCTV ID 매핑 (사용자 편의용 Alias -> 실제 UUID)
CCTV_MAPPING = {
    "CCTV-03": "0868424b-02e1-41ad-84a9-541c0f21f16c",
    "CCTV-04": "0ae0d27a-55a5-400d-923e-ee738e443eb5"
}

