"""
CoinTrader 주문 관리자
주문 실행, 추적, 관리를 담당하는 모듈
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import asyncio
from enum import Enum

from ..config import settings
from ..upbit.client import UpbitClient
from ..telegram.notifications import TelegramNotifier
from ..utils.logger import setup_logger

class OrderStatus(Enum):
    """주문 상태"""
    PENDING = "pending"      # 대기 중
    SUBMITTED = "submitted"  # 제출됨
    FILLED = "filled"        # 체결됨
    CANCELLED = "cancelled"  # 취소됨
    FAILED = "failed"        # 실패

class OrderManager:
    """
    주문 관리자
    
    주요 기능:
    - 주문 생성 및 실행
    - 주문 상태 추적
    - 주문 취소 관리
    - 부분 체결 처리
    - 주문 내역 기록
    """
    
    def __init__(self, upbit_client: UpbitClient, telegram_notifier: Optional[TelegramNotifier] = None):
        self.logger = setup_logger("order.manager")
        self.upbit_client = upbit_client
        self.telegram_notifier = telegram_notifier
        
        # 활성 주문 추적
        self.active_orders = {}  # uuid -> order_info
        self.order_history = []  # 주문 내역
        
        # 설정
        self.order_timeout = 300  # 5분 주문 타임아웃
        self.max_retry_count = 3  # 최대 재시도 횟수
        self.min_order_amount = settings.MIN_ORDER_AMOUNT
        
        # 통계
        self.total_orders = 0
        self.successful_orders = 0
        self.failed_orders = 0
        self.cancelled_orders = 0
        
        self.logger.info("주문 매니저 초기화 완료")
    
    async def initialize(self):
        """주문 매니저 초기화"""
        try:
            # 기존 미체결 주문 확인
            await self._check_pending_orders()
            
            # 주문 모니터링 태스크 시작
            self._monitor_task = asyncio.create_task(self._monitor_orders())
            
            self.logger.info("주문 매니저 초기화 완료")
            
        except Exception as e:
            self.logger.error(f"주문 매니저 초기화 오류: {e}")
            raise
    
    async def place_buy_order(self, ticker: str, amount: float, 
                            strategy: str = "unknown", order_type: str = "market") -> Optional[Dict[str, Any]]:
        """
        매수 주문 실행
        
        Args:
            ticker: 거래 종목 (예: KRW-BTC)
            amount: 주문 금액 (KRW)
            strategy: 사용된 전략명
            order_type: 주문 타입 (market/limit)
            
        Returns:
            Optional[Dict]: 주문 결과 또는 None
        """
        try:
            self.logger.info(f"매수 주문 실행 시작: {ticker} - {amount:,.0f}원 ({strategy})")
            
            # 1. 주문 검증
            if not await self._validate_order(ticker, amount, "buy"):
                return None
            
            # 2. 주문 생성
            order_info = await self._create_order_info(ticker, amount, "buy", strategy, order_type)
            
            # 3. 실제 주문 실행
            if settings.TRADING_MODE == "paper":
                # 모의거래 모드
                result = await self._execute_paper_order(order_info)
            else:
                # 실거래 모드
                result = await self._execute_live_order(order_info)
            
            if result:
                # 4. 주문 등록 및 추적
                await self._register_order(result, order_info)
                
                # 5. 성공 통계 업데이트
                self.successful_orders += 1
                
                self.logger.info(f"매수 주문 성공: {ticker} - UUID: {result.get('uuid')}")
                return result
            else:
                self.failed_orders += 1
                self.logger.error(f"매수 주문 실패: {ticker}")
                return None
                
        except Exception as e:
            self.failed_orders += 1
            self.logger.error(f"매수 주문 실행 오류: {e}")
            return None
    
    async def place_sell_order(self, ticker: str, volume: float, 
                             strategy: str = "unknown", order_type: str = "market") -> Optional[Dict[str, Any]]:
        """
        매도 주문 실행
        
        Args:
            ticker: 거래 종목
            volume: 매도 수량
            strategy: 사용된 전략명
            order_type: 주문 타입
            
        Returns:
            Optional[Dict]: 주문 결과 또는 None
        """
        try:
            self.logger.info(f"매도 주문 실행 시작: {ticker} - {volume:.6f} ({strategy})")
            
            # 1. 주문 검증
            if not await self._validate_sell_order(ticker, volume):
                return None
            
            # 2. 주문 생성
            order_info = await self._create_order_info(ticker, volume, "sell", strategy, order_type)
            
            # 3. 실제 주문 실행
            if settings.TRADING_MODE == "paper":
                # 모의거래 모드
                result = await self._execute_paper_order(order_info)
            else:
                # 실거래 모드
                result = await self._execute_live_order(order_info)
            
            if result:
                # 4. 주문 등록 및 추적
                await self._register_order(result, order_info)
                
                # 5. 성공 통계 업데이트
                self.successful_orders += 1
                
                self.logger.info(f"매도 주문 성공: {ticker} - UUID: {result.get('uuid')}")
                return result
            else:
                self.failed_orders += 1
                self.logger.error(f"매도 주문 실패: {ticker}")
                return None
                
        except Exception as e:
            self.failed_orders += 1
            self.logger.error(f"매도 주문 실행 오류: {e}")
            return None
    
    async def cancel_order(self, order_uuid: str, reason: str = "manual") -> bool:
        """
        주문 취소
        
        Args:
            order_uuid: 주문 UUID
            reason: 취소 사유
            
        Returns:
            bool: 취소 성공 여부
        """
        try:
            self.logger.info(f"주문 취소 시작: {order_uuid} - 사유: {reason}")
            
            # 1. 활성 주문 확인
            if order_uuid not in self.active_orders:
                self.logger.warning(f"활성 주문 아님: {order_uuid}")
                return False
            
            order_info = self.active_orders[order_uuid]
            
            # 2. 실제 취소 실행
            if settings.TRADING_MODE == "paper":
                # 모의거래 모드
                cancel_result = True
            else:
                # 실거래 모드
                cancel_result = await self._cancel_live_order(order_uuid)
            
            if cancel_result:
                # 3. 주문 상태 업데이트
                order_info['status'] = OrderStatus.CANCELLED.value
                order_info['cancelled_at'] = datetime.now()
                order_info['cancel_reason'] = reason
                
                # 4. 활성 주문에서 제거
                del self.active_orders[order_uuid]
                
                # 5. 히스토리에 추가
                self.order_history.append(order_info)
                
                # 6. 통계 업데이트
                self.cancelled_orders += 1
                
                self.logger.info(f"주문 취소 성공: {order_uuid}")
                return True
            else:
                self.logger.error(f"주문 취소 실패: {order_uuid}")
                return False
                
        except Exception as e:
            self.logger.error(f"주문 취소 오류: {e}")
            return False
    
    async def get_order_status(self, order_uuid: str) -> Optional[Dict[str, Any]]:
        """주문 상태 조회"""
        try:
            # 1. 활성 주문에서 확인
            if order_uuid in self.active_orders:
                return self.active_orders[order_uuid]
            
            # 2. 히스토리에서 확인
            for order in self.order_history:
                if order.get('uuid') == order_uuid:
                    return order
            
            # 3. Upbit에서 직접 조회
            if settings.TRADING_MODE == "live":
                upbit_result = await self.upbit_client.get_order_status(order_uuid)
                if upbit_result:
                    return self._convert_upbit_order(upbit_result)
            
            return None
            
        except Exception as e:
            self.logger.error(f"주문 상태 조회 오류: {e}")
            return None
    
    async def _validate_order(self, ticker: str, amount: float, side: str) -> bool:
        """주문 검증"""
        try:
            # 1. 기본 검증
            if not ticker or amount <= 0:
                return False
            
            # 2. 최소 주문 금액 확인
            if amount < self.min_order_amount:
                self.logger.warning(f"최소 주문 금액 미달: {amount:,.0f} < {self.min_order_amount:,.0f}")
                return False
            
            # 3. 마켓 상태 확인
            # 실제 구현에서는 Upbit에서 마켓 정보 확인
            
            return True
            
        except Exception as e:
            self.logger.error(f"주문 검증 오류: {e}")
            return False
    
    async def _validate_sell_order(self, ticker: str, volume: float) -> bool:
        """매도 주문 검증"""
        try:
            # 1. 기본 검증
            if not ticker or volume <= 0:
                return False
            
            # 2. 보유 수량 확인
            balances = await self.upbit_client.get_balances()
            if balances:
                for balance in balances:
                    if balance.get('currency') == ticker.split('-')[1]:
                        available_volume = float(balance.get('balance', 0))
                        if volume > available_volume:
                            self.logger.warning(f"수량 부족: {ticker} - 요청: {volume}, 보유: {available_volume}")
                            return False
                        break
                else:
                    self.logger.warning(f"보유하지 않은 종목: {ticker}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"매도 주문 검증 오류: {e}")
            return False
    
    async def _create_order_info(self, ticker: str, amount_or_volume: float, 
                               side: str, strategy: str, order_type: str) -> Dict[str, Any]:
        """주문 정보 생성"""
        order_info = {
            'ticker': ticker,
            'side': side,
            'order_type': order_type,
            'strategy': strategy,
            'created_at': datetime.now(),
            'status': OrderStatus.PENDING.value,
            'retry_count': 0
        }
        
        if side == "buy":
            order_info['amount'] = amount_or_volume
        else:
            order_info['volume'] = amount_or_volume
        
        return order_info
    
    async def _execute_live_order(self, order_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """실거래 주문 실행"""
        try:
            ticker = order_info['ticker']
            side = order_info['side']
            order_type = order_info['order_type']
            
            if side == "buy":
                amount = order_info['amount']
                if order_type == "market":
                    result = await self.upbit_client.buy_market_order(ticker, amount)
                else:
                    # 지정가 주문 구현 필요
                    result = None
            else:
                volume = order_info['volume']
                if order_type == "market":
                    result = await self.upbit_client.sell_market_order(ticker, volume)
                else:
                    # 지정가 주문 구현 필요
                    result = None
            
            return result
            
        except Exception as e:
            self.logger.error(f"실거래 주문 실행 오류: {e}")
            return None
    
    async def _execute_paper_order(self, order_info: Dict[str, Any]) -> Dict[str, Any]:
        """모의거래 주문 실행"""
        try:
            import uuid
            
            ticker = order_info['ticker']
            side = order_info['side']
            
            # 현재가 조회
            current_price = await self.upbit_client.get_current_price(ticker)
            if not current_price:
                return None
            
            # 모의 주문 결과 생성
            order_uuid = str(uuid.uuid4())
            
            if side == "buy":
                amount = order_info['amount']
                volume = amount / current_price
                result = {
                    'uuid': order_uuid,
                    'market': ticker,
                    'side': 'bid',
                    'ord_type': 'price',
                    'price': str(amount),
                    'volume': str(volume),
                    'executed_volume': str(volume),
                    'trades_count': 1,
                    'state': 'done',
                    'created_at': datetime.now().isoformat(),
                    'paper_trade': True
                }
            else:
                volume = order_info['volume']
                amount = volume * current_price
                result = {
                    'uuid': order_uuid,
                    'market': ticker,
                    'side': 'ask',
                    'ord_type': 'market',
                    'price': str(current_price),
                    'volume': str(volume),
                    'executed_volume': str(volume),
                    'trades_count': 1,
                    'state': 'done',
                    'created_at': datetime.now().isoformat(),
                    'paper_trade': True
                }
            
            self.logger.info(f"모의거래 주문 생성: {ticker} {side} - {result['uuid']}")
            return result
            
        except Exception as e:
            self.logger.error(f"모의거래 주문 실행 오류: {e}")
            return None
    
    async def _cancel_live_order(self, order_uuid: str) -> bool:
        """실거래 주문 취소"""
        try:
            result = await self.upbit_client.cancel_order(order_uuid)
            return result is not None
            
        except Exception as e:
            self.logger.error(f"실거래 주문 취소 오류: {e}")
            return False
    
    async def _register_order(self, order_result: Dict[str, Any], order_info: Dict[str, Any]):
        """주문 등록 및 추적"""
        try:
            order_uuid = order_result.get('uuid')
            
            # 주문 정보 업데이트
            order_info.update({
                'uuid': order_uuid,
                'upbit_result': order_result,
                'status': OrderStatus.SUBMITTED.value,
                'submitted_at': datetime.now()
            })
            
            # 활성 주문에 추가
            self.active_orders[order_uuid] = order_info
            
            # 통계 업데이트
            self.total_orders += 1
            
            self.logger.debug(f"주문 등록 완료: {order_uuid}")
            
        except Exception as e:
            self.logger.error(f"주문 등록 오류: {e}")
    
    async def _monitor_orders(self):
        """주문 모니터링 태스크"""
        self.logger.info("주문 모니터링 시작")
        
        while True:
            try:
                await asyncio.sleep(10)  # 10초마다 확인
                
                current_time = datetime.now()
                orders_to_check = list(self.active_orders.keys())
                
                for order_uuid in orders_to_check:
                    order_info = self.active_orders.get(order_uuid)
                    if not order_info:
                        continue
                    
                    # 타임아웃 확인
                    created_at = order_info.get('created_at')
                    if created_at and (current_time - created_at).total_seconds() > self.order_timeout:
                        self.logger.warning(f"주문 타임아웃: {order_uuid}")
                        await self.cancel_order(order_uuid, "timeout")
                        continue
                    
                    # 주문 상태 업데이트
                    await self._update_order_status(order_uuid)
                
            except Exception as e:
                self.logger.error(f"주문 모니터링 오류: {e}")
                await asyncio.sleep(30)  # 오류 시 30초 대기
    
    async def _update_order_status(self, order_uuid: str):
        """주문 상태 업데이트"""
        try:
            if settings.TRADING_MODE == "paper":
                # 모의거래는 즉시 체결로 처리
                order_info = self.active_orders.get(order_uuid)
                if order_info and order_info['status'] == OrderStatus.SUBMITTED.value:
                    order_info['status'] = OrderStatus.FILLED.value
                    order_info['filled_at'] = datetime.now()
                    
                    # 활성 주문에서 제거하고 히스토리에 추가
                    del self.active_orders[order_uuid]
                    self.order_history.append(order_info)
            else:
                # 실거래는 Upbit에서 상태 확인
                upbit_status = await self.upbit_client.get_order_status(order_uuid)
                if upbit_status:
                    order_info = self.active_orders.get(order_uuid)
                    if order_info:
                        state = upbit_status.get('state')
                        
                        if state == 'done':
                            order_info['status'] = OrderStatus.FILLED.value
                            order_info['filled_at'] = datetime.now()
                            order_info['upbit_result'].update(upbit_status)
                            
                            # 활성 주문에서 제거하고 히스토리에 추가
                            del self.active_orders[order_uuid]
                            self.order_history.append(order_info)
                        elif state == 'cancel':
                            order_info['status'] = OrderStatus.CANCELLED.value
                            order_info['cancelled_at'] = datetime.now()
                            
                            # 활성 주문에서 제거하고 히스토리에 추가
                            del self.active_orders[order_uuid]
                            self.order_history.append(order_info)
            
        except Exception as e:
            self.logger.error(f"주문 상태 업데이트 오류: {e}")
    
    async def _check_pending_orders(self):
        """기존 미체결 주문 확인"""
        try:
            if settings.TRADING_MODE == "live":
                # 실거래 모드에서는 Upbit의 미체결 주문 확인
                # 실제 구현 시 추가
                pass
            
            self.logger.info("기존 미체결 주문 확인 완료")
            
        except Exception as e:
            self.logger.error(f"기존 미체결 주문 확인 오류: {e}")
    
    def _convert_upbit_order(self, upbit_order: Dict[str, Any]) -> Dict[str, Any]:
        """Upbit 주문 정보를 내부 형식으로 변환"""
        return {
            'uuid': upbit_order.get('uuid'),
            'ticker': upbit_order.get('market'),
            'side': 'buy' if upbit_order.get('side') == 'bid' else 'sell',
            'order_type': upbit_order.get('ord_type'),
            'price': float(upbit_order.get('price', 0)),
            'volume': float(upbit_order.get('volume', 0)),
            'executed_volume': float(upbit_order.get('executed_volume', 0)),
            'state': upbit_order.get('state'),
            'created_at': upbit_order.get('created_at'),
            'upbit_result': upbit_order
        }
    
    async def cleanup(self):
        """주문 매니저 정리"""
        try:
            # 모든 활성 주문 취소
            for order_uuid in list(self.active_orders.keys()):
                await self.cancel_order(order_uuid, "system_shutdown")
            
            self.logger.info("주문 매니저 정리 완료")
            
        except Exception as e:
            self.logger.error(f"주문 매니저 정리 오류: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """주문 통계 반환"""
        success_rate = (self.successful_orders / max(self.total_orders, 1)) * 100
        
        return {
            'total_orders': self.total_orders,
            'successful_orders': self.successful_orders,
            'failed_orders': self.failed_orders,
            'cancelled_orders': self.cancelled_orders,
            'success_rate': success_rate,
            'active_orders_count': len(self.active_orders),
            'order_history_count': len(self.order_history),
            'trading_mode': settings.TRADING_MODE
        }
