"""
M4 CCTV 낙상 감지 시스템

YOLOv8-pose 기반 실시간 낙상 감지 및 경보
"""

__version__ = "1.0.0"
__author__ = "Fall Detection Team"

from .constants import FallStatus, KEYPOINT_INDICES
from .model import YOLOPoseModel
from .detector import FallDetector
from .alert import FallAlertSystem
from .api import M4FallDetectionAPI
from .utils import is_fallen, draw_fall_warning

__all__ = [
    'FallStatus',
    'KEYPOINT_INDICES',
    'YOLOPoseModel',
    'FallDetector',
    'FallAlertSystem',
    'M4FallDetectionAPI',
    'is_fallen',
    'draw_fall_warning'
]

