import os
import json
import pandas as pd
from typing import List, Dict, Optional
from .config import Config

# Supabase Client (Try import)
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("[M2] Warning: 'supabase' library not installed. Using local files only.")

class DataLoader:
    def __init__(self, base_dir: str = None):
        if base_dir is None:
            base_dir = os.path.join(os.path.dirname(__file__), "data")
        self.base_dir = base_dir
        self.csv_path = os.path.join(self.base_dir, "cctv_data.csv")
        self.section_dir = os.path.join(self.base_dir, "section")
        self.whole_section_path = os.path.join(self.section_dir, "whole_section.json")
        
        # Initialize Supabase
        self.supabase: Optional[Client] = None
        if SUPABASE_AVAILABLE and Config.SUPABASE_URL and Config.SUPABASE_KEY:
            try:
                self.supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
                print("[M2] Supabase client initialized.")
            except Exception as e:
                print(f"[M2] Failed to init Supabase: {e}")

    def is_inside(self, lon, lat, poly):
        """Ray Casting Algorithm for Point in Polygon"""
        n = len(poly)
        inside = False
        p1x, p1y = poly[0]
        for i in range(n + 1):
            p2x, p2y = poly[i % n]
            if lat > min(p1y, p2y):
                if lat <= max(p1y, p2y):
                    if lon <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (lat - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or lon <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        return inside

    def get_whole_poly(self):
        try:
            with open(self.whole_section_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("coordinates", [])
        except:
            return []

    def load_cctv_data(self) -> List[Dict]:
        """
        Loads CCTV data. 
        Strategy: 
        1. Fetch ALL CCTVs from COM_CCTV (Base data: ID, Lat, Lon)
        2. Fetch LATEST density from DAT_Crowd_Detection (Live data)
        3. Merge: Update density for active CCTVs, keep 0 for others.
        """
        cctv_list = []
        whole_poly = self.get_whole_poly()

        # 1. Try Supabase (Hybrid Load)
        if self.supabase:
            try:
                print("[M2] Fetching ALL CCTV base info from COM_CCTV...")
                # 1. Fetch Base Data (COM_CCTV)
                base_response = self.supabase.table("COM_CCTV") \
                    .select("cctv_no, latitude, longitude") \
                    .execute()
                
                base_data = base_response.data
                if not base_data:
                    print("[M2] COM_CCTV is empty. Falling back to CSV.")
                    raise Exception("COM_CCTV table empty")

                # Map: cctv_no -> {lat, lon, density=0}
                cctv_map = {}
                for item in base_data:
                    cctv_no = item.get('cctv_no')
                    lat = float(item.get('latitude', 0))
                    lon = float(item.get('longitude', 0))
                    
                    if not whole_poly or self.is_inside(lon, lat, whole_poly):
                        cctv_map[cctv_no] = {
                            "cctv_no": cctv_no,
                            "lat": lat,
                            "lon": lon,
                            "density": 0 # Default safe
                        }
                
                print(f"[M2] Loaded {len(cctv_map)} base CCTVs from DB.")

                # 2. Fetch Live Data (DAT_Crowd_Detection)
                # Fetch recent records (e.g., last 1000 records to ensure we catch active ones)
                # Ideally, we want DISTINCT ON (cctv_no) but Supabase-js client is limited.
                # We will fetch recent data and process in Python.
                print("[M2] Fetching latest crowd density from DAT_Crowd_Detection...")
                live_response = self.supabase.table("DAT_Crowd_Detection") \
                    .select("cctv_no, congestion_level, detected_at") \
                    .order("detected_at", desc=True) \
                    .limit(200) \
                    .execute()
                
                live_data = live_response.data
                processed_ids = set()
                
                if live_data:
                    for item in live_data:
                        cctv_no = item.get('cctv_no')
                        # Only update if it's the first time seeing this ID (since we ordered by desc)
                        # and if the ID exists in our base map
                        if cctv_no in cctv_map and cctv_no not in processed_ids:
                            density = int(item.get('congestion_level', 0))
                            cctv_map[cctv_no]['density'] = density
                            processed_ids.add(cctv_no)
                    
                    print(f"[M2] Updated density for {len(processed_ids)} active CCTVs.")
                
                # Convert map back to list
                cctv_list = list(cctv_map.values())
                return cctv_list

            except Exception as e:
                print(f"[M2] Supabase fetch error: {e}. Falling back to CSV.")

        # 2. Fallback to CSV (Legacy Mode)
        if os.path.exists(self.csv_path):
            try:
                try:
                    df = pd.read_csv(self.csv_path, encoding='utf-8-sig')
                except UnicodeDecodeError:
                    df = pd.read_csv(self.csv_path, encoding='cp949')
                
                column_mapping = {
                    "경도": "lon", "위도": "lat", "밀집도": "density",
                    "Lon": "lon", "Lat": "lat", "Density": "density"
                }
                df.rename(columns=column_mapping, inplace=True)
                
                required_cols = ["lon", "lat", "density"]
                if not all(col in df.columns for col in required_cols):
                    return []

                for _, row in df.iterrows():
                    try:
                        lon = float(row['lon'])
                        lat = float(row['lat'])
                        density = int(row['density'])
                        
                        if not whole_poly or self.is_inside(lon, lat, whole_poly):
                            cctv_no = row.get('cctv_no')
                            if pd.isna(cctv_no):
                                cctv_no = str(len(cctv_list) + 1) # Convert to str for consistency
                            else:
                                cctv_no = str(row.get('cctv_no'))
                                
                            cctv_list.append({
                                "cctv_no": cctv_no,
                                "lat": lat,
                                "lon": lon,
                                "density": density
                            })
                    except ValueError:
                        continue
                print(f"[M2] Loaded {len(cctv_list)} CCTV points from CSV.")
            except Exception as e:
                print(f"[M2] Error reading CSV: {e}")
            
        return cctv_list

    def load_heatmap_csv(self) -> List[Dict]:
        """Loads pre-generated heatmap data if exists"""
        heatmap_path = os.path.join(self.base_dir, "heatmap.csv")
        if os.path.exists(heatmap_path):
            try:
                df = pd.read_csv(heatmap_path)
                return df.to_dict(orient="records")
            except Exception as e:
                print(f"[M2] Error loading heatmap.csv: {e}")
        return []

    def save_heatmap_csv(self, data: List[Dict]):
        """Saves generated heatmap data"""
        try:
            df = pd.DataFrame(data)
            heatmap_path = os.path.join(self.base_dir, "heatmap.csv")
            df.to_csv(heatmap_path, index=False)
        except Exception as e:
            print(f"[M2] Error saving heatmap.csv: {e}")
