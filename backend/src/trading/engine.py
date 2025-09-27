"""
CoinTrader 자동매매 엔진
전체 거래 프로세스를 관리하는 메인 엔진
"""
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from ..config import settings
from ..upbit.client import UpbitClient
from ..upbit.websocket import UpbitWebSocketClient
from ..database.repositories.trade_repository import TradeRepository
from ..telegram.notifications import TelegramNotifier
from .strategies.base import BaseStrategy, strategy_manager
from .strategies.scalping import ScalpingStrategy
from .risk_manager import RiskManager
from .order_manager import OrderManager
from .portfolio import Portfolio
from ..utils.logger import setup_logger

class TradingEngine:
    """
    자동매매 엔진
    
    주요 기능:
    - 실시간 시장 데이터 수신
    - 거래 전략 실행
    - 주문 관리 및 실행
    - 리스크 관리
    - 포트폴리오 관리
    - 성과 추적
    """
    
    def __init__(self):
        self.logger = setup_logger("trading.engine")
        
        # 외부 서비스 클라이언트
        self.upbit_client = UpbitClient()
        self.trade_repository = TradeRepository()
        self.telegram_notifier = TelegramNotifier()
        
        # 내부 관리자들
        self.risk_manager = RiskManager()
        self.order_manager = OrderManager(self.upbit_client, self.telegram_notifier)
        self.portfolio = Portfolio()
        
        # WebSocket 클라이언트
        self.websocket_client = None
        
        # 상태 관리
        self.is_running = False
        self.is_trading_enabled = settings.TRADING_ENABLED
        self.trading_mode = settings.TRADING_MODE  # 'live' or 'paper'
        
        # 거래 대상 마켓
        self.target_markets = [settings.DEFAULT_MARKET]
        
        # 전략 초기화
        self._initialize_strategies()
        
        # 통계
        self.start_time = None
        self.total_signals = 0
        self.successful_trades = 0
        self.failed_trades = 0
        
        self.logger.info(f"거래 엔진 초기화 완료 - 모드: {self.trading_mode}")
    
    def _initialize_strategies(self):
        """거래 전략 초기화"""
        try:
            # 스캘핑 전략 등록
            scalping_strategy = ScalpingStrategy({
                'enabled': settings.SCALPING_ENABLED,
                'rsi_oversold': settings.SCALPING_RSI_OVERSOLD,
                'rsi_overbought': settings.SCALPING_RSI_OVERBOUGHT,
                'min_volume_24h': settings.SCALPING_MIN_VOLUME,
                'min_profit_ratio': settings.SCALPING_MIN_PROFIT / 100,
                'max_loss_ratio': settings.SCALPING_MAX_LOSS / 100,
            })
            
            strategy_manager.register_strategy(scalping_strategy)
            
            self.logger.info("거래 전략 초기화 완료")
            
        except Exception as e:
            self.logger.error(f"거래 전략 초기화 오류: {e}")
    
    async def start(self):
        """거래 엔진 시작"""
        if self.is_running:
            self.logger.warning("거래 엔진이 이미 실행 중입니다")
            return
        
        try:
            self.logger.info("=== 거래 엔진 시작 ===")
            self.start_time = datetime.now()
            
            # 1. 포트폴리오 초기화
            await self.portfolio.initialize()
            self.logger.info("포트폴리오 초기화 완료")
            
            # 2. 리스크 매니저 초기화
            await self.risk_manager.initialize()
            self.logger.info("리스크 매니저 초기화 완료")
            
            # 3. 주문 매니저 초기화
            await self.order_manager.initialize()
            self.logger.info("주문 매니저 초기화 완료")
            
            # 4. WebSocket 연결 시작
            if self.target_markets:
                self.websocket_client = UpbitWebSocketClient(
                    tickers=self.target_markets,
                    callback=self._on_market_data
                )
                
                # WebSocket 연결을 별도 태스크로 실행
                self._websocket_task = asyncio.create_task(self.websocket_client.connect())
                self.logger.info(f"WebSocket 연결 시작: {self.target_markets}")
            
            # 5. 텔레그램 알림
            if settings.TELEGRAM_NOTIFICATIONS_ENABLED:
                await self.telegram_notifier.send_system_notification(
                    f"🚀 거래 엔진 시작\n"
                    f"모드: {self.trading_mode}\n"
                    f"전략: {len(strategy_manager.get_enabled_strategies())}개\n"
                    f"대상 마켓: {', '.join(self.target_markets)}"
                )
            
            self.is_running = True
            self.logger.info("거래 엔진 시작 완료 ✅")
            
        except Exception as e:
            self.logger.error(f"거래 엔진 시작 오류: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """거래 엔진 중지"""
        if not self.is_running:
            return
        
        try:
            self.logger.info("=== 거래 엔진 중지 ===")
            
            self.is_running = False
            
            # 1. WebSocket 연결 해제
            if self.websocket_client:
                await self.websocket_client.disconnect()
                self.logger.info("WebSocket 연결 해제 완료")
            
            # 2. 진행 중인 주문 정리
            await self.order_manager.cleanup()
            self.logger.info("주문 매니저 정리 완료")
            
            # 3. 최종 성과 리포트 생성
            await self._generate_final_report()
            
            # 4. 텔레그램 알림
            if settings.TELEGRAM_NOTIFICATIONS_ENABLED:
                runtime = datetime.now() - self.start_time if self.start_time else timedelta()
                await self.telegram_notifier.send_system_notification(
                    f"🛑 거래 엔진 중지\n"
                    f"실행 시간: {str(runtime).split('.')[0]}\n"
                    f"총 신호: {self.total_signals}\n"
                    f"성공 거래: {self.successful_trades}\n"
                    f"실패 거래: {self.failed_trades}"
                )
            
            self.logger.info("거래 엔진 중지 완료 ✅")
            
        except Exception as e:
            self.logger.error(f"거래 엔진 중지 오류: {e}")
    
    async def _on_market_data(self, data: Dict[str, Any]):
        """시장 데이터 수신 시 콜백"""
        if not self.is_running:
            return
        
        try:
            ticker = data.get('code', '')
            trade_price = data.get('trade_price', 0)
            
            # 거래 비활성화 상태면 로깅만
            if not self.is_trading_enabled:
                self.logger.debug(f"거래 비활성화 - 데이터만 수신: {ticker} @ {trade_price:,.0f}")
                return
            
            # 각 전략에 대해 신호 확인
            enabled_strategies = strategy_manager.get_enabled_strategies()
            
            for strategy_name, strategy in enabled_strategies.items():
                try:
                    await self._process_strategy_signals(strategy, data)
                except Exception as e:
                    self.logger.error(f"전략 처리 오류 ({strategy_name}): {e}")
                    
        except Exception as e:
            self.logger.error(f"시장 데이터 처리 오류: {e}")
    
    async def _process_strategy_signals(self, strategy: BaseStrategy, data: Dict[str, Any]):
        """전략 신호 처리"""
        ticker = data.get('code', '')
        current_price = data.get('trade_price', 0)
        
        # 매수 신호 확인
        if await strategy.should_buy(data):
            self.total_signals += 1
            await self._handle_buy_signal(strategy, ticker, current_price, data)
        
        # 매도 신호 확인 (기존 포지션이 있는 경우)
        position = await self.portfolio.get_position(ticker)
        if position and position.get('volume', 0) > 0:
            if await strategy.should_sell(data, position):
                self.total_signals += 1
                await self._handle_sell_signal(strategy, ticker, current_price, position, data)
    
    async def _handle_buy_signal(self, strategy: BaseStrategy, ticker: str, 
                               current_price: float, market_data: Dict[str, Any]):
        """매수 신호 처리"""
        try:
            self.logger.info(f"매수 신호 감지: {ticker} @ {current_price:,.0f} (전략: {strategy.name})")
            
            # 1. 리스크 검증
            if not await self.risk_manager.validate_buy_order(ticker, current_price):
                self.logger.warning(f"리스크 검증 실패: {ticker}")
                return
            
            # 2. 사용 가능한 잔고 확인
            available_balance = await self.portfolio.get_available_balance()
            if available_balance < settings.MIN_ORDER_AMOUNT:
                self.logger.warning(f"잔고 부족: {available_balance:,.0f} < {settings.MIN_ORDER_AMOUNT:,.0f}")
                return
            
            # 3. 포지션 크기 계산
            position_size = await strategy.calculate_position_size(market_data, available_balance)
            position_size = min(position_size, settings.MAX_POSITION_SIZE)
            
            if position_size < settings.MIN_ORDER_AMOUNT:
                self.logger.warning(f"주문 금액 부족: {position_size:,.0f}")
                return
            
            # 4. 주문 실행
            order_result = await self.order_manager.place_buy_order(
                ticker=ticker,
                amount=position_size,
                strategy=strategy.name
            )
            
            if order_result:
                self.successful_trades += 1
                await self._handle_successful_trade('buy', order_result, strategy.name)
            else:
                self.failed_trades += 1
                self.logger.error(f"매수 주문 실패: {ticker}")
                
        except Exception as e:
            self.failed_trades += 1
            self.logger.error(f"매수 신호 처리 오류: {e}")
    
    async def _handle_sell_signal(self, strategy: BaseStrategy, ticker: str, 
                                current_price: float, position: Dict[str, Any], 
                                market_data: Dict[str, Any]):
        """매도 신호 처리"""
        try:
            volume = position.get('volume', 0)
            self.logger.info(f"매도 신호 감지: {ticker} @ {current_price:,.0f} (수량: {volume:.6f}, 전략: {strategy.name})")
            
            # 1. 리스크 검증
            if not await self.risk_manager.validate_sell_order(ticker, volume):
                self.logger.warning(f"매도 리스크 검증 실패: {ticker}")
                return
            
            # 2. 주문 실행
            order_result = await self.order_manager.place_sell_order(
                ticker=ticker,
                volume=volume,
                strategy=strategy.name
            )
            
            if order_result:
                self.successful_trades += 1
                await self._handle_successful_trade('sell', order_result, strategy.name)
            else:
                self.failed_trades += 1
                self.logger.error(f"매도 주문 실패: {ticker}")
                
        except Exception as e:
            self.failed_trades += 1
            self.logger.error(f"매도 신호 처리 오류: {e}")
    
    async def _handle_successful_trade(self, side: str, order_result: Dict[str, Any], strategy_name: str):
        """성공한 거래 처리"""
        try:
            # 1. 거래 데이터 준비
            trade_data = {
                'market': order_result.get('market'),
                'side': side,
                'price': float(order_result.get('price', 0)),
                'volume': float(order_result.get('volume', 0)),
                'amount': float(order_result.get('price', 0)) * float(order_result.get('volume', 0)),
                'strategy': strategy_name,
                'order_type': 'market',
                'upbit_uuid': order_result.get('uuid'),
                'timestamp': datetime.now()
            }
            
            # 2. 데이터베이스에 저장
            await self.trade_repository.create_trade(trade_data)
            
            # 3. 포트폴리오 업데이트
            await self.portfolio.update_position(order_result)
            
            # 4. 텔레그램 알림 발송
            if settings.TELEGRAM_NOTIFICATIONS_ENABLED:
                await self.telegram_notifier.send_trade_notification(trade_data)
            
            # 5. 성과 추적 업데이트
            await self.risk_manager.update_performance_tracking(trade_data)
            
            self.logger.info(
                f"거래 완료 처리: {side.upper()} {trade_data['market']} "
                f"가격: {trade_data['price']:,.0f} 수량: {trade_data['volume']:.6f} "
                f"금액: {trade_data['amount']:,.0f}"
            )
            
        except Exception as e:
            self.logger.error(f"거래 완료 처리 오류: {e}")
    
    async def _generate_final_report(self):
        """최종 성과 리포트 생성"""
        try:
            if not self.start_time:
                return
            
            runtime = datetime.now() - self.start_time
            
            # 포트폴리오 정보
            portfolio_info = await self.portfolio.get_portfolio_summary()
            
            # 전략별 통계
            strategy_stats = strategy_manager.get_manager_statistics()
            
            # 리스크 매니저 통계
            risk_stats = await self.risk_manager.get_statistics()
            
            report = {
                'session_info': {
                    'start_time': self.start_time.isoformat(),
                    'end_time': datetime.now().isoformat(),
                    'runtime_seconds': runtime.total_seconds(),
                    'trading_mode': self.trading_mode,
                },
                'trading_stats': {
                    'total_signals': self.total_signals,
                    'successful_trades': self.successful_trades,
                    'failed_trades': self.failed_trades,
                    'success_rate': (self.successful_trades / max(self.total_signals, 1)) * 100,
                },
                'portfolio_info': portfolio_info,
                'strategy_stats': strategy_stats,
                'risk_stats': risk_stats,
            }
            
            self.logger.info(f"세션 완료 리포트: {report}")
            
            return report
            
        except Exception as e:
            self.logger.error(f"최종 리포트 생성 오류: {e}")
            return None
    
    # 운영 관리 메서드들
    
    async def enable_trading(self):
        """거래 활성화"""
        self.is_trading_enabled = True
        self.logger.info("거래 활성화됨")
        
        if settings.TELEGRAM_NOTIFICATIONS_ENABLED:
            await self.telegram_notifier.send_system_notification("✅ 거래 활성화")
    
    async def disable_trading(self):
        """거래 비활성화"""
        self.is_trading_enabled = False
        self.logger.info("거래 비활성화됨")
        
        if settings.TELEGRAM_NOTIFICATIONS_ENABLED:
            await self.telegram_notifier.send_system_notification("⏸️ 거래 비활성화")
    
    async def add_market(self, market: str):
        """거래 마켓 추가"""
        if market not in self.target_markets:
            self.target_markets.append(market)
            self.logger.info(f"거래 마켓 추가: {market}")
            
            # WebSocket 재연결 필요
            if self.websocket_client and self.is_running:
                await self.websocket_client.disconnect()
                self.websocket_client = UpbitWebSocketClient(
                    tickers=self.target_markets,
                    callback=self._on_market_data
                )
                self._websocket_task = asyncio.create_task(self.websocket_client.connect())
    
    async def remove_market(self, market: str):
        """거래 마켓 제거"""
        if market in self.target_markets:
            self.target_markets.remove(market)
            self.logger.info(f"거래 마켓 제거: {market}")
            
            # 해당 마켓의 포지션이 있으면 경고
            position = await self.portfolio.get_position(market)
            if position and position.get('volume', 0) > 0:
                self.logger.warning(f"포지션이 있는 마켓 제거: {market}")
    
    def get_engine_status(self) -> Dict[str, Any]:
        """엔진 상태 반환"""
        runtime = datetime.now() - self.start_time if self.start_time else None
        
        return {
            'is_running': self.is_running,
            'is_trading_enabled': self.is_trading_enabled,
            'trading_mode': self.trading_mode,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'runtime_seconds': runtime.total_seconds() if runtime else 0,
            'target_markets': self.target_markets,
            'websocket_connected': self.websocket_client is not None,
            'statistics': {
                'total_signals': self.total_signals,
                'successful_trades': self.successful_trades,
                'failed_trades': self.failed_trades,
                'success_rate': (self.successful_trades / max(self.total_signals, 1)) * 100,
            },
            'strategies': {
                name: strategy.get_statistics() 
                for name, strategy in strategy_manager.get_all_strategies().items()
            }
        }
