"""
CoinTrader 텔레그램 봇
사용자와의 상호작용을 위한 텔레그램 봇 명령어 처리
"""
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError

from ..config import settings
from ..utils.logger import setup_logger

class TelegramBot:
    """
    텔레그램 봇
    
    주요 기능:
    - 봇 명령어 처리
    - 시스템 상태 조회
    - 거래 제어 (시작/중지)
    - 포트폴리오 조회
    - 알림 설정 관리
    """
    
    def __init__(self):
        self.logger = setup_logger("telegram.bot")
        
        # 텔레그램 봇 설정
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.enabled = settings.TELEGRAM_ENABLED
        
        # 봇 애플리케이션
        self.application = None
        self.bot = None
        
        # 실행 상태
        self.is_running = False
        
        # 외부 참조 (의존성 주입용)
        self.trading_engine = None
        self.portfolio_manager = None
        self.risk_manager = None
        
        if self.enabled and self.bot_token:
            self.logger.info("텔레그램 봇 초기화 완료")
        else:
            self.logger.warning("텔레그램 봇 비활성화 또는 설정 불완전")
    
    def set_dependencies(self, trading_engine=None, portfolio_manager=None, risk_manager=None):
        """외부 의존성 설정"""
        self.trading_engine = trading_engine
        self.portfolio_manager = portfolio_manager
        self.risk_manager = risk_manager
    
    async def start(self):
        """텔레그램 봇 시작"""
        if not self.enabled or not self.bot_token:
            self.logger.info("텔레그램 봇 비활성화")
            return
        
        try:
            # 애플리케이션 생성
            self.application = Application.builder().token(self.bot_token).build()
            self.bot = self.application.bot
            
            # 명령어 핸들러 등록
            self._register_handlers()
            
            # 봇 시작
            await self.application.initialize()
            await self.application.start()
            
            # 폴링 시작 (백그라운드)
            self._polling_task = asyncio.create_task(self._start_polling())
            
            self.is_running = True
            self.logger.info("텔레그램 봇 시작 완료")
            
        except Exception as e:
            self.logger.error(f"텔레그램 봇 시작 오류: {e}")
            raise
    
    async def stop(self):
        """텔레그램 봇 중지"""
        if self.application and self.is_running:
            try:
                await self.application.stop()
                await self.application.shutdown()
                
                self.is_running = False
                self.logger.info("텔레그램 봇 중지 완료")
                
            except Exception as e:
                self.logger.error(f"텔레그램 봇 중지 오류: {e}")
    
    def _register_handlers(self):
        """명령어 핸들러 등록"""
        try:
            # 기본 명령어
            self.application.add_handler(CommandHandler("start", self.cmd_start))
            self.application.add_handler(CommandHandler("help", self.cmd_help))
            self.application.add_handler(CommandHandler("status", self.cmd_status))
            
            # 거래 관련 명령어
            self.application.add_handler(CommandHandler("trading_start", self.cmd_trading_start))
            self.application.add_handler(CommandHandler("trading_stop", self.cmd_trading_stop))
            self.application.add_handler(CommandHandler("trading_status", self.cmd_trading_status))
            
            # 포트폴리오 관련 명령어
            self.application.add_handler(CommandHandler("portfolio", self.cmd_portfolio))
            self.application.add_handler(CommandHandler("positions", self.cmd_positions))
            self.application.add_handler(CommandHandler("balance", self.cmd_balance))
            
            # 통계 및 성과 관련 명령어
            self.application.add_handler(CommandHandler("stats", self.cmd_stats))
            self.application.add_handler(CommandHandler("daily", self.cmd_daily_summary))
            self.application.add_handler(CommandHandler("performance", self.cmd_performance))
            
            # 리스크 관련 명령어
            self.application.add_handler(CommandHandler("risk", self.cmd_risk_status))
            self.application.add_handler(CommandHandler("emergency_stop", self.cmd_emergency_stop))
            
            # 기타 명령어
            self.application.add_handler(CommandHandler("ping", self.cmd_ping))
            self.application.add_handler(CommandHandler("version", self.cmd_version))
            
            # 알 수 없는 명령어 처리
            self.application.add_handler(MessageHandler(filters.COMMAND, self.cmd_unknown))
            
            self.logger.info("텔레그램 봇 핸들러 등록 완료")
            
        except Exception as e:
            self.logger.error(f"핸들러 등록 오류: {e}")
    
    async def _start_polling(self):
        """폴링 시작 (백그라운드)"""
        try:
            await self.application.updater.start_polling()
            self.logger.info("텔레그램 봇 폴링 시작")
        except Exception as e:
            self.logger.error(f"폴링 시작 오류: {e}")
    
    # ===========================================
    # 명령어 핸들러들
    # ===========================================
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """시작 명령어"""
        try:
            welcome_message = """
🤖 **CoinTrader 봇에 오신 것을 환영합니다!**

이 봇을 통해 거래 시스템을 모니터링하고 제어할 수 있습니다.

📋 **주요 명령어**:
• `/status` - 시스템 상태 확인
• `/portfolio` - 포트폴리오 현황
• `/trading_status` - 거래 엔진 상태
• `/help` - 전체 명령어 목록

🚀 시작하려면 `/help` 명령어를 입력하세요!
"""
            
            await update.message.reply_text(welcome_message, parse_mode='Markdown')
            
        except Exception as e:
            self.logger.error(f"start 명령어 오류: {e}")
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """도움말 명령어"""
        try:
            help_message = """
📚 **CoinTrader 봇 명령어 가이드**

🎯 **기본 명령어**:
• `/start` - 봇 시작 메시지
• `/help` - 이 도움말
• `/status` - 전체 시스템 상태
• `/ping` - 봇 응답 테스트
• `/version` - 시스템 버전 정보

💰 **거래 관련**:
• `/trading_status` - 거래 엔진 상태
• `/trading_start` - 거래 시작
• `/trading_stop` - 거래 중지

💼 **포트폴리오**:
• `/portfolio` - 포트폴리오 요약
• `/positions` - 보유 포지션 상세
• `/balance` - 잔고 현황

📊 **통계/성과**:
• `/stats` - 거래 통계
• `/daily` - 일일 요약
• `/performance` - 성과 지표

⚠️ **리스크 관리**:
• `/risk` - 리스크 상태
• `/emergency_stop` - 긴급 정지

🔄 명령어는 언제든지 사용 가능합니다!
"""
            
            await update.message.reply_text(help_message, parse_mode='Markdown')
            
        except Exception as e:
            self.logger.error(f"help 명령어 오류: {e}")
    
    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """시스템 상태 명령어"""
        try:
            status_message = "🔍 **시스템 상태 조회 중...**"
            await update.message.reply_text(status_message, parse_mode='Markdown')
            
            # 시스템 상태 수집
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 거래 엔진 상태
            trading_status = "❌ 비활성"
            if self.trading_engine:
                if hasattr(self.trading_engine, 'is_running') and self.trading_engine.is_running:
                    trading_status = "✅ 실행 중"
                elif hasattr(self.trading_engine, 'is_trading_enabled') and self.trading_engine.is_trading_enabled:
                    trading_status = "⏸️ 대기 중"
            
            # 포트폴리오 요약
            portfolio_text = "조회 불가"
            if self.portfolio_manager:
                try:
                    summary = await self.portfolio_manager.get_portfolio_summary()
                    total_value = summary.get('total_krw_value', 0)
                    positions_count = summary.get('positions_count', 0)
                    portfolio_text = f"{total_value:,.0f}원 ({positions_count}개 포지션)"
                except:
                    portfolio_text = "조회 실패"
            
            status_detail = f"""
📊 **CoinTrader 시스템 상태**

🤖 **거래 엔진**: {trading_status}
💼 **포트폴리오**: {portfolio_text}
📱 **텔레그램 봇**: ✅ 실행 중
⏰ **조회 시간**: {current_time}

#시스템상태
"""
            
            await update.message.reply_text(status_detail, parse_mode='Markdown')
            
        except Exception as e:
            self.logger.error(f"status 명령어 오류: {e}")
            await update.message.reply_text("❌ 상태 조회 중 오류가 발생했습니다.")
    
    async def cmd_trading_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """거래 상태 명령어"""
        try:
            if not self.trading_engine:
                await update.message.reply_text("❌ 거래 엔진에 연결할 수 없습니다.")
                return
            
            # 거래 엔진 상태 조회
            if hasattr(self.trading_engine, 'get_engine_status'):
                status = self.trading_engine.get_engine_status()
                
                is_running = status.get('is_running', False)
                is_trading = status.get('is_trading_enabled', False)
                trading_mode = status.get('trading_mode', 'unknown')
                target_markets = status.get('target_markets', [])
                statistics = status.get('statistics', {})
                
                running_emoji = "✅" if is_running else "❌"
                trading_emoji = "🟢" if is_trading else "🔴"
                
                message = f"""
🤖 **거래 엔진 상태**

{running_emoji} **엔진 상태**: {'실행 중' if is_running else '중지됨'}
{trading_emoji} **거래 활성화**: {'활성' if is_trading else '비활성'}
🎯 **거래 모드**: {trading_mode}
📊 **대상 마켓**: {', '.join(target_markets) if target_markets else '없음'}

📈 **거래 통계**:
• 총 신호: {statistics.get('total_signals', 0)}개
• 성공 거래: {statistics.get('successful_trades', 0)}개
• 실패 거래: {statistics.get('failed_trades', 0)}개
• 성공률: {statistics.get('success_rate', 0):.1f}%

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
                
                await update.message.reply_text(message, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ 거래 엔진 상태를 조회할 수 없습니다.")
            
        except Exception as e:
            self.logger.error(f"trading_status 명령어 오류: {e}")
            await update.message.reply_text("❌ 거래 상태 조회 중 오류가 발생했습니다.")
    
    async def cmd_portfolio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """포트폴리오 명령어"""
        try:
            if not self.portfolio_manager:
                await update.message.reply_text("❌ 포트폴리오 매니저에 연결할 수 없습니다.")
                return
            
            await update.message.reply_text("💼 **포트폴리오 조회 중...**", parse_mode='Markdown')
            
            # 포트폴리오 요약 조회
            summary = await self.portfolio_manager.get_portfolio_summary()
            
            total_value = summary.get('total_krw_value', 0)
            krw_balance = summary.get('krw_balance', 0)
            positions_count = summary.get('positions_count', 0)
            daily_pnl = summary.get('daily_pnl', 0)
            total_pnl = summary.get('total_pnl', 0)
            win_rate = summary.get('win_rate', 0)
            
            daily_emoji = "📈" if daily_pnl > 0 else "📉" if daily_pnl < 0 else "➖"
            total_emoji = "💰" if total_pnl > 0 else "💸" if total_pnl < 0 else "➖"
            
            message = f"""
