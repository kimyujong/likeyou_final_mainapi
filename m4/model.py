"""
YOLO Pose 모델 로더
"""

from ultralytics import YOLO
import torch


class YOLOPoseModel:
    """
    YOLOv8-pose 모델 로더 및 관리 클래스
    """
    def __init__(self, model_path='yolov8n-pose.pt', device='cuda'):
        """
        Args:
            model_path: YOLO 모델 파일 경로 (.pt)
            device: 'cuda' 또는 'cpu'
        """
        self.device = device if torch.cuda.is_available() else 'cpu'
        self.model_path = model_path
        
        # YOLO 모델 로드
        self.model = YOLO(model_path)
        
        print(f"✅ YOLO Pose 모델 로드 완료")
        print(f"   모델: {model_path}")
        print(f"   디바이스: {self.device}")
    
    def predict(self, frame, conf=0.25, verbose=False, imgsz=1280):
        """
        프레임에서 포즈 추론 (Tracking 포함)
        """
        # track 모드로 변경하여 객체 ID를 부여받음 (이동 거리 계산용)
        # persist=True: 프레임 간 ID 유지
        # [수정] OpenCV GMC 에러 방지를 위해 tracker="bytetrack.yaml" 명시
        results = self.model.track(frame, conf=conf, verbose=verbose, device=self.device, imgsz=imgsz, 
                                 persist=True, tracker="bytetrack.yaml")
        return results
    
    def get_keypoints(self, results):
        """
        결과에서 키포인트 추출
        
        Args:
            results: YOLO 결과 객체
        
        Returns:
            list: 키포인트 배열 리스트 [(17, 2), ...]
        """
        keypoints_list = []
        
        if results[0].keypoints is not None and len(results[0].keypoints.xy) > 0:
            for kp in results[0].keypoints.xy:
                keypoints_list.append(kp.cpu().numpy())
        
        return keypoints_list
