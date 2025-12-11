# 📋 [Spring Boot 개발자용] 전체 AI 모듈(M1~M5) 연동 가이드 총정리

이 문서는 메인 백엔드(Spring Boot) 개발자가 5개의 AI 모듈(FastAPI)을 연동하고 활용하는 방법을 통합 정리한 가이드입니다.

---

## 1. 🚧 M1: 도로 위험도 분석 (Road Risk)
**방식**: **DB 직접 조회 (Read-Only) + 서버 병합 (Server-Side Merge)**

M1 모듈은 실시간 API 호출이 필요 없습니다. AI가 사전에 분석하여 DB에 적재해 둔 데이터를 **직접 조회**하여 사용합니다.

### ⚠️ 중요: 데이터 병합 방식 (변경됨)
DB(`COM_Location`)에는 위험도 점수만 저장되어 있고, 도로의 모양(좌표, geometry) 정보는 없습니다. 
따라서 **Spring Boot 서버에서 이 두 데이터를 병합하여 프론트엔드에 제공**해야 합니다.

### ✅ 역할 분담
- **AI 서버**: (사전 작업) 도로별 위험도 분석 후 `COM_Location` 테이블에 데이터 적재 완료.
- **Spring Boot**: 
  - `roads_cleaned_filtered.geojson` 파일을 서버 시작 시 메모리(Map)에 로드.
  - 사용자 요청 시 DB에서 위험도 데이터(`risk_score`) 조회.
  - 메모리의 좌표 정보와 DB 데이터를 병합(Merge)하여 최종 JSON 반환.
- **프론트엔드**:
  - 반환된 JSON을 받아 지도에 바로 표출 (별도 병합 로직 불필요).

### 💾 DB 테이블 정보
- **테이블명**: `COM_Location`
- **주요 컬럼**:
  - `hour` (INT): 시간대 (0~23)
  - `risk_score` (FLOAT): 위험도 점수 (0.0 ~ 1.0)
  - `osmid` (TEXT): 도로 ID (OpenStreetMap ID) - **매핑 키(Key)**
  - `name`: 도로명

### 🚀 사용 시나리오 (예시)
1. 사용자: "지금(18시) 도로 위험도 보여줘"
2. **Spring Boot**: 
   - DB 조회: `SELECT * FROM "COM_Location" WHERE hour = 18;`
   - Java 로직: `List<Result> results = new ArrayList<>();`
     ```java
     for (RiskData data : dbList) {
         Geometry geom = geometryMap.get(data.getOsmid()); // 메모리에서 좌표 찾기
         results.add(new Result(data, geom));
     }
     ```
   - 최종 JSON 반환.
3. **프론트엔드**: 지도에 선 그리기 (빨강/노랑/초록)

---

## 2. 🛡️ M2: 안심 경로 탐색 (Safe Route)
**방식**: **실시간 API 호출 (Request/Response)**

M2 모듈은 사용자의 출발/도착지를 받아 실시간으로 CCTV 밀집도와 위험 요소를 피해가는 경로를 계산합니다.

### ✅ 역할 분담
- **Spring Boot**: 사용자로부터 출발/도착지를 받아 AI 서버(**8002 포트**)에 요청.
- **AI 서버**: 최신 CCTV 데이터를 반영하여 최적 경로 계산 후 JSON 반환.
- **참고**: 이전에는 실시간 분석 중인 CCTV만 반영되었으나, 현재는 **하이브리드 로딩** 방식을 적용하여 분석되지 않는 구역(Dummy/Default)까지 포함한 **82개 전체 구역**에 대해 안전 경로를 계산합니다.

### 📡 API 규격
- **URL**: `POST http://localhost:8002/m2/route`
- **Content-Type**: `application/json`

#### **Request Body**
```json
{
  "origin": {
    "lat": 35.1532,
    "lng": 129.1186
  },
  "destination": {
    "lat": 35.1550,
    "lng": 129.1230
  }
}
```

#### **Response Body**
```json
{
  "success": true,
  "path": [
    {"lat": 35.1532, "lng": 129.1186},
    {"lat": 35.1533, "lng": 129.1187},
    ...
  ],
  "info": {
    "distance": 450.5,       // 거리 (m)
    "duration_min": 6        // 시간 (분)
  }
}
```

---

## 3. 👥 M3: 실시간 인구 혼잡도 분석 (Crowd Density)
**방식**: **제어 API 호출 (Start/Stop) + DB 조회 (Monitoring)**

M3 모듈은 Spring Boot의 요청에 따라 분석을 시작/중지합니다. 분석이 시작되면 실시간으로 DB에 로그를 쌓습니다.

