"""
M4 낙상 감지기
"""

import cv2
import numpy as np
from datetime import datetime

from .constants import FallStatus, DEFAULT_CONFIRM_FRAMES
from .utils import is_fallen, is_fallen_by_ratio


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
        self.fall_buffer = 0  # [추가] 낙상 감지 끊김 보정용 버퍼
        self.total_fall_count = 0
        self.current_status = FallStatus.NORMAL
        self.fall_events = []  # 낙상 이벤트 기록
        
        # [이동 거리 추적] 간판/포스터 오탐 방지 (개선된 로직)
        # ID별로 등장 이후 총 이동 거리를 기록
        # 움직인 적이 없는(이동거리 ≈ 0) 객체만 무시하고, 움직이다 멈춘(기절한) 사람은 감지함
        self.object_history = {}  # { id: {'total_dist': 0, 'last_pos': (x,y), 'frame_count': 0} }
        
        print(f"FallDetector 초기화:")
        print(f"  확정 프레임 수: {confirm_frames}")
        print(f"  낙상 임계값: {fall_threshold}")
    
    def detect_frame(self, frame):
        """
        단일 프레임에서 낙상 감지
        """
        h, w = frame.shape[:2]
        
        # YOLO 추론 (Tracking 모드)
        results = self.model.predict(frame, conf=0.25, verbose=False)
        
        # 키포인트 추출
        keypoints_list = self.model.get_keypoints(results)
        boxes = results[0].boxes
        
        # 추적 ID 추출 (track 모드에서만 사용 가능)
        if results[0].boxes.id is not None:
            track_ids = results[0].boxes.id.int().cpu().tolist()
        else:
            track_ids = [-1] * len(boxes) if boxes is not None else []
        
        # 낙상 여부 확인
        fall_detected_now = False
        fallen_persons = []
        
        if boxes is not None:
            # 박스와 키포인트를 함께 확인
            for idx, (box, kp, track_id) in enumerate(zip(boxes, keypoints_list, track_ids)):
                bbox = box.xyxy[0].cpu().numpy()  # [x1, y1, x2, y2]
                center_x, center_y = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
                
                # [예외 처리 1] 화면 가장자리에 잘린 사람 처리
                # 화면 테두리에 닿은 객체는 박스 비율이 왜곡되므로(납작해짐), Ratio 기반 감지를 금지함.
                margin = 5
                is_touching_edge = (bbox[0] < margin) or (bbox[1] < margin) or \
                                   (bbox[2] > w - margin) or (bbox[3] > h - margin)
                
                # [예외 처리 2] 너무 큰 객체 (얼굴 클로즈업 등) 무시
                box_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                if is_touching_edge and box_area > (w * h * 0.3):
                    continue # 이건 아예 무시 (기존 로직 유지)

                # [이동 이력 관리]
                is_static_object = False
                
                if track_id != -1:
                    if track_id not in self.object_history:
                        # 처음 등장한 객체
                        self.object_history[track_id] = {
                            'total_dist': 0, 
                            'last_pos': (center_x, center_y), 
                            'frame_count': 1
                        }
                    else:
                        # 기존 객체: 이동 거리 누적
                        hist = self.object_history[track_id]
                        last_x, last_y = hist['last_pos']
                        
                        # 이동 거리 계산
                        dist = np.sqrt((center_x - last_x)**2 + (center_y - last_y)**2)
                        
                        hist['total_dist'] += dist
                        hist['last_pos'] = (center_x, center_y)
                        hist['frame_count'] += 1
                        
                        # 판단: 등장한 지 꽤 됐는데(30프레임 이상), 총 이동 거리가 너무 짧으면(50픽셀 미만) -> 간판/배경
                        # 움직인 적이 없는 녀석은 무시한다!
                        if hist['frame_count'] > 30 and hist['total_dist'] < 50:
                            is_static_object = True
                
                if is_static_object:
                    continue  # 간판/사진이므로 무시 (움직인 적이 없음)
                
                # 1. 키포인트 기반 정밀 판별
                is_fall_kp = is_fallen(kp, h, threshold=self.fall_threshold)
                
                # 2. 박스 비율 기반 판별
                is_fall_ratio = is_fallen_by_ratio(bbox)
                
                # [스마트 감지 로직]
                valid_kps_count = np.sum((kp[:, 0] > 0) & (kp[:, 1] > 0))
                
                is_final_fall = False
                reason = ''
                
                if valid_kps_count > 10:
                    # 관절이 10개 이상 보이면 -> 관절 정보만 100% 신뢰
                    if is_fall_kp:
                        is_final_fall = True
                        reason = 'keypoint'
                else:
                    # 관절이 잘 안 보이면(멀거나 가려짐) -> 비율 정보도 참고 (백업 가동)
                    if is_fall_kp:
                        is_final_fall = True
                        reason = 'keypoint'
                    # [수정] 화면 테두리에 닿은 객체는 비율 감지(Ratio) 사용 금지
                    # (잘려서 납작해진 것을 낙상으로 오판하는 것 방지)
                    elif is_fall_ratio and not is_touching_edge:
                        is_final_fall = True
                        reason = 'ratio'
                
                if is_final_fall:
                    fall_detected_now = True
                    fallen_persons.append({
                        'person_id': idx,
                        'track_id': track_id,
                        'keypoints': kp,
                        'bbox': bbox,
                        'reason': reason
                    })
        
        # 연속 프레임 검증 (오탐 방지) & 깜빡임 보정
        if fall_detected_now:
            self.consecutive_fall_frames += 1
            self.fall_buffer = 5  # 낙상이 감지되면 버퍼 충전 (5프레임 동안은 끊겨도 봐줌)
            status = FallStatus.SUSPECTED
        else:
            if self.fall_buffer > 0:
                # 낙상이 아니지만, 버퍼가 남아있으면 카운트 유지 (리셋 안 함)
                # 단, 카운트를 증가시키진 않음 (현상 유지)
                self.fall_buffer -= 1
                status = FallStatus.SUSPECTED
            else:
                # 버퍼도 다 떨어졌으면 진짜 일어난 것 -> 리셋
                self.consecutive_fall_frames = 0
                status = FallStatus.NORMAL
        
        # 낙상 확정 (기준 완화: 카운트가 쌓여있으면 확정)
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
        self.object_history = {}
    
    def get_fall_events(self):
        """낙상 이벤트 기록 반환"""
        return self.fall_events
