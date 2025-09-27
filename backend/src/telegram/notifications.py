"""
CoinTrader 텔레그램 알림 시스템
거래 및 시스템 상태를 텔레그램으로 알림하는 모듈
"""
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import json

from telegram import Bot
from telegram.error import TelegramError, NetworkError, TimedOut

from ..config import settings
from ..utils.logger import setup_logger

class TelegramNotifier:
    """
    텔레그램 알림 발송자
    
    주요 기능:
    - 거래 체결 알림
    - 시스템 상태 알림
    - 오류 및 경고 알림
    - 일일 성과 요약
    - 포트폴리오 상태 알림
    """
    
    def __init__(self):
        self.logger = setup_logger("telegram.notifier")
        
        # 텔레그램 봇 설정
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.notifications_enabled = settings.TELEGRAM_NOTIFICATIONS_ENABLED
        
        # 봇 인스턴스
        self.bot = None
        if self.bot_token:
            self.bot = Bot(token=self.bot_token)
        
        # 알림 설정
        self.trade_alerts = settings.NOTIFICATION_TRADE_ALERTS
        self.error_alerts = settings.NOTIFICATION_ERROR_ALERTS
        self.daily_summary = settings.NOTIFICATION_DAILY_SUMMARY
        self.system_status = settings.NOTIFICATION_SYSTEM_STATUS
        
        # 알림 통계
        self.total_sent = 0
        self.total_failed = 0
        self.last_sent_time = None
        
        # 알림 제한 (스팸 방지)
        self.max_alerts_per_minute = 10
        self.alert_counts = {}
        
        if self.notifications_enabled and self.bot:
            self.logger.info("텔레그램 알림 시스템 초기화 완료")
        else:
            self.logger.warning("텔레그램 알림 비활성화 또는 설정 불완전")
    
    async def send_trade_notification(self, trade_data: Dict[str, Any]) -> bool:
        """
        거래 체결 알림 발송
        
        Args:
            trade_data: 거래 정보
            
        Returns:
            bool: 발송 성공 여부
        """
        if not self.trade_alerts or not self._can_send_notification():
            return False
        
        try:
            side = trade_data.get('side', 'unknown')
            market = trade_data.get('market', 'UNKNOWN')
            price = trade_data.get('price', 0)
            volume = trade_data.get('volume', 0)
            amount = trade_data.get('amount', 0)
            strategy = trade_data.get('strategy', 'unknown')
            profit_loss = trade_data.get('profit_loss', 0)
            
            # 거래 방향에 따른 이모지 및 텍스트
            if side == 'buy':
                emoji = "🟢"
                action_text = "매수"
                color_indicator = "📈"
            else:
                emoji = "🔴"
                action_text = "매도"
                color_indicator = "📉" if profit_loss < 0 else "📈"
            
            # 수익/손실 정보 (매도 시에만)
            profit_text = ""
            if side == 'sell' and profit_loss != 0:
                profit_emoji = "💰" if profit_loss > 0 else "💸"
                profit_text = f"\n{profit_emoji} **손익**: {profit_loss:+,.0f}원"
            
            # 메시지 구성
            message = f"""
{emoji} **거래 체결 알림** {color_indicator}

📊 **종목**: `{market}`
💱 **구분**: {action_text}
💰 **가격**: {price:,.0f} KRW
📦 **수량**: {volume:.6f}
💵 **총액**: {amount:,.0f} KRW
🎯 **전략**: {strategy}{profit_text}
⏰ **시간**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

#{market.replace('-', '')} #거래체결 #{action_text}
"""
            
            success = await self._send_message(message)
            
            if success:
                self.logger.info(f"거래 알림 발송 완료: {market} {action_text}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"거래 알림 발송 오류: {e}")
            return False
    
    async def send_system_notification(self, message: str, level: str = "INFO") -> bool:
        """
        시스템 상태 알림 발송
        
        Args:
            message: 알림 메시지
            level: 알림 레벨 (INFO, WARNING, ERROR, CRITICAL)
            
        Returns:
            bool: 발송 성공 여부
        """
        if not self.system_status or not self._can_send_notification():
            return False
        
        try:
            # 레벨별 이모지
            level_emojis = {
                'INFO': 'ℹ️',
                'WARNING': '⚠️',
                'ERROR': '❌',
                'CRITICAL': '🚨'
            }
            
            emoji = level_emojis.get(level, 'ℹ️')
            
            formatted_message = f"""
{emoji} **시스템 알림**

{message}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

#시스템알림 #{level.lower()}
"""
            
            success = await self._send_message(formatted_message)
            
            if success:
                self.logger.info(f"시스템 알림 발송 완료: {level} - {message[:50]}...")
            
            return success
            
        except Exception as e:
            self.logger.error(f"시스템 알림 발송 오류: {e}")
            return False
    
    async def send_error_notification(self, error_message: str, error_details: Optional[str] = None) -> bool:
        """
        오류 알림 발송
        
        Args:
            error_message: 오류 메시지
            error_details: 상세 오류 정보 (선택)
            
        Returns:
            bool: 발송 성공 여부
        """
        if not self.error_alerts or not self._can_send_notification():
            return False
        
        try:
            details_text = ""
            if error_details:
                # 너무 긴 상세 정보는 자르기
                if len(error_details) > 500:
                    error_details = error_details[:500] + "..."
                details_text = f"\n\n**상세 정보**:\n```\n{error_details}\n```"
            
            message = f"""
🚨 **오류 발생**

❌ {error_message}{details_text}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

#오류알림 #시스템오류
"""
            
            success = await self._send_message(message)
            
            if success:
                self.logger.info(f"오류 알림 발송 완료: {error_message[:50]}...")
            
            return success
            
        except Exception as e:
            self.logger.error(f"오류 알림 발송 실패: {e}")
            return False
    
    async def send_daily_summary(self, summary_data: Dict[str, Any]) -> bool:
        """
        일일 거래 요약 발송
        
        Args:
            summary_data: 일일 요약 데이터
            
        Returns:
            bool: 발송 성공 여부
        """
        if not self.daily_summary or not self._can_send_notification():
            return False
        
        try:
            date = summary_data.get('date', datetime.now().strftime('%Y-%m-%d'))
            total_trades = summary_data.get('total_trades', 0)
            total_amount = summary_data.get('total_amount', 0)
            total_profit = summary_data.get('total_profit', 0)
            win_rate = summary_data.get('win_rate', 0)
            winning_trades = summary_data.get('winning_trades', 0)
            losing_trades = summary_data.get('losing_trades', 0)
            
            # 수익/손실에 따른 이모지
            profit_emoji = "📈" if total_profit > 0 else "📉" if total_profit < 0 else "➖"
            
            message = f"""
📊 **일일 거래 요약** {profit_emoji}

📅 **날짜**: {date}
💰 **총 거래금액**: {total_amount:,.0f} KRW
📈 **거래 횟수**: {total_trades}회
💹 **실현 손익**: {total_profit:+,.0f} KRW
🎯 **승률**: {win_rate:.1f}%

📊 **거래 결과**:
  ✅ 수익 거래: {winning_trades}회
  ❌ 손실 거래: {losing_trades}회

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

#일일요약 #거래성과
"""
            
            success = await self._send_message(message)
            
            if success:
                self.logger.info(f"일일 요약 발송 완료: {date}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"일일 요약 발송 오류: {e}")
            return False
    
    async def send_portfolio_status(self, portfolio_data: Dict[str, Any]) -> bool:
        """
        포트폴리오 상태 알림 발송
        
        Args:
            portfolio_data: 포트폴리오 데이터
            
        Returns:
            bool: 발송 성공 여부
        """
        if not self._can_send_notification():
            return False
        
        try:
            total_value = portfolio_data.get('total_krw_value', 0)
            krw_balance = portfolio_data.get('krw_balance', 0)
            positions_count = portfolio_data.get('positions_count', 0)
            total_pnl = portfolio_data.get('total_pnl', 0)
            win_rate = portfolio_data.get('win_rate', 0)
            
            profit_emoji = "📈" if total_pnl > 0 else "📉" if total_pnl < 0 else "➖"
            
            message = f"""
💼 **포트폴리오 현황** {profit_emoji}

💰 **총 자산**: {total_value:,.0f} KRW
💵 **KRW 잔고**: {krw_balance:,.0f} KRW
📦 **보유 포지션**: {positions_count}개
💹 **총 손익**: {total_pnl:+,.0f} KRW
🎯 **승률**: {win_rate:.1f}%

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

#포트폴리오 #자산현황
"""
            
            success = await self._send_message(message)
            
            if success:
                self.logger.info("포트폴리오 상태 알림 발송 완료")
            
            return success
            
        except Exception as e:
            self.logger.error(f"포트폴리오 상태 알림 발송 오류: {e}")
            return False
    
    async def send_risk_alert(self, risk_data: Dict[str, Any]) -> bool:
        """
        리스크 경고 알림 발송
        
        Args:
            risk_data: 리스크 데이터
            
        Returns:
            bool: 발송 성공 여부
        """
        if not self._can_send_notification():
            return False
        
        try:
            alert_type = risk_data.get('type', 'UNKNOWN')
            message_text = risk_data.get('message', '알 수 없는 리스크')
            level = risk_data.get('level', 'WARNING')
            
            # 레벨별 이모지
            level_emojis = {
                'WARNING': '⚠️',
                'ERROR': '❌',
                'CRITICAL': '🚨'
            }
            
            emoji = level_emojis.get(level, '⚠️')
            
            message = f"""
{emoji} **리스크 경고**

🔔 **유형**: {alert_type}
📝 **내용**: {message_text}
📊 **레벨**: {level}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

#리스크경고 #{alert_type.lower()} #{level.lower()}
"""
            
            success = await self._send_message(message)
            
            if success:
                self.logger.info(f"리스크 경고 발송 완료: {alert_type}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"리스크 경고 발송 오류: {e}")
            return False
    
    async def _send_message(self, message: str) -> bool:
        """
        실제 메시지 발송
        
        Args:
            message: 발송할 메시지
            
        Returns:
            bool: 발송 성공 여부
        """
        if not self.notifications_enabled or not self.bot or not self.chat_id:
            return False
        
        try:
            # 메시지 길이 제한 (4096자)
            if len(message) > 4000:
                message = message[:4000] + "\n\n... (메시지가 너무 길어 일부 생략)"
            
            # 메시지 발송
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
            # 통계 업데이트
            self.total_sent += 1
            self.last_sent_time = datetime.now()
            
            return True
            
        except TimedOut:
            self.logger.warning("텔레그램 메시지 발송 타임아웃")
            return False
        except NetworkError:
            self.logger.warning("텔레그램 네트워크 오류")
            return False
        except TelegramError as e:
            self.logger.error(f"텔레그램 API 오류: {e}")
            self.total_failed += 1
            return False
        except Exception as e:
            self.logger.error(f"메시지 발송 오류: {e}")
            self.total_failed += 1
            return False
    
    def _can_send_notification(self) -> bool:
        """알림 발송 가능 여부 확인"""
        if not self.notifications_enabled:
            return False
        
        if not self.bot or not self.chat_id:
            return False
        
        # 스팸 방지: 분당 최대 알림 수 확인
        current_minute = datetime.now().strftime('%Y%m%d%H%M')
        
        if current_minute not in self.alert_counts:
            self.alert_counts = {current_minute: 0}  # 이전 분 데이터 삭제
        
        if self.alert_counts[current_minute] >= self.max_alerts_per_minute:
            self.logger.warning("분당 알림 제한 도달, 발송 생략")
            return False
        
        self.alert_counts[current_minute] += 1
        return True
    
    async def test_connection(self) -> bool:
        """텔레그램 연결 테스트"""
        try:
            if not self.bot:
                return False
            
            # 봇 정보 가져오기
            bot_info = await self.bot.get_me()
            
            if bot_info:
                self.logger.info(f"텔레그램 봇 연결 성공: @{bot_info.username}")
                
                # 테스트 메시지 발송
                test_message = f"""
🔧 **연결 테스트**

✅ CoinTrader 텔레그램 봇이 정상적으로 연결되었습니다.

🤖 **봇 정보**: @{bot_info.username}
⏰ **테스트 시간**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

#연결테스트 #시스템체크
"""
                
                success = await self._send_message(test_message)
                return success
            
            return False
            
        except Exception as e:
            self.logger.error(f"텔레그램 연결 테스트 실패: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """알림 시스템 통계"""
        success_rate = 0
        if self.total_sent + self.total_failed > 0:
            success_rate = (self.total_sent / (self.total_sent + self.total_failed)) * 100
        
        return {
            'enabled': self.notifications_enabled,
            'total_sent': self.total_sent,
            'total_failed': self.total_failed,
            'success_rate': success_rate,
            'last_sent_time': self.last_sent_time.isoformat() if self.last_sent_time else None,
            'settings': {
                'trade_alerts': self.trade_alerts,
                'error_alerts': self.error_alerts,
                'daily_summary': self.daily_summary,
                'system_status': self.system_status
            }
        }
    
    def update_settings(self, new_settings: Dict[str, Any]):
        """알림 설정 업데이트"""
        if 'trade_alerts' in new_settings:
            self.trade_alerts = new_settings['trade_alerts']
        
        if 'error_alerts' in new_settings:
            self.error_alerts = new_settings['error_alerts']
        
        if 'daily_summary' in new_settings:
            self.daily_summary = new_settings['daily_summary']
        
        if 'system_status' in new_settings:
            self.system_status = new_settings['system_status']
        
        self.logger.info("텔레그램 알림 설정 업데이트 완료")
    
    async def start(self):
        """텔레그램 알림 시스템 시작"""
        if self.notifications_enabled and self.bot:
            # 연결 테스트
            connection_success = await self.test_connection()
            if connection_success:
                self.logger.info("텔레그램 알림 시스템 시작 완료")
            else:
                self.logger.error("텔레그램 연결 실패")
        else:
            self.logger.info("텔레그램 알림 비활성화 상태")
    
    async def stop(self):
        """텔레그램 알림 시스템 종료"""
        if self.notifications_enabled and self.bot:
            # 종료 알림 발송
            await self.send_system_notification("🛑 CoinTrader 시스템이 종료됩니다.", "INFO")
            self.logger.info("텔레그램 알림 시스템 종료 완료")
        else:
            self.logger.info("텔레그램 알림 시스템 종료")

