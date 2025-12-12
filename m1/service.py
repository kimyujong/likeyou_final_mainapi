import pandas as pd
import geopandas as gpd
import json
from .loader import get_supabase_client, get_road_geometry

def get_risk_by_hour(hour: int):
    """
    특정 시간대의 도로 위험도 데이터(DB)와 좌표 정보(GeoJSON)를 결합하여 반환합니다.
    """
    # 1. DB에서 해당 시간대 데이터 조회
    supabase = get_supabase_client()
    if supabase is None:
        return []
    
    try:
        # Supabase select (Pagination)
        all_data = []
        start = 0
        limit = 1000
        
        while True:
            # range(start, end)는 inclusive (start ~ end 포함)
            response = supabase.table("COM_Location").select("*").eq("hour", hour).range(start, start + limit - 1).execute()
            data = response.data
            all_data.extend(data)
            
            # 가져온 데이터가 limit보다 적으면 더 이상 데이터가 없다는 뜻
            if len(data) < limit:
                break
            start += limit
            
        data = all_data
        
        if not data:
            return []
            
        df = pd.DataFrame(data)
            
        # 2. osmid 파싱 (DB에는 JSONB 또는 List로 저장됨)
        def parse_osmid(x):
            try:
                if isinstance(x, list) and len(x) > 0:
                    return str(x[0])
                elif isinstance(x, str):
                    # JSON 문자열인 경우
                    val = json.loads(x)
                    if isinstance(val, list) and len(val) > 0:
                        return str(val[0])
                    return str(val)
                return str(x)
            except:
                return str(x)

        df['osmid'] = df['osmid'].apply(parse_osmid)

    except Exception as e:
        print(f"[M1] DB Query Error: {e}")
        return []

    # 3. 좌표 데이터 가져오기
    gdf = get_road_geometry()
    if gdf is None:
        return []

    # 4. 데이터 병합
    merged_gdf = gdf[['osmid', 'geometry']].merge(df, on='osmid', how='inner')
    
    # 5. 결과 변환
    results = []
    
    for _, row in merged_gdf.iterrows():
        if row.geometry is None:
            continue
            
        risk_level = "중간"
        # risk_level 컬럼이 없으면 점수로 계산
        score = row['risk_score']
        
        if score > 0.8: risk_level = "심각" # 0.8 초과 -> 진한 빨강
        elif score >= 0.6: risk_level = "높음"
        elif score >= 0.4: risk_level = "중간"
        else: risk_level = "낮음"
            
        results.append({
            "unique_road_id": row['unique_road_id'],
            "name": row['name'] if pd.notna(row['name']) else None,
            "risk_score": row['risk_score'],
            "risk_level": risk_level,
            "geometry": row.geometry.__geo_interface__
        })
        
    return results


