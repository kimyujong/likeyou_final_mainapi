import pandas as pd
import numpy as np
import random
import datetime
from pathlib import Path
from .model_loader import load_m5_model

# 날씨 API 클래스 (실제 파일이 같은 패키지 내에 있다고 가정하거나 외부에서 주입)
from .weather_api import WeatherAPI 
# 여기서는 의존성을 줄이기 위해 외부에서 데이터를 받아오는 구조를 권장하지만,
# 편의상 직접 import 하지 않고 함수 인자로 받도록 설계함.

TARGET_COL = "방문인구"

class M5Predictor:
    def __init__(self, model_dir: str, weather_data_path: str):
        """
        Args:
            model_dir (str): saved_models 폴더 경로
            weather_data_path (str): total_weather.xlsx 파일 경로
        """
        self.model_dir = model_dir
        self.weather_history = pd.read_excel(weather_data_path)
        self.models = {} # Lazy Loading을 위한 캐시

    def get_model(self, region_code: int):
        if region_code not in self.models:
            print(f"[M5] 모델 로딩 중... Region: {region_code}")
            self.models[region_code] = load_m5_model(self.model_dir, region_code)
        return self.models[region_code]

    def _add_time_signal(self, df):
        df = df.copy()
        # 시간대(0~23)
        df['hour_sin'] = np.sin(2 * np.pi * df['시간대']/24)
        df['hour_cos'] = np.cos(2 * np.pi * df['시간대']/24)
        # 요일(0~6)
        df['weekday_sin'] = np.sin(2 * np.pi * df['weekday']/7)
        df['weekday_cos'] = np.cos(2 * np.pi * df['weekday']/7)
        # 월(1~12)
        df['month_sin'] = np.sin(2 * np.pi * df['month']/12)
        df['month_cos'] = np.cos(2 * np.pi * df['month']/12)
        # 일(1~366)
        df['day_sin'] = np.sin(2 * np.pi * df['dayofyear']/366)
        df['day_cos'] = np.cos(2 * np.pi * df['dayofyear']/366)
        return df

    def get_historical_scenario_weather(self, scenario_type: str, target_month: int):
        """
        과거 데이터(total_weather.xlsx)에서 시나리오에 맞는 날씨 패턴 추출
        """
        # 1. 대표 지역(민락동 등) 데이터만 필터링 (중복 제거)
        # 데이터에 행정동코드가 여러 개 섞여있다면 하나만 씁니다.
        sample_dong = self.weather_history['행정동코드'].iloc[0]
        df = self.weather_history[self.weather_history['행정동코드'] == sample_dong].copy()
        
        df['date_obj'] = pd.to_datetime(df['기준일자'], format='%Y%m%d')
        df['month'] = df['date_obj'].dt.month
        
        month_df = df[df['month'] == target_month]
        if month_df.empty:
            month_df = df # 없으면 전체 기간
            
        daily_stats = month_df.groupby('기준일자').agg({
            '강수량': 'sum',
            '하늘상태': 'mean',
            '기온': 'mean'
        })
        
        target_date = None
        
        if scenario_type == 'sunny':
            # 맑음: 강수량 0 & 하늘상태 맑음(1.5이하)
            candidates = daily_stats[(daily_stats['강수량'] == 0) & (daily_stats['하늘상태'] <= 1.5)]
            if candidates.empty:
                candidates = daily_stats[daily_stats['강수량'] == 0]
            if not candidates.empty:
                target_date = random.choice(candidates.index.tolist())
                
        elif scenario_type == 'rainy':
            # 비: 강수량 상위 3일
            rainy_days = daily_stats.sort_values('강수량', ascending=False).head(3)
            if not rainy_days.empty and rainy_days['강수량'].max() > 0:
                target_date = random.choice(rainy_days.index.tolist())
                
        elif scenario_type == 'cloudy':
            # 흐림: 강수량 적고 하늘상태 흐림
            candidates = daily_stats[(daily_stats['강수량'] < 5) & (daily_stats['하늘상태'] >= 3.0)]
            if not candidates.empty:
                target_date = random.choice(candidates.index.tolist())
            else:
                target_date = daily_stats['하늘상태'].idxmax()
                
        # 기본값: 랜덤
        if target_date is None:
            target_date = random.choice(daily_stats.index.tolist())
            
        # 해당 날짜의 24시간 데이터 추출
        result_df = month_df[month_df['기준일자'] == target_date].sort_values('시간대').copy()
        result_df = result_df.set_index('시간대')
        
        summary = {
            "date": str(target_date),
            "avg_temp": round(result_df['기온'].mean(), 1),
            "total_rain": round(result_df['강수량'].sum(), 1),
            "condition": scenario_type
        }
        
        return result_df[['기온', '강수량', '하늘상태', '강수형태']], summary

    def predict(self, region_code: int, target_date_str: str, scenario_type: str = 'realtime', weather_api_client=None):
        """
        메인 예측 함수
        """
        model_bundle = self.get_model(region_code)
        target_dt = pd.to_datetime(target_date_str, format='%Y%m%d')
        
        # 1. 날씨 데이터 준비
        weather_df = None
        weather_summary = {"condition": "unknown"}
        
        if scenario_type == 'realtime' and weather_api_client:
            # 실시간/예보 API 호출
            try:
                weather_df = weather_api_client.get_forecast(target_date_str, region_code)
                weather_summary = {
                    "condition": "realtime",
                    "source": "KMA API"
                }
            except Exception as e:
                print(f"API 호출 실패, 과거 데이터기반 '맑음'으로 대체: {e}")
                scenario_type = 'sunny' # Fallback
                
        if scenario_type != 'realtime':
            # 시나리오 기반 과거 데이터 로드
            weather_df, summary = self.get_historical_scenario_weather(scenario_type, target_dt.month)
            weather_summary = summary

        # 2. 예측 수행 (LSTM)
        predictions = self._run_lstm_forecast(
            model_bundle, 
            start_date=target_date_str, 
            weather_data=weather_df
        )
        
        # weather_df(시간대별 상세 날씨)도 함께 반환하여 DB 저장 시 사용
        return predictions, weather_summary, weather_df

    def _run_lstm_forecast(self, model_bundle, start_date, seq_len=24, horizon=24, weather_data=None):
        model = model_bundle['model']
        feature_scaler = model_bundle['feature_scaler']
        target_scaler = model_bundle['target_scaler']
        feature_cols = model_bundle['feature_cols']
        seed = model_bundle['seed_df'].copy()

        # 시드 데이터 준비
        seed = seed.sort_values(['기준일자', '시간대']).reset_index(drop=True)
        stored_seq_len = model_bundle.get('seq_len', len(seed))
        
        if len(seed) < stored_seq_len:
            stored_seq_len = len(seed)
        seed = seed.tail(stored_seq_len)
        seed_columns = seed.columns.tolist()

        # 스케일링
        seed_scaled = seed.copy()
        float_cols = feature_cols + [TARGET_COL]
        # 타입 변환
        for col in float_cols:
            if col in seed_scaled.columns:
                seed_scaled[col] = seed_scaled[col].astype(np.float32)
                
        feature_scaled_seed = feature_scaler.transform(seed[feature_cols]).astype(np.float32)
        target_scaled_seed = target_scaler.transform(seed[[TARGET_COL]]).astype(np.float32)
        
        seed_scaled.loc[:, feature_cols] = feature_scaled_seed
        seed_scaled.loc[:, TARGET_COL] = target_scaled_seed
        seed_scaled = seed_scaled[seed_columns]

        # LSTM 입력 시퀀스 생성
        seq = np.expand_dims(seed_scaled.to_numpy(dtype=np.float32), 0)
        
        # 날씨 백업 데이터
        col_idx = {col: idx for idx, col in enumerate(seed_columns)}
        weather_cols = [col for col in ['기온','강수량','하늘상태','강수형태'] if col in col_idx]
        
        predictions = []
        base_date = pd.to_datetime(str(start_date), format='%Y%m%d')
        last_actual_row = seed.tail(1).copy()
        region_code = seed['행정동코드'].iloc[-1]

        for step in range(horizon):
            # 예측
            yhat_scaled = model.predict(seq, verbose=0)[0][0]
            yhat = target_scaler.inverse_transform([[yhat_scaled]])[0][0]
            
            # 음수 방지
            yhat = max(0.0, float(yhat))
            predictions.append(yhat)

            # 다음 입력을 위한 업데이트
            target_dt = base_date + pd.Timedelta(hours=step)
            hour_val = int(target_dt.hour)

            next_actual = last_actual_row.copy()
            next_actual[TARGET_COL] = yhat
            next_actual['행정동코드'] = region_code
            next_actual['시간대'] = hour_val
            next_actual['기준일자'] = int(target_dt.strftime('%Y%m%d'))
            next_actual['year'] = target_dt.year
            next_actual['month'] = target_dt.month
            next_actual['day'] = target_dt.day
            next_actual['weekday'] = target_dt.weekday()
            next_actual['is_weekend'] = int(target_dt.weekday() >= 5)
            next_actual['dayofyear'] = target_dt.timetuple().tm_yday
            next_actual = self._add_time_signal(next_actual)

            # 날씨 채우기
            for col in weather_cols:
                if weather_data is not None and hour_val in weather_data.index:
                    next_actual[col] = weather_data.loc[hour_val, col]
                else:
                    # 데이터 없으면 직전 값 유지 or 0 (여기서는 직전 값)
                    next_actual[col] = last_actual_row[col].values[0]

            # 스케일링 후 시퀀스 업데이트
            next_scaled = next_actual.copy()
            for col in float_cols:
                if col in next_scaled.columns:
                    next_scaled[col] = next_scaled[col].astype(np.float32)

            feature_scaled = feature_scaler.transform(next_actual[feature_cols]).astype(np.float32)
            target_scaled = target_scaler.transform(next_actual[[TARGET_COL]]).astype(np.float32)

            next_scaled.loc[:, feature_cols] = feature_scaled
            next_scaled.loc[:, TARGET_COL] = target_scaled
            next_scaled = next_scaled[seed_columns]

            seq = np.roll(seq, -1, axis=1)
            seq[0, -1, :] = next_scaled.to_numpy(dtype=np.float32)[0]
            last_actual_row = next_actual

        return predictions

