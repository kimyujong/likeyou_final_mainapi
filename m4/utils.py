"""
M4 시스템 유틸리티 함수
"""

import cv2
import numpy as np
from PIL import Image, ImageFont, ImageDraw

from .constants import KEYPOINT_INDICES, DEFAULT_FALL_THRESHOLD


def is_fallen(keypoints, frame_height, threshold=0.5):
    """
    키포인트 기반 낙상 판별 (앉은 자세 포함 개선)
    """
    try:
        # 주요 관절 y좌표
        shoulder_y = np.mean([
            keypoints[KEYPOINT_INDICES['left_shoulder']][1],
            keypoints[KEYPOINT_INDICES['right_shoulder']][1]
        ])
        hip_y = np.mean([
            keypoints[KEYPOINT_INDICES['left_hip']][1],
            keypoints[KEYPOINT_INDICES['right_hip']][1]
        ])
        ankle_y = np.mean([
            keypoints[KEYPOINT_INDICES['left_ankle']][1],
            keypoints[KEYPOINT_INDICES['right_ankle']][1]
        ])
        knee_y = np.mean([
            keypoints[KEYPOINT_INDICES['left_knee']][1],
            keypoints[KEYPOINT_INDICES['right_knee']][1]
        ])
        
        # 0. 관절 신뢰도 체크
        if shoulder_y == 0 or hip_y == 0 or ankle_y == 0:
            return False

        # 1. 수직 길이 계산
        torso_len = abs(hip_y - shoulder_y)       # 상체 길이
        lower_body_len = abs(ankle_y - hip_y)     # 하체 전체 길이 (엉덩이~발목)
        thigh_len = abs(knee_y - hip_y)           # 허벅지 길이 (엉덩이~무릎)
        
        # 전체 추정 키 (서 있을 때 기준)
        total_height = torso_len * 1.6 + lower_body_len
        if total_height == 0: return False

        # --- 판별 로직 ---
        
        # Case A: 완전히 쓰러짐 (누움)
        # 상체가 매우 낮아짐 (전체 키 대비 25% 미만)
        is_lying_down = torso_len < (total_height * 0.25)
        
        # Case B: 주저 앉음 (Sitting / Slumping)
        # 특징: 엉덩이가 낮아짐 -> 무릎이 굽혀짐
        
        # [걷는 사람 오탐 방지 핵심]
        # 걸어오는 사람은 원근법 때문에 상체가 커 보이고 하체가 짧아 보일 수 있음.
        # 하지만 "서 있는 상태"라면 무릎은 엉덩이보다 확실히 아래에 있어야 함.
        
        # 엉덩이~무릎 수직 거리 (허벅지 길이)
        thigh_vertical_len = knee_y - hip_y  # y좌표는 아래가 큼
        
        # 주저 앉음 판단 조건 강화:
        # 1. 엉덩이가 발목 가까이 내려옴 (하체 압축)
        # 2. AND 허벅지 수직 길이가 매우 짧음 (무릎이 엉덩이 높이까지 올라옴)
        
        # 서 있는 사람: thigh_vertical_len이 큼 (최소 전체 키의 15% 이상)
        # 주저 앉은 사람: thigh_vertical_len이 작음 (무릎이 엉덩이와 수평에 가까워짐)
        
        is_standing = thigh_vertical_len > (total_height * 0.15)
        
        if is_standing:
            return False  # 서 있으면 무조건 낙상 아님 (걷는 사람 제외)
        
        # 이하 낙상 상세 판별
        
        # Case A: 완전히 쓰러짐 (누움)
        is_lying_down = torso_len < (total_height * 0.25)
        
        # Case B: 주저 앉음 (Sitting / Slumping)
        # 다리가 접혔고 AND 서 있지 않음(위에서 이미 걸러짐)
        is_legs_folded = lower_body_len < (torso_len * 0.8)
        
        return is_lying_down or is_legs_folded
        
    except Exception:
        return False


def is_fallen_by_ratio(bbox):
    """
    Bounding Box 비율 기반 낙상 판별 (주저앉음 감지 추가)
    """
    try:
        x1, y1, x2, y2 = bbox
        width = x2 - x1
        height = y2 - y1
        
        if height == 0: return False
        
        ratio = width / height
        
        # 1. 완전히 누움: 가로가 훨씬 김 (2.0 이상)
        if ratio > 2.0:
            return True
            
        # 2. 주저 앉음: 정사각형에 가까워짐 (0.9 ~ 1.5)
        # 서 있는 사람은 보통 0.3 ~ 0.5 (세로가 김)
        # 따라서 0.9 이상이면 '서 있지 않다'고 볼 수 있음
        if ratio > 0.9:
            return True
            
        return False
        
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
