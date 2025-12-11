import networkx as nx
import osmnx as ox
import math
import pandas as pd
from typing import List, Dict, Tuple
from .loader import DataLoader

class M2Service:
    def __init__(self):
        self.loader = DataLoader()
        self.heatmap_data = []
        self.density_grid = {}
        self.G = None
        
        # Lazy Loading은 실제 요청 시 또는 서버 시작 시 트리거 가능
        # 여기서는 초기화 시 로드 시도
        self.initialize()

    def initialize(self):
        print("[M2] Initializing Service...")
        
        # [수정] 항상 최신 CCTV 데이터를 DB에서 가져와 히트맵을 새로 생성하도록 변경
        # 기존: 파일 있으면 로드 -> 없으면 생성
        # 변경: 무조건 생성 시도 -> 실패하면 파일 로드
        
        print("[M2] Fetching latest data from DB to generate heatmap...")
        generated_data = self.generate_heatmap_with_idw()
        
        if generated_data:
            print("[M2] Heatmap updated with latest DB data.")
            self.heatmap_data = generated_data
        else:
            print("[M2] Failed to generate heatmap from DB (or empty). Trying local backup...")
            self.heatmap_data = self.loader.load_heatmap_csv()
            
        if not self.heatmap_data:
             print("[M2] Warning: No heatmap data available (neither DB nor local file).")

        # 2. Build Density Grid
        self.build_density_grid()
        
        # 3. Load Graph
        self.load_graph()

    def build_density_grid(self):
        """Builds O(1) density lookup grid"""
        self.density_grid = {}
        for point in self.heatmap_data:
            key = (round(point['lat'], 3), round(point['lon'], 3))
            current_max = self.density_grid.get(key, 0)
            if point['density'] > current_max:
                self.density_grid[key] = point['density']
        print(f"[M2] Density Grid ready with {len(self.density_grid)} cells.")

    def calculate_distance(self, lat1, lon1, lat2, lon2):
        R = 6371000 
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2) * math.sin(dlambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

    def generate_heatmap_with_idw(self) -> List[Dict]:
        print("[M2] Generating IDW Heatmap...")
        cctv_list = self.loader.load_cctv_data()
        if not cctv_list:
            return []

        whole_poly = self.loader.get_whole_poly()
        if not whole_poly:
            return []

        # Grid Configuration (Gwangalli Beach)
        center_lat = 35.1524
        center_lon = 129.1193
        hex_radius = 0.0003
        lon_scale = 1.216
        lat_step = 1.5 * hex_radius
        lon_step = math.sqrt(3) * hex_radius * lon_scale
        row_count = 80
        col_count = 80
        POWER = 2

        final_data = []

        for r in range(-row_count, row_count):
            for c in range(-col_count, col_count):
                offset_x = (lon_step / 2.0) if (r % 2 != 0) else 0.0
                lat = center_lat + (r * lat_step)
                lon = center_lon + (c * lon_step) + offset_x
                
                if not self.loader.is_inside(lon, lat, whole_poly):
                    continue

                numerator = 0.0
                denominator = 0.0
                interpolated_density = 0
                exact_match = False

                for cctv in cctv_list:
                    dist = self.calculate_distance(lat, lon, cctv['lat'], cctv['lon'])
                    if dist < 66: # 10 meters approx check? Logic kept from original
                        interpolated_density = cctv['density']
                        exact_match = True
                        break
                    
                    weight = 1.0 / (pow(dist, POWER) + 1e-6) 
                    numerator += weight * cctv['density']
                    denominator += weight
                
                if not exact_match:
                    interpolated_density = numerator / denominator if denominator > 0 else 0

                final_data.append({
                    "lat": round(lat, 7),
                    "lon": round(lon, 7),
                    "density": int(interpolated_density)
                })

        self.loader.save_heatmap_csv(final_data)
        return final_data

    def apply_density_weights(self):
        print("[M2] Applying density weights to graph...")
        for u, v, k, data in self.G.edges(keys=True, data=True):
            check_points = []
            node_u = self.G.nodes[u]
            node_v = self.G.nodes[v]
            
            if 'geometry' in data:
                coords = list(data['geometry'].coords)
                for lon, lat in coords:
                    check_points.append((lat, lon))
            else:
                check_points.append((node_u['y'], node_u['x']))
                check_points.append((node_v['y'], node_v['x']))
                mid_lat = (node_u['y'] + node_v['y']) / 2
                mid_lon = (node_u['x'] + node_v['x']) / 2
                check_points.append((mid_lat, mid_lon))
                
                if data.get('length', 0) > 50:
                    check_points.append((node_u['y']*0.75 + node_v['y']*0.25, node_u['x']*0.75 + node_v['x']*0.25))
                    check_points.append((node_u['y']*0.25 + node_v['y']*0.75, node_u['x']*0.25 + node_v['x']*0.75))

            base_weight = data.get('length', 1.0)
            max_density = 0
            
            # Check density using simplified grid lookup or full check
            # For performance, using grid lookup first could be better, but sticking to logic
            # Using raw heatmap data loop is slow, let's optimize using grid if possible?
            # Original code looped all heatmap points. Let's keep it robust but maybe optimize later.
            # Here we use the original logic for consistency.
            
            for lat, lon in check_points:
                # Optimization: Check grid first
                grid_key = (round(lat, 3), round(lon, 3))
                if grid_key in self.density_grid:
                    # If grid has value, it might be close. 
                    # But grid is just max value of cell.
                    # Let's adhere to original logic: check proximity to heatmap points
                    pass

                # Warning: Looping 2000+ heatmap points for every edge is SLOW.
                # But it's done once at startup.
                for point in self.heatmap_data:
                    if abs(point['lat'] - lat) > 0.001 or abs(point['lon'] - lon) > 0.001:
                        continue
                    dist = self.calculate_distance(lat, lon, point['lat'], point['lon'])
                    if dist < 40:
                        if point['density'] > max_density:
                            max_density = point['density']
                
                if max_density >= 80:
                    break
            
            penalty_factor = 1.0
            if max_density >= 80:
                penalty_factor = 10000.0
            elif max_density >= 50:
                penalty_factor = 1.3
            
            data['weight'] = base_weight * penalty_factor

    def load_graph(self):
        print("[M2] Loading OSM Graph...")
        try:
            # Gwangalli Beach Center
            self.G = ox.graph_from_point((35.1532, 129.1186), dist=3000, network_type='drive')
            if self.heatmap_data:
                self.apply_density_weights()
            else:
                for u, v, k, data in self.G.edges(keys=True, data=True):
                    data['weight'] = data.get('length', 1.0)
            print("[M2] Graph loaded successfully!")
        except Exception as e:
            print(f"[M2] Error loading graph: {e}")

    def find_shortest_path(self, origin_lat, origin_lng, dest_lat, dest_lng):
        if self.G is None:
            raise Exception("Graph not initialized")

        orig_node = ox.distance.nearest_nodes(self.G, origin_lng, origin_lat)
        dest_node = ox.distance.nearest_nodes(self.G, dest_lng, dest_lat)

        def improved_heuristic(u, v):
            u_node = self.G.nodes[u]
            v_node = self.G.nodes[v]
            dx = u_node['x'] - v_node['x']
            dy = u_node['y'] - v_node['y']
            dist = math.sqrt(dx**2 + dy**2)
            
            penalty_multiplier = 1.0
            for t in [0.3, 0.6]:
                sample_lat = u_node['y'] + dy * t
                sample_lon = u_node['x'] + dx * t
                key = (round(sample_lat, 3), round(sample_lon, 3))
                density = self.density_grid.get(key, 0)
                if density > 80:
                    penalty_multiplier += 5.0
                    break
                elif density > 40:
                    penalty_multiplier += 2.0
            
            return dist * penalty_multiplier * 100000

        path_nodes = nx.astar_path(self.G, orig_node, dest_node, heuristic=improved_heuristic, weight='weight')
        
        path_coords = []
        for node_id in path_nodes:
            node = self.G.nodes[node_id]
            path_coords.append({"lat": node['y'], "lng": node['x']})
            
        total_dist = 0
        for i in range(len(path_nodes)-1):
            u = path_nodes[i]
            v = path_nodes[i+1]
            edge_data = self.G.get_edge_data(u, v)
            min_w = float('inf')
            len_val = 0
            # MultiDiGraph may have multiple edges between nodes
            for key, data in edge_data.items():
                if data['weight'] < min_w:
                    min_w = data['weight']
                    len_val = data['length']
            total_dist += len_val

        # [추가] 도보 시간 계산 (평균 시속 4km/h = 분당 66.7m)
        walking_speed_m_per_min = 66.7
        duration_min = int(total_dist / walking_speed_m_per_min)
        if duration_min < 1:
            duration_min = 1

        return path_coords, total_dist, duration_min

    def get_cctv_list(self):
        return self.loader.load_cctv_data()

    def get_heatmap_list(self):
        return self.heatmap_data

