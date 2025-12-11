# M4 CCTV 낙상 감지 시스템

YOLOv8-pose 기반 실시간 낙상 감지 및 경보 시스템

## 📦 모듈 구조

```
M4/
├── __init__.py          # 패키지 초기화
├── constants.py         # 상수 정의 (FallStatus, 키포인트 등)
├── model.py             # YOLOPoseModel (YOLO 로더)
├── detector.py          # FallDetector (핵심 감지 로직)
├── alert.py             # FallAlertSystem (경보)
├── api.py               # M4FallDetectionAPI (FastAPI용)
├── utils.py             # 유틸리티 함수
├── config.py            # M4Config (설정)
├── requirements.txt     # 필수 패키지
└── README.md            # 이 파일
```

## 🎯 낙상 판별 알고리즘

### 키포인트 기반 판별
```
어깨-엉덩이 수직 거리 < 프레임 높이 × 0.30 → 낙상
```

**원리**:
- 정상적으로 서 있으면: 어깨와 엉덩이의 수직 거리가 큼
- 쓰러지면: 수직 거리가 매우 작아짐

### 연속 프레임 검증 (오탐 방지)
```
10 프레임 연속 낙상 감지 → 낙상 확정
```

**이유**:
- 일시적인 자세 변화 (앉기, 굽히기) 오탐 방지
- 실제 낙상만 감지

## 🚀 빠른 시작

### 1. 기본 사용 (Python)

```python
from M4 import M4FallDetectionAPI
import cv2

# API 초기화
api = M4FallDetectionAPI(
    model_path='path/to/best.pt',
    device='cuda',
    confirm_frames=10
)

# 비디오 처리
cap = cv2.VideoCapture('cctv_video.mp4')

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    result = api.analyze_frame(frame)
    
    if result['fall_detected']:
        print(f"⚠️ 낙상 감지! 총 {result['fall_count']}회")
```

### 2. FastAPI 서버

```python
from fastapi import FastAPI, File, UploadFile
from M4 import M4FallDetectionAPI, M4Config

app = FastAPI()

# M4 API 초기화
m4_api = M4FallDetectionAPI(**M4Config.get_model_config())

@app.post("/detect")
async def detect_fall(file: UploadFile = File(...)):
    contents = await file.read()
    result = m4_api.analyze_image_bytes(contents)
    return result
```

### 3. 실시간 RTSP 스트림

```python
from M4 import FallDetector, YOLOPoseModel
import cv2

# 모델 및 감지기 초기화
model = YOLOPoseModel('best.pt', device='cuda')
detector = FallDetector(model, confirm_frames=10)

# RTSP 연결
cap = cv2.VideoCapture("rtsp://192.168.1.100:554/stream")

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    result = detector.detect_frame(frame)
    
    # 낙상 확정 시 처리
    if result['fall_detected']:
        # 경보 발령
        print(f"🚨 낙상 감지! ({result['fall_count']}회)")
        # 알림 전송, DB 저장 등
```

## 📊 출력 형식

```json
{
  "fall_detected": true,
  "status": "낙상",
  "status_en": "FALLEN",
  "fall_count": 3,
  "persons_count": 1,
  "consecutive_frames": 12,
  "alert": true,
  "alert_message": "🚨 낙상 감지 경보..."
}
```

## 🎨 낙상 상태

| 상태 | 설명 | 색상 |
|------|------|------|
| 🟢 정상 | 일반 상태 | 녹색 |
| 🟡 의심 | 낙상 의심 (연속 프레임 < 10) | 노란색 |
| 🔴 낙상 | 낙상 확정 (연속 프레임 ≥ 10) | 빨간색 |

## ⚙️ 설정

`config.py`에서 설정 변경:

```python
FALL_THRESHOLD = 0.30     # 낙상 판별 임계값 (낮을수록 민감)
CONFIRM_FRAMES = 10       # 확정 프레임 수
ALERT_COOLDOWN = 5        # 경보 쿨다운 (초)
CONFIDENCE = 0.25         # YOLO 신뢰도
```

## 🔧 임계값 조정

### 민감도 증가 (더 많이 감지)
```python
FALL_THRESHOLD = 0.35  # 0.30 → 0.35
CONFIRM_FRAMES = 7     # 10 → 7
```

### 민감도 감소 (오탐 방지)
```python
FALL_THRESHOLD = 0.25  # 0.30 → 0.25
CONFIRM_FRAMES = 15    # 10 → 15
```

## 📝 성능

**테스트 데이터셋 (03_M4_모델성능 측정.ipynb 결과)**:
- **mAP50**: 0.9877 (98.77%)
- **mAP50-95**: 0.7055
- **Precision**: 0.9720
- **Recall**: 0.9863
- **Pose mAP50**: 0.8322
- **Pose mAP50-95**: 0.4828

**학습 데이터**:
- Train: 8,472개 프레임
- Val: 1,843개 프레임
- Test: 1,754개 프레임
- 총 803개 비디오

## 🌐 배포

### Docker

```dockerfile
FROM ultralytics/ultralytics:latest
COPY M4/ /app/M4/
WORKDIR /app
RUN pip install -r M4/requirements.txt
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
```

### AWS

- **EC2**: GPU 인스턴스 (p3.2xlarge) - FastAPI 서버
- **S3**: 낙상 이벤트 영상 저장
- **SNS**: 실시간 알림 (이메일/SMS)
- **CloudWatch**: 로그 및 모니터링

## 🔗 SpringBoot 연동

```java
@RestController
@RequestMapping("/api/fall")
public class FallDetectionController {
    
    @PostMapping("/detect")
    public ResponseEntity<FallDetectionResponse> detectFall(
            @RequestParam("image") MultipartFile image) {
        
        // Python FastAPI 호출 (Port 8001)
        ResponseEntity<Map> response = restTemplate.postForEntity(
            "http://fastapi-server:8001/detect", 
            request, 
            Map.class
        );
        
        return ResponseEntity.ok(response);
    }
}
```

## 📚 사용 예제

### 단일 이미지 분석
```python
from M4 import M4FallDetectionAPI

api = M4FallDetectionAPI('best.pt')

with open('cctv_image.jpg', 'rb') as f:
    result = api.analyze_image_bytes(f.read())

if result['fall_detected']:
    print(f"⚠️ 낙상 감지!")
```

### 비디오 배치 처리
```python
import cv2
from M4 import FallDetector, YOLOPoseModel

model = YOLOPoseModel('best.pt')
detector = FallDetector(model)

cap = cv2.VideoCapture('video.mp4')

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    result = detector.detect_frame(frame)
    
    # 결과 처리
    print(f"상태: {result['status'].korean}")
```

## 🛠️ 개발 및 테스트

### 설치
```bash
cd C:\Users\user\M4
pip install -r requirements.txt
```

### 테스트
```python
from M4 import is_fallen
import numpy as np

# 테스트 키포인트 (쓰러진 자세)
keypoints = np.array([[0, 0]] * 17)
keypoints[5] = [100, 50]   # 왼쪽 어깨
keypoints[6] = [120, 50]   # 오른쪽 어깨
keypoints[11] = [100, 55]  # 왼쪽 엉덩이
keypoints[12] = [120, 55]  # 오른쪽 엉덩이

result = is_fallen(keypoints, frame_height=480)
print(f"낙상 여부: {result}")  # True
```

## 👥 개발자

TEAM LIKEYOU
