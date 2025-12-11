import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class Config:
    GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

    # 테이블 이름 설정
    TABLE_CCTV = "cctv_data"  # Supabase 테이블 이름 (예시)
    TABLE_HEATMAP = "heatmap_data" # 필요한 경우
    TABLE_SECTION = "sections"

