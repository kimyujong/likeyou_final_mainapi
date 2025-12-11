import os
from supabase import create_client, Client
from datetime import datetime

# Supabase 클라이언트는 싱글톤으로 관리하거나, 요청마다 생성할 수 있습니다.
# 여기서는 모듈 레벨에서 초기화 시도

def get_supabase_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        print("[Warning] SUPABASE_URL or SUPABASE_KEY not set. DB logging disabled.")
        return None
    return create_client(url, key)

def save_prediction_log(
    region_code: str,
    target_date: str, # YYYYMMDD
    target_hour: int,
    predicted_count: int,
    weather_info: dict,
    scenario_type: str = 'realtime'
):
    """
    예측 결과를 'DAT_Population_Prediction' 테이블에 저장
    """
    supabase = get_supabase_client()
    if not supabase:
        return

    # 날짜 포맷 변환 YYYYMMDD -> YYYY-MM-DD
    try:
        dt = datetime.strptime(target_date, "%Y%m%d")
        formatted_date = dt.strftime("%Y-%m-%d")
    except ValueError:
        formatted_date = target_date

    # 날씨 코드 -> 텍스트 매핑 (단순화)
    sky_map = {1: "Sunny", 2:"Little cloudy",3: "Normal cloudy", 4: "Very cloudy"}
    # 모델에서 넘어오는 하늘상태는 실수(float)일 수 있으므로 반올림
    sky_val = int(round(weather_info.get('하늘상태', 1)))
    weather_cat = sky_map.get(sky_val, "Unknown")
    
    pty_val = int(round(weather_info.get('강수형태', 0)))
    pty_map = {0: "None", 1: "Rain", 2: "Sleet", 3: "Snow"}
    precip_type = pty_map.get(pty_val, "None")

    data = {
        "region_id": str(region_code),
        # DB 컬럼명에 맞춰 수정 (target_date -> base_date, target_hour -> hour_slot)
        "base_date": formatted_date,
        "hour_slot": target_hour,
        
        "scenario_type": scenario_type,
        "predicted_population": int(predicted_count),
        
        # 메타 데이터
        "temperature": float(weather_info.get('기온', 0)),
        "precipitation": float(weather_info.get('강수량', 0)),
        "weather_cat": weather_cat,
        "precipitation_type": precip_type,
        
        # target_time (TIMESTAMPTZ) 필수 컬럼 생성
        # KST(+09:00) 가정
        "target_time": f"{formatted_date}T{target_hour:02d}:00:00+09:00",
        
        # datetime_id는 YYYYMMDDHH 형식으로 생성 (기존 스키마 호환용)
        "datetime_id": f"{target_date}{target_hour:02d}"
    }

    try:
        # upsert=True를 쓰거나, 충돌 시 무시하려면 on_conflict 옵션 사용
        # 여기서는 단순 insert
        supabase.table("DAT_Population_Prediction").insert(data).execute()
    except Exception as e:
        print(f"[DB Error] Failed to save log: {e}")