### ✅ 역할 분담
- **Spring Boot**: 로그인/대시보드 진입 시 `/control/start` 호출, 종료 시 `/control/stop` 호출.
- **AI 서버**: 요청 시 CCTV 영상을 분석하며 `DAT_Crowd_Detection` 테이블에 실시간 `INSERT`.

**⚠️ 참고 (Auto-Dummy Mode)**:
M3 서버는 실행과 동시에 **백그라운드에서 시뮬레이션(Dummy) 모드**가 동작합니다.
- `/control/start`로 분석 중인 CCTV: **실제 분석 데이터** 저장
- 분석 중이지 않은 나머지 CCTV: **가상(Dummy) 데이터** 자동 저장
- 따라서 대시보드에서는 항상 82개 모든 CCTV의 데이터가 실시간으로 들어오는 것처럼 보입니다.

### 📡 제어 API (Control)
**1. 분석 시작**
- **URL**: `POST http://localhost:8003/control/start?cctv_no=CCTV-01`
- **Response**: `{"status": "started", ...}`

**2. 분석 중지**
- **URL**: `POST http://localhost:8003/control/stop?cctv_no=CCTV-01`
- **Response**: `{"status": "stopped", ...}`

### 💾 DB 테이블 정보
- **테이블명**: `DAT_Crowd_Detection`
- **주요 컬럼**:
  - `cctv_no` (UUID): CCTV 식별자
  - `person_count` (INT): 감지된 인원 수
  - `congestion_level` (INT): 혼잡도 (%)
  - `risk_level` (INT): 위험 등급 (1:안전 ~ 4:위험)
  - `detected_at` (TIMESTAMP): 감지 시간
  - `status` (TEXT): 상태 (기본값: 'NEW')
  - `cleared_by` (TEXT): 조치자 (초기값: NULL)

---

## 4. 🚨 M4: 낙상 감지 시스템 (Fall Detection)
**방식**: **제어 API 호출 (Start/Stop) + DB 조회 (Event Log)**

M4 모듈도 M3와 동일하게 Spring Boot의 제어를 받아 동작합니다.

### ✅ 역할 분담
- **Spring Boot**: 필요 시 `/control/start` 호출로 감시 시작.
- **AI 서버**: 낙상 감지 시 `DAT_Fall_Event` 테이블에 이벤트 기록.

### 📡 제어 API (Control)
**1. 감시 시작**
- **URL**: `POST http://localhost:8004/control/start?cctv_no=CCTV-01`
- **Response**: `{"status": "started", ...}`

**2. 감시 중지**
- **URL**: `POST http://localhost:8004/control/stop?cctv_no=CCTV-01`
- **Response**: `{"status": "stopped", ...}`

### 💾 DB 테이블 정보
- **테이블명**: `DAT_Fall_Event`
- **주요 컬럼**:
  - `cctv_no` (UUID): 감지된 CCTV
  - `timestamp` (TIMESTAMP): 발생 시간
  - `status` (TEXT): 처리 상태 ('NEW', 'CHECKED' 등)

---

## 5. 🔮 M5: 사고 위험 예측 (Accident Prediction)
**방식**: **API 실행(Trigger) + DB 조회(Read)**

미래의 사고 위험도를 예측합니다.

### ✅ 역할 분담
- **Spring Boot**: 
  1. 관리자가 "내일 예측해줘" 버튼을 누르거나 날씨 아이콘(맑음/우천 등)을 변경하면 API 호출 (Trigger).
     - 예측 날짜는 **20251115**로 고정하여 요청.
     - 맑음 → 우천 클릭 시 `scenario`를 `"rainy"`로 설정.
  2. 대시보드에서는 DB에 저장된 예측 결과를 조회 (Read)하여 표출.

### 📡 1. 예측 실행 (Trigger)
- **URL**: `POST http://localhost:8005/m5/predict`
- **Request Body**:
```json
{
  "region_code": 26500800,  // 행정동 코드
  "target_date": "20251115", // 예측할 날짜 (고정)
  "scenario": "rainy"        // 시나리오 (realtime, sunny, rainy, cloudy)
}
```

### 💾 2. 결과 조회 (DB Read)
- **테이블명**: `DAT_Population_Prediction`
- **Spring Boot**: `SELECT * FROM "DAT_Population_Prediction" WHERE base_date = '2025-11-15' AND scenario_type = 'rainy';`

---

## 📝 포트 번호 요약 (로컬 기준)
| 모듈 | 포트 | 주요 기능 |
| :--- | :--- | :--- |
| **M1** | 8001 | (API 없음, DB만 사용) |
| **M2** | 8002 | `POST /m2/route` |
| **M3** | 8003 | `POST /control/start` |
| **M4** | 8004 | `POST /control/start` |
| **M5** | 8005 | `POST /m5/predict` |
