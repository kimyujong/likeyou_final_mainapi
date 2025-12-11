# 🌊 M5: 방문자 수 예측 및 실시간 날씨 모듈

부산 불꽃축제 등 주요 행사 시 **방문자 수를 예측(LSTM)**하고, 대시보드에 **실시간 날씨 정보**를 제공하는 API 모듈입니다.

## 📌 주요 기능

1.  **방문자 수 예측 (`/predict`)**
    *   특정 날짜와 지역의 시간대별(0~23시) 방문자 수를 예측합니다.
    *   **시나리오 시뮬레이션**: '맑음', '비', '흐림' 등 날씨 조건에 따른 인파 변화를 예측할 수 있습니다.
2.  **일괄 예측 (`/predict/all`)**
    *   관리 대상 5개 지역(민락동, 광안2동, 남천1/2동, 우3동)의 예측을 한 번에 수행하고 DB에 저장합니다.
3.  **실시간 날씨 (`/weather/current`)**
    *   기상청 API를 연동하여 현재 시간의 기온, 강수량, 날씨 상태를 반환합니다.

## ⚙️ 설치 및 설정

### 1. 환경 변수 (`.env`)
프로젝트 루트의 `.env` 파일에 다음 설정이 필요합니다.
```ini
# Supabase DB 설정
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key

# M5 모듈 설정 (선택 사항, 기본값 있음)
M5_MODEL_DIR=./saved_models        # 모델 파일(.pkl, .keras) 위치
M5_WEATHER_DATA=./total_weather.xlsx # 시나리오용 과거 날씨 데이터
```

### 2. 패키지 설치
```bash
pip install -r requirements.txt
```

### 3. 모델 파일 준비
`saved_models/` 폴더에 학습된 모델 파일들(`final_model_xxxxx_bundle.pkl` 및 `.keras`)이 있어야 합니다.

## 🚀 API 사용법

### 1. 방문자 수 예측 (단일)
*   **URL**: `POST /m5/predict`
*   **Body**:
    ```json
    {
      "region_code": 26500800,
      "target_date": "20251115",
      "scenario": "rainy"  // "realtime", "sunny", "rainy", "cloudy"
    }
    ```

### 2. 일괄 예측 (전체 지역)
*   **URL**: `POST /m5/predict/all`
*   **Body**:
    ```json
    {
      "target_date": "20251115",
      "scenario": "realtime"
    }
    ```

### 3. 실시간 날씨 조회
*   **URL**: `GET /m5/weather/current?region_code=26500800`
*   **Response**:
    ```json
    {
      "temp": 21.5,
      "condition_text": "맑음",
      "condition_code": 1,
      "rain_amount": 0.0,
      "base_time": "20251115 14:00"
    }
    ```

## 📂 폴더 구조
```
m5/
├── predictor.py    # LSTM 예측 로직 및 시나리오 처리
├── model_loader.py # .pkl 및 .keras 모델 로딩 유틸
├── router.py       # FastAPI 라우터 (엔드포인트 정의)
├── schemas.py      # Pydantic 데이터 모델
├── database.py     # Supabase DB 저장 로직
├── weather_api.py  # 기상청 API 연동 클라이언트
└── requirements.txt
```

