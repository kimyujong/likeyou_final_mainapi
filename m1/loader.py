import os
import geopandas as gpd
from supabase import create_client, Client
from dotenv import load_dotenv
from pathlib import Path

# 전역 변수로 데이터 캐싱
_road_geometry = None
_supabase_client = None

def load_data():
    global _road_geometry
    
    if _road_geometry is not None:
        return

    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")
    
    # 도로 지리 데이터 로드 (GeoJSON)
    # 1. 환경변수 확인
    env_path = os.getenv("M1_GEOJSON_PATH")
    if env_path and os.path.exists(env_path):
        geojson_path = env_path
        print(f"[M1] Loading GeoJSON from env: {geojson_path}")
    else:
        # 2. 기본 경로 (m1/data)
        geojson_path = os.path.join(data_dir, "roads_cleaned_filtered.geojson")
    
    if os.path.exists(geojson_path):
        _road_geometry = gpd.read_file(geojson_path)
        # osmid를 문자열로 통일
        if 'osmid' in _road_geometry.columns:
             _road_geometry['osmid'] = _road_geometry['osmid'].astype(str)
        
        # 좌표계 변환 (EPSG:4326)
        if _road_geometry.crs is not None and _road_geometry.crs.to_string() != "EPSG:4326":
            try:
                _road_geometry = _road_geometry.to_crs(epsg=4326)
                print("[M1] Geometry converted to EPSG:4326")
            except Exception as e:
                print(f"[M1] Warning: Failed to convert CRS: {e}")

        print(f"[M1] Geometry data loaded: {len(_road_geometry)} features")
    else:
        print(f"[M1] Error: Geometry data not found at {geojson_path}")

def get_supabase_client():
    global _supabase_client
    if _supabase_client is None:
        # 상위 폴더의 .env 로드
        env_path = Path("/home/ubuntu/main-api/.env")
        load_dotenv(dotenv_path=env_path)
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        
        if not url or not key:
            print("[M1] Error: SUPABASE_URL or SUPABASE_KEY not found in .env")
            return None
            
        try:
            _supabase_client = create_client(url, key)
            print("[M1] Supabase Client created")
        except Exception as e:
            print(f"[M1] Error creating Supabase client: {e}")
            return None
    return _supabase_client

def get_road_geometry():
    if _road_geometry is None:
        load_data()
    return _road_geometry


