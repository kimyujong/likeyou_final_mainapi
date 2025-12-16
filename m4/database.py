"""
Supabase 데이터베이스 연동 모듈 (M4)

낙상 감지 이력을 Supabase에 저장/조회
"""

import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid

from supabase import create_client, Client
from dotenv import load_dotenv

# 환경변수 로드
# 현재 패키지(m4)의 상위 폴더(main_package)에 있는 .env 로드
from pathlib import Path
env_path = Path(__file__).resolve().parent.parent / '.env'
# env_path = Path("/home/ubuntu/main-api/.env")
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)


class SupabaseDB_M4:
    """Supabase 데이터베이스 클라이언트 (M4용)"""
    
    def __init__(self):
        """Supabase 클라이언트 초기화"""
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            logger.warning("⚠️ Supabase 환경변수가 설정되지 않았습니다. DB 기능이 비활성화됩니다.")
            self.client = None
            self.enabled = False
            return
        
        try:
            self.client: Client = create_client(supabase_url, supabase_key)
            self.enabled = True
            logger.info("✅ Supabase 연결 성공!")
        except Exception as e:
            logger.error(f"❌ Supabase 연결 실패: {str(e)}")
            self.client = None
            self.enabled = False
    
    def is_enabled(self) -> bool:
        """DB 연결 상태 확인"""
        return self.enabled and self.client is not None
    
    async def save_fall_event(
        self,
        cctv_no: str,
        timestamp: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:
        """
        낙상 이벤트를 DAT_Fall_Event 테이블에 저장
        
        Args:
            cctv_no: CCTV 식별자 (UUID) - COM_CCTV 테이블에 존재해야 함
            timestamp: 발생 시각 (기본값: 현재 시간)
        
        Returns:
            저장된 데이터 또는 None
        """
        if not self.is_enabled():
            logger.warning("DB가 비활성화되어 있습니다. 데이터를 저장하지 않습니다.")
            return None
        
        try:
            if timestamp is None:
                timestamp = datetime.now(timezone.utc)
            
            # UUID 생성
            event_id = str(uuid.uuid4())
            
            # DAT_Fall_Event 테이블 스키마에 맞춰 데이터 구성
            data = {
                'event_id': event_id,
                'cctv_no': cctv_no,
                'timestamp': timestamp.isoformat(),
                'status': 'NEW',     # 기본값: 미처리(NEW)
                'cleared_by': None   # 초기값: NULL
            }
            
            response = self.client.table('DAT_Fall_Event').insert(data).execute()
            
            logger.info(f"✅ 낙상 이벤트 저장 완료: CCTV={cctv_no}, Time={timestamp}")
            return response.data[0] if response.data else None
            
        except Exception as e:
            logger.error(f"❌ 낙상 이벤트 저장 실패: {str(e)}")
            return None
    
    async def get_cctv_info_by_idx(self, cctv_idx: str) -> Optional[Dict[str, Any]]:
        """
        cctv_idx ("CCTV_01")로 CCTV 정보 (UUID, URL 등) 조회
        
        Args:
            cctv_idx: CCTV 인덱스 (예: "CCTV_01")
        
        Returns:
            dict: {
                'cctv_no': UUID,
                'stream_url': 스트리밍 주소
            } 또는 None
        """
        if not self.is_enabled():
            return None
        
        try:
            # cctv_idx 컬럼으로 조회 (stream_url 포함)
            response = self.client.table('COM_CCTV').select('cctv_no, stream_url').eq('cctv_idx', cctv_idx).execute()
            
            if response.data and len(response.data) > 0:
                data = response.data[0]
                stream_url = data.get('stream_url')
                
                # [자동 경로 변환 로직 - M4 맞춤]
                # DB에 저장된 경로가 로컬/서버 환경과 다를 경우 자동으로 변환하여 확인
                if stream_url and not stream_url.startswith(('http', 'rtsp')):
                    # 1. 원본 경로가 존재하면 그대로 사용
                    if os.path.exists(stream_url):
                        pass
                    else:
                        # 2. 파일명만 추출
                        filename = os.path.basename(stream_url)
                        
                        # 3. 로컬 테스트 경로 (Windows)
                        local_path = f"C:/Users/kyj/OneDrive/Desktop/main_package/m4/test_file/{filename}"
                        
                        # 4. 서버 운영 경로 (Linux)
                        server_path = f"/home/ubuntu/storage/m4/{filename}"
                        
                        if os.path.exists(local_path):
                            logger.info(f"🔄 경로 자동 변환 (Local): {stream_url} -> {local_path}")
                            data['stream_url'] = local_path
                        elif os.path.exists(server_path):
                            logger.info(f"🔄 경로 자동 변환 (Server): {stream_url} -> {server_path}")
                            data['stream_url'] = server_path
                        else:
                            logger.warning(f"⚠️ 영상 파일을 찾을 수 없음: {stream_url} (Local/Server 경로 모두 없음)")
                
                return data
            return None
            
        except Exception as e:
            logger.error(f"❌ CCTV 정보 조회 실패 ({cctv_idx}): {str(e)}")
            return None

    async def get_test_cctv_no(self) -> Optional[str]:
        """
        테스트용 CCTV 번호(UUID) 조회 (COM_CCTV 테이블에서 1개)
        
        Returns:
            cctv_no (UUID) 또는 None
        """
        if not self.is_enabled():
            return None
        
        try:
            response = self.client.table('COM_CCTV').select('cctv_no').limit(1).execute()
            if response.data:
                return response.data[0]['cctv_no']
            return None
        except Exception as e:
            logger.error(f"❌ CCTV 조회 실패: {str(e)}")
            return None

    async def get_recent_events(
        self,
        limit: int = 10,
        cctv_no: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        최근 낙상 이벤트 조회
        
        Args:
            limit: 조회할 개수
            cctv_no: CCTV 필터 (선택)
        
        Returns:
            이벤트 목록
        """
        if not self.is_enabled():
            return []
        
        try:
            query = self.client.table('DAT_Fall_Event').select('*')
            
            if cctv_no:
                query = query.eq('cctv_no', cctv_no)
            
            response = query.order('timestamp', desc=True).limit(limit).execute()
            
            logger.info(f"✅ 낙상 이벤트 조회 완료: {len(response.data)}건")
            return response.data
            
        except Exception as e:
            logger.error(f"❌ 낙상 이벤트 조회 실패: {str(e)}")
            return []


# 전역 인스턴스
_db_instance = None


def get_db() -> SupabaseDB_M4:
    """
    Supabase DB 인스턴스 반환 (싱글톤)
    
    Returns:
        SupabaseDB_M4 인스턴스
    """
    global _db_instance
    
    if _db_instance is None:
        _db_instance = SupabaseDB_M4()
    
    return _db_instance


# 편의 함수들
async def save_fall_event(
    cctv_no: str,
    timestamp: Optional[datetime] = None
) -> Optional[Dict[str, Any]]:
    """낙상 이벤트 저장 (간편 함수)"""
    db = get_db()
    return await db.save_fall_event(
        cctv_no=cctv_no,
        timestamp=timestamp
    )


async def get_events(limit: int = 10, cctv_no: Optional[str] = None) -> List[Dict[str, Any]]:
    """낙상 이벤트 조회 (간편 함수)"""
    db = get_db()
    return await db.get_recent_events(limit=limit, cctv_no=cctv_no)


async def get_test_cctv_no() -> Optional[str]:
    """테스트용 CCTV 번호 조회 (간편 함수)"""
    db = get_db()
    return await db.get_test_cctv_no()


if __name__ == "__main__":
    # 테스트 코드
    import asyncio
    
    async def test_fall_db():
        """낙상 DB 저장 테스트"""
        print("\n" + "="*60)
        print("🚨 낙상 이벤트 DB 저장 테스트")
        print("="*60 + "\n")
        
        db = get_db()
        if not db.is_enabled():
            print("❌ Supabase가 설정되지 않았습니다.")
            return
        
        try:
            # 1. 테스트할 CCTV ID 확보
            print("🔄 COM_CCTV 테이블에서 CCTV ID 조회 중...")
            cctv_query = db.client.table('COM_CCTV').select('cctv_no').limit(1).execute()
            
            if not cctv_query.data:
                print("❌ COM_CCTV 테이블이 비어있습니다.")
                return
            
            test_cctv_no = cctv_query.data[0]['cctv_no']
            print(f"✅ CCTV ID 확보: {test_cctv_no}")
            
            # 2. 낙상 이벤트 저장
            print("\n💾 낙상 이벤트 저장 중...")
            result = await db.save_fall_event(cctv_no=test_cctv_no)
            
            if result:
                print("✅ 저장 성공!")
                print(f"  - event_id: {result.get('event_id')}")
                print(f"  - status: {result.get('status')}")
                print(f"  - cleared_by: {result.get('cleared_by')}")
            else:
                print("❌ 저장 실패")
            
            # 3. 조회 테스트
            print("\n📋 최근 이벤트 조회:")
            events = await db.get_recent_events(limit=3)
            for evt in events:
                print(f"  - {evt.get('timestamp')}: {evt.get('status')}")
                
        except Exception as e:
            print(f"\n❌ 오류 발생: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # 실행
    asyncio.run(test_fall_db())


