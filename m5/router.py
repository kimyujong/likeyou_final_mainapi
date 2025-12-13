from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime
from .schemas import (
    M5PredictionRequest, M5PredictionResponse, 
    M5BatchPredictionRequest, M5BatchResponse,
    HourlyPrediction, WeatherSummary,
    CurrentWeatherResponse
)
from .predictor import M5Predictor
from .database import save_prediction_log
from .weather_api import WeatherAPI
import os

router = APIRouter(
    prefix="/m5",
    tags=["m5-population-prediction"]
)

M5_MODEL_DIR = os.environ.get("M5_MODEL_DIR", "./saved_models")
M5_WEATHER_DATA = os.environ.get("M5_WEATHER_DATA", "./total_weather.xlsx")

TARGET_REGIONS = [
    26500800, 26500770, 26500660, 26500670, 26350525
]

predictor = None
weather_api_client = None

def get_predictor():
    global predictor
    if predictor is None:
        predictor = M5Predictor(M5_MODEL_DIR=M5_MODEL_DIR, M5_WEATHER_DATA=M5_WEATHER_DATA)
    return predictor

def get_weather_api():
    global weather_api_client
    if weather_api_client is None:
        weather_api_client = WeatherAPI() 
    return weather_api_client

@router.post("/predict", response_model=M5PredictionResponse)
async def predict_population(req: M5PredictionRequest):
    """
    [단일] 특정 날짜와 지역의 방문자 수를 예측합니다.
    """
    m5 = get_predictor()
    api_client = get_weather_api() if req.scenario == 'realtime' else None
    
    try:
        # [수정] weather_df 추가 반환 받음
        predictions, weather_summary, weather_df = m5.predict(
            region_code=req.region_code,
            target_date_str=req.target_date,
            scenario_type=req.scenario,
            weather_api_client=api_client
        )
        
        hourly_data = []
        for hour, count in enumerate(predictions):
            hourly_data.append(HourlyPrediction(
                hour=hour,
                count=int(count),
                is_over_capacity=(count > 5000)
            ))
            
            # [수정] 시간대별 상세 날씨 추출
            weather_info = {}
            if weather_df is not None and hour in weather_df.index:
                weather_info = weather_df.loc[hour].to_dict()
            
            # DB 저장
            save_prediction_log(
                region_code=str(req.region_code),
                target_date=req.target_date,
                target_hour=hour,
                predicted_count=int(count),
                weather_info=weather_info,  # 상세 정보 전달
                scenario_type=req.scenario
            )

        return M5PredictionResponse(
            meta={
                "region": str(req.region_code),
                "date": req.target_date,
                "scenario": req.scenario
            },
            weather=WeatherSummary(**weather_summary),
            data=hourly_data
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/predict/all", response_model=M5BatchResponse)
async def predict_all_regions(req: M5BatchPredictionRequest):
    """
    [일괄] 관리 대상 모든 지역(5곳)에 대해 예측을 수행하고 DB에 저장합니다.
    """
    m5 = get_predictor()
    api_client = get_weather_api() if req.scenario == 'realtime' else None
    
    results = []
    
    try:
        for region_code in TARGET_REGIONS:
            # [수정] weather_df 추가 반환 받음
            predictions, weather_summary, weather_df = m5.predict(
                region_code=region_code,
                target_date_str=req.target_date,
                scenario_type=req.scenario,
                weather_api_client=api_client
            )
            
            hourly_data = []
            for hour, count in enumerate(predictions):
                hourly_data.append(HourlyPrediction(
                    hour=hour,
                    count=int(count),
                    is_over_capacity=(count > 5000)
                ))
                
                # [수정] 시간대별 상세 날씨 추출
                weather_info = {}
                if weather_df is not None and hour in weather_df.index:
                    weather_info = weather_df.loc[hour].to_dict()
                
                save_prediction_log(
                    region_code=str(region_code),
                    target_date=req.target_date,
                    target_hour=hour,
                    predicted_count=int(count),
                    weather_info=weather_info, # 상세 정보 전달
                    scenario_type=req.scenario
                )
            
            results.append(M5PredictionResponse(
                meta={
                    "region": str(region_code),
                    "date": req.target_date,
                    "scenario": req.scenario
                },
                weather=WeatherSummary(**weather_summary),
                data=hourly_data
            ))
            
        return M5BatchResponse(
            status="success",
            target_date=req.target_date,
            scenario=req.scenario,
            processed_count=len(results),
            results=results
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Batch processing failed: {str(e)}")

@router.get("/weather/current", response_model=CurrentWeatherResponse)
async def get_current_weather(region_code: int = 26500800):
    """
    [실시간] 대시보드 우측 상단 표시용 현재 날씨 조회
    """
    api = get_weather_api()
    now = datetime.now()
    today_str = now.strftime("%Y%m%d")
    current_hour = now.hour
    
    try:
        df = api.get_forecast(today_str, region_code)
        
        if current_hour in df.index:
            row = df.loc[current_hour]
        else:
            row = df.iloc[-1]
            
        sky_code = int(row['하늘상태'])
        pty_code = int(row['강수형태'])
        
        condition_text = "맑음"
        if pty_code > 0:
            condition_map = {1:"비", 2:"비/눈", 3:"눈", 5:"빗방울"}
            condition_text = condition_map.get(pty_code, "우천")
        elif sky_code >= 4:
            condition_text = "흐림"
        elif sky_code >= 3:
            condition_text = "구름많음"
            
        return CurrentWeatherResponse(
            temp=float(row['기온']),
            condition_text=condition_text,
            condition_code=sky_code,
            rain_amount=float(row['강수량']),
            base_time=f"{today_str} {current_hour}:00"
        )
        
    except Exception as e:
        print(f"[Weather API Error] {e}")
        return CurrentWeatherResponse(
            temp=20.0,
            condition_text="정보없음",
            condition_code=1,
            rain_amount=0.0,
            base_time=f"{today_str} {current_hour}:00 (Backup)"
        )