💼 **포트폴리오 현황**

💰 **총 자산**: {total_value:,.0f} KRW
💵 **KRW 잔고**: {krw_balance:,.0f} KRW
📦 **포지션 수**: {positions_count}개

{daily_emoji} **일일 손익**: {daily_pnl:+,.0f} KRW
{total_emoji} **총 손익**: {total_pnl:+,.0f} KRW
🎯 **승률**: {win_rate:.1f}%

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

💡 더 자세한 정보는 `/positions` 또는 `/balance`를 사용하세요.
"""
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            self.logger.error(f"portfolio 명령어 오류: {e}")
            await update.message.reply_text("❌ 포트폴리오 조회 중 오류가 발생했습니다.")
    
    async def cmd_ping(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """핑 명령어"""
        try:
            response_time = datetime.now().strftime('%H:%M:%S')
            message = f"🏓 **Pong!**\n\n⏰ 응답 시간: {response_time}"
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            self.logger.error(f"ping 명령어 오류: {e}")
    
    async def cmd_version(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """버전 명령어"""
        try:
            message = f"""
📋 **CoinTrader 시스템 정보**

🤖 **시스템**: CoinTrader v1.0.0
🐍 **Python**: 3.11+
⚡ **FastAPI**: Backend API
⚛️ **Next.js**: Frontend Dashboard
📱 **Telegram**: Bot Interface

