"""
YOLO Pose 모델 로더
"""

from ultralytics import YOLO
import torch


class YOLOPoseModel:
    """
    YOLOv8-pose 모델 로더 및 관리 클래스
    """
    def __init__(self, model_path='best.pt', device='cuda'):
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
    
    def predict(self, frame, conf=0.25, verbose=False):
        """
        프레임에서 포즈 추론
        
        Args:
            frame: OpenCV BGR 이미지
            conf: 신뢰도 임계값
            verbose: 상세 출력 여부
        
        Returns:
            results: YOLO 결과 객체
        """
        results = self.model(frame, conf=conf, verbose=verbose, device=self.device)
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

