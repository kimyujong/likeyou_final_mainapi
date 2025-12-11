import sys
import os
import json
from dotenv import load_dotenv
from supabase import create_client

# 현재 디렉토리를 path에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_db_duplicate():
    load_dotenv()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    supabase = create_client(url, key)
    
    print("🔍 DB 데이터 중복 확인 중...")
    
    # 18시 데이터 개수 조회
    response = supabase.table("COM_Location").select("count", count="exact").eq("hour", 18).execute()
    count_18h = response.count
    
    print(f"📊 18시 데이터 총 개수: {count_18h}개")
    print(f"   (정상 범위: 약 1,791개)")
    
    if count_18h > 2000:
        print("⚠️ 데이터가 중복 저장된 것으로 보입니다!")
        print("   -> 해결책: DB 테이블을 비우고 다시 한 번만 저장해야 합니다.")
    else:
        print("✅ DB 데이터 개수는 정상입니다. (Merge 로직 문제일 가능성)")

if __name__ == "__main__":
    check_db_duplicate()