🏗️ **아키텍처**: Microservices
💾 **데이터베이스**: SQLite/PostgreSQL
📊 **거래소**: Upbit API

⏰ **빌드 시간**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            self.logger.error(f"version 명령어 오류: {e}")
    
    async def cmd_unknown(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """알 수 없는 명령어"""
        try:
            command = update.message.text
            message = f"""
❓ **알 수 없는 명령어**: `{command}`

💡 사용 가능한 명령어를 확인하려면 `/help`를 입력하세요.
"""
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            self.logger.error(f"unknown 명령어 오류: {e}")
    
    # 추가 명령어들 (간단히 구현)
    
    async def cmd_trading_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """거래 시작 명령어"""
        try:
            if self.trading_engine and hasattr(self.trading_engine, 'enable_trading'):
                await self.trading_engine.enable_trading()
                await update.message.reply_text("✅ 거래가 활성화되었습니다.")
            else:
                await update.message.reply_text("❌ 거래 엔진에 연결할 수 없습니다.")
        except Exception as e:
            self.logger.error(f"trading_start 명령어 오류: {e}")
            await update.message.reply_text("❌ 거래 시작 중 오류가 발생했습니다.")
    
    async def cmd_trading_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """거래 중지 명령어"""
        try:
            if self.trading_engine and hasattr(self.trading_engine, 'disable_trading'):
                await self.trading_engine.disable_trading()
                await update.message.reply_text("⏸️ 거래가 비활성화되었습니다.")
            else:
                await update.message.reply_text("❌ 거래 엔진에 연결할 수 없습니다.")
        except Exception as e:
            self.logger.error(f"trading_stop 명령어 오류: {e}")
            await update.message.reply_text("❌ 거래 중지 중 오류가 발생했습니다.")
    
    async def cmd_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """포지션 조회 명령어"""
        await update.message.reply_text("📦 포지션 상세 조회 기능은 개발 중입니다.")
    
    async def cmd_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """잔고 조회 명령어"""
        await update.message.reply_text("💵 잔고 상세 조회 기능은 개발 중입니다.")
    
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """통계 명령어"""
        await update.message.reply_text("📊 거래 통계 기능은 개발 중입니다.")
    
    async def cmd_daily_summary(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """일일 요약 명령어"""
        await update.message.reply_text("📋 일일 요약 기능은 개발 중입니다.")
    
    async def cmd_performance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """성과 지표 명령어"""
        await update.message.reply_text("📈 성과 지표 기능은 개발 중입니다.")
    
    async def cmd_risk_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """리스크 상태 명령어"""
        await update.message.reply_text("⚠️ 리스크 상태 조회 기능은 개발 중입니다.")
    
    async def cmd_emergency_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """긴급 정지 명령어"""
        try:
            if self.risk_manager and hasattr(self.risk_manager, 'force_emergency_stop'):
                await self.risk_manager.force_emergency_stop("텔레그램 봇 명령")
                await update.message.reply_text("🚨 긴급 정지가 활성화되었습니다!")
            else:
                await update.message.reply_text("❌ 리스크 매니저에 연결할 수 없습니다.")
        except Exception as e:
            self.logger.error(f"emergency_stop 명령어 오류: {e}")
            await update.message.reply_text("❌ 긴급 정지 중 오류가 발생했습니다.")
    
    def get_statistics(self) -> Dict[str, Any]:
        """봇 통계"""
        return {
            'enabled': self.enabled,
            'is_running': self.is_running,
            'bot_token_configured': bool(self.bot_token),
            'chat_id_configured': bool(self.chat_id)
        }
