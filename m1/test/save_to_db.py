import os
import pandas as pd
from dotenv import load_dotenv
import json
from supabase import create_client, Client

def save_to_supabase():
    # 1. 환경 변수 로드
    load_dotenv()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("❌ Error: .env 파일에 SUPABASE_URL 또는 SUPABASE_KEY가 없습니다.")
        return

    # 2. Supabase 클라이언트 생성
    print(f"\n🚀 Supabase 연결 중... ({url})")
    try:
        supabase: Client = create_client(url, key)
    except Exception as e:
        print(f"❌ Supabase 연결 실패: {e}")
        return

    # 3. 데이터 개수 확인 (중복 저장 방지)
    try:
        response = supabase.table("COM_Location").select("count", count="exact").execute()
        count = response.count
        print(f"📊 현재 DB 데이터 개수: {count}개")
        
        if count > 0:
            print("✅ 이미 데이터가 존재하므로 저장을 건너뜁니다 (Pass).")
            return
    except Exception as e:
        print(f"⚠️ 테이블 조회 오류 (테이블이 없거나 권한 문제): {e}")

    # 4. 데이터 파일 로드
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(current_dir, "data", "road_risk_final.csv")
    
    if not os.path.exists(csv_path):
        print(f"❌ Error: 데이터 파일이 없습니다. ({csv_path})")
        return

    print("📂 CSV 데이터 로딩 중...")
    df = pd.read_csv(csv_path, dtype={'osmid': str})
    
    # 5. 데이터 전처리
    print("🔄 데이터 전처리 중...")
    
    def clean_osmid(x):
        if not isinstance(x, str):
            x = str(x)
        val = x.split('.')[0]
        # JSONB는 파이썬 리스트로 변환하면 API가 알아서 처리함
        return [val] 

    df['osmid'] = df['osmid'].apply(clean_osmid)
    
    # NaN 값 처리 (Supabase는 NaN을 못 받음 -> None으로 변환)
    df = df.where(pd.notnull(df), None)
    
    target_columns = ['unique_road_id', 'hour', 'osmid', 'name', 'dong', 'risk_score']
    df_final = df[target_columns].to_dict(orient='records') # 딕셔너리 리스트로 변환
    
    print(f"✅ 전처리 완료: {len(df_final)} rows")

    # 6. 데이터 업로드 (청크 단위)
    print("💾 데이터 저장 시작...")
    chunk_size = 1000 # API 방식은 한 번에 너무 많이 보내면 타임아웃 가능성 있음
    
    try:
        for i in range(0, len(df_final), chunk_size):
            chunk = df_final[i : i + chunk_size]
            supabase.table("COM_Location").insert(chunk).execute()
            print(f"   -> {i + len(chunk)} / {len(df_final)} 저장 완료")
            
        print("🎉 모든 데이터 저장 완료!")
        
    except Exception as e:
        print(f"❌ 데이터 저장 실패: {e}")

if __name__ == "__main__":
    save_to_supabase()
