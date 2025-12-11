import sys
import os
import json
import pandas as pd
import geopandas as gpd
from dotenv import load_dotenv
from supabase import create_client

# 현재 디렉토리(.../package/m1/test)의 상위 상위 디렉토리(.../package)를 path에 추가
# 그래야 'import m1.loader'가 가능함
current_dir = os.path.dirname(os.path.abspath(__file__))
m1_dir = os.path.dirname(current_dir)      # .../package/m1
package_dir = os.path.dirname(m1_dir)      # .../package
sys.path.append(package_dir)

from m1.loader import get_road_geometry, load_data

def diagnose_data_mismatch():
    print("[Test] 데이터 정합성 진단 시작...\n")
    
    # 1. 로컬 GeoJSON 로드
    load_data()
    gdf = get_road_geometry()
    print(f"[GeoJSON] 데이터 (지도 형상): {len(gdf)}개")
    
    # 2. DB 데이터 로드 (18시 기준)
    load_dotenv()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("[Error] .env 설정 오류")
        return

    try:
        supabase = create_client(url, key)
        
        # Pagination으로 전체 데이터 가져오기
        all_data = []
        start = 0
        limit = 1000
        while True:
            response = supabase.table("COM_Location").select("*").eq("hour", 18).range(start, start + limit - 1).execute()
            data = response.data
            all_data.extend(data)
            if len(data) < limit:
                break
            start += limit
            
        db_data = all_data
        df = pd.DataFrame(db_data)
        print(f"[DB] 데이터 (18시 위험도): {len(df)}개")
    except Exception as e:
        print(f"[Error] DB 접속 실패: {e}")
        return

    # 3. osmid 전처리 및 매칭 테스트
    print("\n[Analysis] osmid 매칭 분석 중...")
    
    # DB osmid 전처리 (리스트/JSON -> 문자열)
    def parse_osmid(x):
        try:
            if isinstance(x, list) and len(x) > 0:
                return str(x[0])
            elif isinstance(x, str):
                # JSON 문자열 처리
                try:
                    val = json.loads(x)
                    if isinstance(val, list) and len(val) > 0:
                        return str(val[0])
                    return str(val)
                except:
                    return str(x)
            return str(x)
        except:
            return str(x)

    df['osmid_clean'] = df['osmid'].apply(parse_osmid)
    gdf['osmid_clean'] = gdf['osmid'].astype(str)

    # 집합(Set) 연산
    db_osmids = set(df['osmid_clean'])
    geo_osmids = set(gdf['osmid_clean'])
    
    common = db_osmids & geo_osmids
    missing_in_geo = db_osmids - geo_osmids
    missing_in_db = geo_osmids - db_osmids
    
    print(f"[Success] 매칭 성공 (지도에 표시됨): {len(common)}개 (osmid 기준)")
    print(f"[Warning] DB에는 있는데 지도(GeoJSON)에 없음 (누락): {len(missing_in_geo)}개")
    print(f"[Warning] 지도에는 있는데 DB에 없음 (점수 없음): {len(missing_in_db)}개")
    
    print("\n[Detail] 상세 분석:")
    if len(missing_in_geo) > 0:
        print(f"   -> 누락된 도로 예시 (DB O, Geo X): {list(missing_in_geo)[:5]}")
        print("   -> 원인: 'roads_cleaned_filtered.geojson' 파일에서 필터링되어 삭제된 도로일 수 있습니다.")
        
    if len(missing_in_db) > 0:
        print(f"   -> 점수 없는 도로 예시 (Geo O, DB X): {list(missing_in_db)[:5]}")
        print("   -> 원인: 위험도 분석 단계에서 제외된 도로일 수 있습니다.")

    # 4. 병합 시 뻥튀기 확인
    merged = gdf.merge(df, left_on='osmid_clean', right_on='osmid_clean', how='inner')
    print(f"\n[Result] 최종 병합된 행 개수 (화면에 그려지는 선 개수): {len(merged)}개")
    if len(merged) > len(common):
        print(f"   -> 1:N 매칭 발생! (하나의 osmid가 여러 조각으로 나뉘어짐)")
        print(f"   -> 배율: 약 {len(merged)/len(common):.1f}배")

if __name__ == "__main__":
    diagnose_data_mismatch()
