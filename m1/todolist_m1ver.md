# 🚀 M1 모듈 배포 및 시스템 통합 가이드

M1(도로 위험도 분석) 모듈의 역할 정의 및 배포 가이드입니다.

---

## 🏗️ 전체 시스템 구조도 (M2 Ver. 기준 + M1 추가)

```bash
/home/ubuntu/
├── springboot/           # [메인 백엔드] (Port 8080)
│   ├── (User API)      # 클라이언트 요청 처리
│   └── (DB Service)    # DB에서 특정 시간 데이터 조회 (READ)
│
├── main-api/            # [AI 허브 서버] (Port 8000)
│   ├── env: Python 3.10 (venv)
│   ├── modules:
│   │   ├── m5/          # 방문자 예측 모듈
│   │   ├── m2/          # 안심 경로 모듈
│   │   └── m1/          # 🆕 [M1 도로 위험도 모듈]
│   │       ├── main.py     # 모듈 진입점
│   │       ├── service.py  # 위험도 분석 및 DB 적재 로직 (WRITE)
│   │       ├── loader.py   # 데이터 로드 유틸
│   │       └── data/       # 분석용 원본 데이터 (CSV, GeoJSON)
│
└── p2pnet-api/          # [영상 분석 서버] (Port 8001)
```

---

## 🔄 역할 정의 (R&R)

| 컴포넌트 | 역할 | 주요 기능 |
| :--- | :--- | :--- |
| **FastAPI (M1)** | **모델 실행 및 결과 저장 (Write)** | - 초기 데이터 구축 및 주기적 모델 재실행<br>- 분석 결과를 DB (`COM_Location`)에 적재<br>- GeoJSON(좌표) 데이터 관리 |
| **Spring Boot** | **데이터 조회 및 서빙 (Read)** | - 프론트엔드 요청(`GET /risk?hour=18`) 수신<br>- DB에서 해당 시간대 위험도 데이터 조회<br>- 클라이언트에 JSON 응답 |
| **Supabase (DB)** | **데이터 저장소** | - `COM_Location` 테이블에 시간대별 도로 위험도 저장 |

---

## ✅ To-Do List (현재 진행 상황)

### 1. 📂 서버 배포 (FastAPI)
- [ ] **파일 업로드**: `package/m1` 폴더를 EC2 서버의 `main-api/modules/m1/` 경로로 업로드
    - **필수 파일**: `main.py`, `service.py`, `loader.py`, `data/` (CSV, GeoJSON)
    - **제외 파일**: `test/` 폴더 내 파일들은 운영 서버에 불필요하므로 제외 가능
- [ ] **라이브러리 설치**: `requirements.txt` 기반 패키지 설치 (`pandas`, `geopandas`, `supabase` 등)

### 2. 🗄️ 데이터 적재 (초기 구축)
- [x] **로컬 테스트 완료**: `test_m1_local.py`를 통해 데이터 정합성(GeoJSON vs DB) 검증 완료.
- [ ] **운영 DB 적재**: 서버 배포 후 `save_to_db.py` (또는 서비스 로직)을 1회 실행하여 전체 데이터 적재 필요.
    - *참고: M1 모듈은 서버 시작 시 자동 적재 로직이 비활성화되어 있으므로, 수동 실행 필요.*

### 3. 🤝 Spring Boot 개발자 전달 사항 (데이터 명세)
Spring Boot 개발자가 DB에서 데이터를 조회할 수 있도록 아래 정보를 전달해야 합니다.

*   **테이블명**: `COM_Location`
*   **주요 컬럼**:
    *   `hour` (int): 시간대 (0~23)
    *   `unique_road_id` (int): 도로 고유 ID
    *   `risk_score` (float): 위험도 점수 (0.0 ~ 1.0)
    *   `osmid` (text): OpenStreetMap ID (GeoJSON 매핑용 키)
*   **위험도 레벨 기준 (Backend Logic)**:
    *   `risk_score > 0.8`: **심각 (DarkRed #8B0000)**
    *   `0.6 <= risk_score <= 0.8`: **높음 (Red #E74C3C)**
    *   `0.4 <= risk_score < 0.6`: **중간 (Yellow #F1C40F)**
    *   `risk_score < 0.4`: **낮음 (Green #2ECC71)**
*   **좌표 데이터 이슈**:
    *   현재 FastAPI 구조는 **로컬 GeoJSON 파일**과 **DB 데이터**를 `osmid` 기준으로 병합(Merge)하여 반환합니다.
    *   Spring Boot가 데이터를 서빙하려면 **GeoJSON 파일을 Spring Boot 서버에도 배치**하고 병합 로직을 구현하거나, **DB에 Geometry 컬럼을 추가**하여 좌표까지 함께 저장해야 합니다. (후자 권장)

---

## 📝 유지보수 계획
- [ ] **데이터 갱신**: 축제/행사 데이터 변경 시 `csv` 파일 교체 후 재적재
- [ ] **모델 고도화**: 위험도 산출 로직 변경 시 `service.py` 수정 후 배포
