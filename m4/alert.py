"""
M4 낙상 경보 시스템
"""

from datetime import datetime
from constants import FallStatus, DEFAULT_ALERT_COOLDOWN


class FallAlertSystem:
    """
    낙상 경보 알림 시스템
    """
    def __init__(self, alert_cooldown=DEFAULT_ALERT_COOLDOWN):
        """
        Args:
            alert_cooldown: 중복 알림 방지 대기 시간 (초)
        """
        self.alert_cooldown = alert_cooldown
        self.last_alert_time = None
        self.alert_history = []
    
    def check_alert(self, detection_result):
        """
        경보 발생 여부 확인
        
        Args:
            detection_result: FallDetector의 detect_frame 결과
        
        Returns:
            tuple: (should_alert: bool, message: str or None)
        """
        current_time = datetime.now()
        
        # 낙상 감지되지 않으면 경보 없음
        if not detection_result['fall_detected']:
            return False, None
        
        # 쿨다운 체크
        if self.last_alert_time:
            elapsed = (current_time - self.last_alert_time).total_seconds()
            if elapsed < self.alert_cooldown:
                return False, None
        
        # 경보 발생
        self.last_alert_time = current_time
        
        message = f"""
🚨 낙상 감지 경보 🚨
━━━━━━━━━━━━━━━━━━━━━━
⏰ 시간: {current_time.strftime('%Y-%m-%d %H:%M:%S')}
👤 낙상자 수: {len(detection_result['fallen_persons'])}명
📊 총 낙상 횟수: {detection_result['fall_count']}회
⚠️  상태: {detection_result['status'].korean}
━━━━━━━━━━━━━━━━━━━━━━
조치: 즉시 현장 확인 및 응급 조치 필요!
"""
        
        # 경보 기록
        self.alert_history.append({
            'timestamp': current_time,
            'fall_count': detection_result['fall_count'],
            'persons_count': len(detection_result['fallen_persons'])
        })
        
        return True, message
    
    def send_alert(self, message, method='console'):
        """
        실제 알림 발송
        
        Args:
            message: 알림 메시지
            method: 'console', 'email', 'sms', 'slack' 등
        """
        if method == 'console':
            print(message)
        
        # TODO: 실제 알림 구현
        # elif method == 'email':
        #     send_email(message)
        # elif method == 'sms':
        #     send_sms(message)
        # elif method == 'slack':
        #     send_slack_webhook(message)
        # elif method == 'db':
        #     save_to_database(message)
    
    def get_alert_history(self):
        """경보 기록 반환"""
        return self.alert_history

