from pydantic import BaseModel
from typing import List, Optional, Any, Dict

class RoadRiskItem(BaseModel):
    unique_road_id: int
    name: Optional[str] = None
    risk_score: float
    risk_level: str
    geometry: Dict[str, Any]  # GeoJSON Geometry (type: LineString, coordinates: [...])

class RiskResponse(BaseModel):
    hour: int
    count: int
    data: List[RoadRiskItem]


