"""
M4 시스템 유틸리티 함수
"""

import cv2
import numpy as np
from PIL import Image, ImageFont, ImageDraw

from constants import KEYPOINT_INDICES, DEFAULT_FALL_THRESHOLD


def is_fallen(keypoints, frame_height, threshold=DEFAULT_FALL_THRESHOLD):
    """
    키포인트 기반 낙상 판별
    
    Args:
        keypoints: numpy array of shape (17, 2) - COCO pose 키포인트
        frame_height: 영상 높이 (픽셀)
        threshold: 낙상 판별 임계값 (기본 0.30)
    
    Returns:
        bool: True(낙상), False(정상)
    
    알고리즘:
        - 어깨(5,6)와 엉덩이(11,12)의 y좌표 평균 계산
        - 수직 거리가 frame_height * threshold보다 작으면 낙상
    """
    try:
        # 어깨 y좌표 평균
        shoulder_y = np.mean([
            keypoints[KEYPOINT_INDICES['left_shoulder']][1],
            keypoints[KEYPOINT_INDICES['right_shoulder']][1]
        ])
        
        # 엉덩이 y좌표 평균
        hip_y = np.mean([
            keypoints[KEYPOINT_INDICES['left_hip']][1],
            keypoints[KEYPOINT_INDICES['right_hip']][1]
        ])
        
        # 수직 거리 계산
        vertical_dist = abs(hip_y - shoulder_y)
        
        # 거리가 임계값보다 작으면 낙상
        return vertical_dist < frame_height * threshold
        
    except Exception:
        return False


def put_korean_text(img, text, position, font_size=30, color=(255, 255, 255)):
    """
    OpenCV 이미지에 한글 텍스트 표시
    
    Args:
        img: OpenCV BGR 이미지
        text: 표시할 텍스트
        position: (x, y) 위치
        font_size: 폰트 크기
        color: BGR 색상
    
    Returns:
        img: 텍스트가 추가된 이미지
    """
    img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)
    
    # 한글 폰트
    try:
        font = ImageFont.truetype("malgun.ttf", font_size)
    except:
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", font_size)
        except:
            font = ImageFont.load_default()
    
    # PIL은 RGB 사용
    color_rgb = (color[2], color[1], color[0]) if len(color) == 3 else color
    draw.text(position, text, font=font, fill=color_rgb)
    
    # OpenCV로 변환
    img_cv = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
    return img_cv


def draw_fall_warning(frame, fall_count=0, status="NORMAL"):
    """
    낙상 경고 화면에 표시
    
    Args:
        frame: OpenCV 프레임
        fall_count: 낙상 감지 횟수
        status: 상태 ("NORMAL", "SUSPECTED", "FALLEN")
    
    Returns:
        frame: 경고가 표시된 프레임
    """
    if status == "FALLEN":
        # 경고 배경
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame.shape[1], 150), (0, 0, 255), -1)
        frame = cv2.addWeighted(overlay, 0.3, frame, 0.7, 0)
        
        # 경고 텍스트
        cv2.putText(frame, "⚠ FALL DETECTED ⚠", (50, 100),
                   cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 4)
        
        # 한글 경고
        frame = put_korean_text(frame, "낙상 감지!", (50, 120), 
                               font_size=40, color=(255, 255, 255))
    
    # 감지 횟수 표시
    if fall_count > 0:
        cv2.putText(frame, f"Falls: {fall_count}", (frame.shape[1] - 200, 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    
    return frame


def calculate_body_angle(keypoints):
    """
    신체 기울기 각도 계산 (추가 판별 지표)
    
    Args:
        keypoints: numpy array of shape (17, 2)
    
    Returns:
        float: 각도 (도) - 0도=수평, 90도=수직
    """
    try:
        # 어깨 중심
        shoulder_center = np.mean([
            keypoints[KEYPOINT_INDICES['left_shoulder']],
            keypoints[KEYPOINT_INDICES['right_shoulder']]
        ], axis=0)
        
        # 엉덩이 중심
        hip_center = np.mean([
            keypoints[KEYPOINT_INDICES['left_hip']],
            keypoints[KEYPOINT_INDICES['right_hip']]
        ], axis=0)
        
        # 벡터 계산
        vec = hip_center - shoulder_center
        
        # 수직선(0, 1)과의 각도 계산
        angle = np.arctan2(abs(vec[0]), abs(vec[1])) * 180 / np.pi
        
        return angle
        
    except Exception:
        return 90  # 기본값 (수직)

