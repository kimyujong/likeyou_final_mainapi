from pydantic import BaseModel
from typing import List, Optional

class M5PredictionRequest(BaseModel):
    region_code: int
    target_date: str  # YYYYMMDD
    scenario: str = "realtime"  # 'realtime', 'sunny', 'rainy', 'cloudy'

# 일괄 요청을 위한 모델
class M5BatchPredictionRequest(BaseModel):
    target_date: str  # YYYYMMDD
    scenario: str = "realtime"

class HourlyPrediction(BaseModel):
    hour: int
    count: int
    capacity_limit: int = 5000  # 기본값
    is_over_capacity: bool

class WeatherSummary(BaseModel):
    condition: str
    avg_temp: Optional[float] = None
    total_rain: Optional[float] = None
    source: Optional[str] = None

class M5PredictionResponse(BaseModel):
    meta: dict
    weather: WeatherSummary
    data: List[HourlyPrediction]

class M5BatchResponse(BaseModel):
    status: str
    target_date: str
    scenario: str
    processed_count: int
    results: List[M5PredictionResponse]

# [추가] 실시간 날씨 응답 모델
class CurrentWeatherResponse(BaseModel):
    temp: float
    condition_text: str     # "맑음", "흐림" 등 텍스트
    condition_code: int     # 1, 3, 4 등 코드
    rain_amount: float
    humidity: Optional[float] = None # API에서 제공한다면
    base_time: str
