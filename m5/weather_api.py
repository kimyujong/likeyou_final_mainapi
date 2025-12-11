import requests
import pandas as pd
import datetime
import numpy as np


import os

# 환경변수에서 키 로드 (없으면 기본값 사용하거나 에러 처리)
SERVICE_KEY = os.environ.get("WEATHER_API_KEY", "LV9VqydlVHSgjsUjQBB6HzhTyR6Z4XkSzqIfmQzuZaigTc8H5u2iPf7kpxA79doaQq16dxnNCknCZFIxJLftwQ==")

class WeatherAPI:
    def __init__(self, service_key=None):
        # 생성자에서 키를 주입받지 않으면 전역 변수(환경변수 값) 사용
        self.service_key = service_key or SERVICE_KEY
        # 기상청 단기예보 URL
        self.url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
        
        # 행정동별 격자 좌표 매핑 (부산 주요 지역)
        # 출처: 기상청 격자변환 엑셀 파일
        self.location_map = {
            26500800: {'nx': 99, 'ny': 75},  # 민락동
            26500770: {'nx': 99, 'ny': 75},  # 광안2동
            26500660: {'nx': 98, 'ny': 75},  # 남천1동
            26500670: {'nx': 99, 'ny': 75},  # 남천2동
            26350525: {'nx': 99, 'ny': 76}   # 우제3동
        }

    def get_forecast(self, target_date, region_code):
        """
        특정 날짜, 지역의 24시간 예보 데이터를 가져옵니다.
        
        Args:
            target_date (str): 'YYYYMMDD' (예: '20251115')
            region_code (int): 행정동 코드 (예: 26500800)
            
        Returns:
            pd.DataFrame: 시간대별(0~23) 기상 데이터
        """
        # API 키가 없으면 가짜 데이터(Mock) 반환 (테스트용)
        if not self.service_key:
            print(f"⚠️ [Mock Mode] API 키가 없어 가상 예보 데이터를 생성합니다. ({target_date}, {region_code})")
            return self._generate_mock_data(target_date)

        # 1. 요청 파라미터 설정
        # [수정] 0시부터 전체 데이터를 얻기 위해, '전날 23시' 발표 데이터를 요청합니다.
        # 단기예보는 3시간 단위 발표(02,05,08...)지만, 전날 23시는 모든 시간을 포함하는 안전한 기준입니다.
        
        # 타겟 날짜의 전날 구하기
        target_dt = datetime.datetime.strptime(target_date, "%Y%m%d")
        base_date = (target_dt - datetime.timedelta(days=1)).strftime("%Y%m%d")
        base_time = "2300" # 전날 23시 발표 기준
        
        if region_code not in self.location_map:
            print(f"⚠️ 알 수 없는 지역 코드: {region_code}. 기본값(민락동) 사용.")
            nx, ny = 99, 75
        else:
            loc = self.location_map[region_code]
            nx, ny = loc['nx'], loc['ny']

        params = {
            'serviceKey': self.service_key,
            'pageNo': '1',
            'numOfRows': '1000',
            'dataType': 'JSON',
            'base_date': base_date,
            'base_time': base_time,
            'nx': nx,
            'ny': ny
        }

        try:
            # 2. API 호출
            response = requests.get(self.url, params=params)
            data = response.json()
            
            if response.status_code != 200 or 'response' not in data or 'body' not in data['response']:
                raise ValueError("API 응답 오류")

            items = data['response']['body']['items']['item']
            
            # 3. 데이터 파싱 및 변환
            return self._parse_api_response(items, target_date)

        except Exception as e:
            print(f"❌ API 호출 실패: {e}")
            print("➡️ 가상 데이터를 대신 반환합니다.")
            return self._generate_mock_data(target_date)

    def _parse_api_response(self, items, target_date):
        """API 응답을 모델용 DataFrame으로 변환"""
        # 카테고리 매핑: API 코드 -> 우리 모델 컬럼명
        # TMP: 1시간 기온 -> 기온
        # PCP: 1시간 강수량 -> 강수량
        # SKY: 하늘상태 -> 하늘상태
        # PTY: 강수형태 -> 강수형태
        
        forecast_dict = {}
        
        for item in items:
            fcst_date = item['fcstDate']
            fcst_time = item['fcstTime']
            category = item['category']
            value = item['fcstValue']
            
            if fcst_date != target_date:
                continue
                
            hour = int(fcst_time[:2])
            if hour not in forecast_dict:
                forecast_dict[hour] = {}
            
            if category == 'TMP':
                forecast_dict[hour]['기온'] = float(value)
            elif category == 'PCP':
                if value == '강수없음': value = 0
                elif value.endswith('mm'): value = value[:-2]
                forecast_dict[hour]['강수량'] = float(value)
            elif category == 'SKY':
                forecast_dict[hour]['하늘상태'] = int(value)
            elif category == 'PTY':
                forecast_dict[hour]['강수형태'] = int(value)

        # DataFrame 변환
        df = pd.DataFrame.from_dict(forecast_dict, orient='index')
        df.index.name = '시간대'
        
        # 결측치 처리 (기본값)
        df['기온'] = df.get('기온', 15.0)
        df['강수량'] = df.get('강수량', 0.0)
        df['하늘상태'] = df.get('하늘상태', 1) # 맑음
        df['강수형태'] = df.get('강수형태', 0) # 없음
        
        return df

    def d_generate_mock_data(self, target_date):
        """테스트용 가상 데이터 생성"""
        hours = range(24)
        
        # 가상 시나리오: 오후 2시부터 비가 옴
        mock_data = {
            '시간대': hours,
            '기온': [10 + (h - 12)**2 * -0.1 + 5 for h in hours], # 포물선 형태 기온
            '강수량': [0]*14 + [5.0]*4 + [0]*6, # 14시~17시 비 (5mm)
            '하늘상태': [1]*12 + [4]*6 + [3]*6, # 맑음 -> 흐림 -> 구름많음
            '강수형태': [0]*14 + [1]*4 + [0]*6  # 없음 -> 비 -> 없음
        }
        
        df = pd.DataFrame(mock_data)
        df.set_index('시간대', inplace=True)
        return df

# 사용 예시
if __name__ == "__main__":
    # API 키 (Decoding Key 사용 권장)
    SERVICE_KEY = "LV9VqydlVHSgjsUjQBB6HzhTyR6Z4XkSzqIfmQzuZaigTc8H5u2iPf7kpxA79doaQq16dxnNCknCZFIxJLftwQ=="
    
    # API 객체 생성
    api = WeatherAPI(service_key=SERVICE_KEY)
    
    # 오늘 날짜 구하기 (YYYYMMDD)
    today = datetime.datetime.now().strftime("%Y%m%d")
    
    print(f"📡 기상청 API 호출 중... (날짜: {today}, 지역: 민락동)")
    
    # 오늘 날짜의 예보 요청
    weather_df = api.get_forecast(today, 26500800)
    
    print(f"\n=== [API 결과] {today} 날씨 예보 (상위 24개) ===")
    print(weather_df.head(24))
    
    # 통계 확인
    print("\n[데이터 요약]")
    print(weather_df.describe())

