"""
CoinTrader Upbit API 클라이언트
Upbit API 연동 및 거래 실행
"""
import pyupbit
import asyncio
import aiohttp
import time
from typing import Dict, List, Optional, Any
from decimal import Decimal
import logging
from datetime import datetime, timedelta

from ..config import settings
from ..utils.logger import setup_logger, log_trade, log_error

class UpbitAPIError(Exception):
    """Upbit API 관련 오류"""
    pass

class UpbitRateLimitError(UpbitAPIError):
    """Rate Limit 오류"""
    pass

class UpbitClient:
    """Upbit API 클라이언트"""
    
    def __init__(self):
        self.access_key = settings.UPBIT_ACCESS_KEY
        self.secret_key = settings.UPBIT_SECRET_KEY
        self.server_url = settings.UPBIT_SERVER_URL
        
        # pyupbit 클라이언트 (동기)
        if self.access_key and self.secret_key:
            self.upbit = pyupbit.Upbit(self.access_key, self.secret_key)
        else:
            self.upbit = None
            
        self.logger = setup_logger("upbit.client")
        
        # Rate limiting
        self.last_request_time = 0
        self.request_count = 0
        self.request_window_start = time.time()
        
        # 요청 제한 (Upbit API 기준)
        self.max_requests_per_second = 8
        self.max_requests_per_minute = 200
        
    def _check_rate_limit(self):
        """Rate limit 확인"""
        current_time = time.time()
        
        # 1분 윈도우 리셋
        if current_time - self.request_window_start >= 60:
            self.request_count = 0
            self.request_window_start = current_time
        
        # 1분당 요청 수 제한
        if self.request_count >= self.max_requests_per_minute:
            raise UpbitRateLimitError("분당 요청 한도 초과")
        
        # 초당 요청 수 제한
        time_since_last = current_time - self.last_request_time
        if time_since_last < (1.0 / self.max_requests_per_second):
            sleep_time = (1.0 / self.max_requests_per_second) - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
    
    def _handle_api_error(self, func_name: str, error: Exception):
        """API 오류 처리"""
        error_msg = str(error)
        
        if "Too Many Requests" in error_msg:
            raise UpbitRateLimitError(f"{func_name}: Rate limit exceeded")
        elif "Invalid access key" in error_msg:
            raise UpbitAPIError(f"{func_name}: Invalid API credentials")
        elif "Insufficient funds" in error_msg:
            raise UpbitAPIError(f"{func_name}: Insufficient funds")
        else:
            raise UpbitAPIError(f"{func_name}: {error_msg}")
    
    # ===========================================
    # 계좌 관련 메서드
    # ===========================================
    
    def get_balances(self) -> List[Dict[str, Any]]:
        """계좌 잔고 조회"""
        if not self.upbit:
            raise UpbitAPIError("API 인증 정보가 설정되지 않았습니다")
        
        try:
            self._check_rate_limit()
            balances = self.upbit.get_balances()
            
            if not balances:
                return []
            
            # 데이터 정규화
            result = []
            for balance in balances:
                result.append({
                    'currency': balance['currency'],
                    'balance': float(balance['balance']),
                    'locked': float(balance['locked']),
                    'avg_buy_price': float(balance.get('avg_buy_price', 0)),
                    'avg_buy_price_modified': balance.get('avg_buy_price_modified', False),
                    'unit_currency': balance['unit_currency']
                })
            
            self.logger.debug(f"잔고 조회 완료: {len(result)}개 항목")
            return result
            
        except Exception as e:
            log_error(e, "잔고 조회 실패")
            self._handle_api_error("get_balances", e)
    
    def get_balance(self, currency: str = "KRW") -> float:
        """특정 통화 잔고 조회"""
        balances = self.get_balances()
        
        for balance in balances:
            if balance['currency'] == currency:
                return balance['balance']
        
        return 0.0
    
    # ===========================================
    # 시장 데이터 조회 메서드
    # ===========================================
    
    def get_current_price(self, ticker: str) -> Optional[float]:
        """현재가 조회"""
        try:
            self._check_rate_limit()
            price = pyupbit.get_current_price(ticker)
            
            if price is None:
                self.logger.warning(f"현재가 조회 실패: {ticker}")
                return None
            
            self.logger.debug(f"현재가 조회: {ticker} = {price:,.0f}")
            return float(price)
            
        except Exception as e:
            log_error(e, f"현재가 조회 실패: {ticker}")
            return None
    
    def get_current_prices(self, tickers: List[str]) -> Dict[str, float]:
        """여러 종목 현재가 조회"""
        try:
            self._check_rate_limit()
            prices = pyupbit.get_current_price(tickers)
            
            if not prices:
                return {}
            
            # None 값 제거
            result = {k: float(v) for k, v in prices.items() if v is not None}
            
            self.logger.debug(f"현재가 조회: {len(result)}개 종목")
            return result
            
        except Exception as e:
            log_error(e, f"현재가 조회 실패: {tickers}")
            return {}
    
    def get_orderbook(self, ticker: str) -> Optional[Dict[str, Any]]:
        """호가 정보 조회"""
        try:
            self._check_rate_limit()
            orderbook = pyupbit.get_orderbook(ticker)
            
            if not orderbook:
                return None
            
            return {
                'market': orderbook[0]['market'],
                'timestamp': orderbook[0]['timestamp'],
                'total_ask_size': orderbook[0]['total_ask_size'],
                'total_bid_size': orderbook[0]['total_bid_size'],
                'orderbook_units': orderbook[0]['orderbook_units']
            }
            
        except Exception as e:
            log_error(e, f"호가 조회 실패: {ticker}")
            return None
    
    def get_market_all(self) -> List[Dict[str, str]]:
        """마켓 코드 조회"""
        try:
            self._check_rate_limit()
            markets = pyupbit.get_tickers()
            
            if not markets:
                return []
            
            # KRW 마켓만 필터링
            krw_markets = [
                {'market': market, 'korean_name': '', 'english_name': ''}
                for market in markets if market.startswith('KRW-')
            ]
            
            self.logger.debug(f"마켓 조회: {len(krw_markets)}개 KRW 마켓")
            return krw_markets
            
        except Exception as e:
            log_error(e, "마켓 조회 실패")
            return []
    
    # ===========================================
    # 주문 관련 메서드
    # ===========================================
    
    def buy_market_order(self, ticker: str, price: float) -> Optional[Dict[str, Any]]:
        """시장가 매수 주문"""
        if not self.upbit:
            raise UpbitAPIError("API 인증 정보가 설정되지 않았습니다")
        
        if settings.TRADING_MODE == "paper":
            # 모의거래 모드
            return self._simulate_order(ticker, "bid", "market", price=price)
        
        try:
            self._check_rate_limit()
            
            # 최소 주문 금액 확인
            if price < settings.MIN_ORDER_AMOUNT:
                raise UpbitAPIError(f"최소 주문 금액 미달: {price:,.0f}원 < {settings.MIN_ORDER_AMOUNT:,.0f}원")
            
            result = self.upbit.buy_market_order(ticker, price)
            
            if result:
                # 거래 로그 기록
                log_trade(
                    side="buy",
                    market=ticker,
                    price=0,  # 시장가는 체결가가 나중에 결정됨
                    volume=0,
                    amount=price,
                    strategy="manual",
                    order_type="market",
                    upbit_uuid=result.get('uuid')
                )
                
                self.logger.info(f"매수 주문 완료: {ticker} {price:,.0f}원")
                
                return {
                    'uuid': result['uuid'],
                    'side': result['side'],
                    'ord_type': result['ord_type'],
                    'price': result.get('price', 0),
                    'state': result['state'],
                    'market': result['market'],
                    'created_at': result['created_at'],
                    'volume': result.get('volume', 0),
                    'remaining_volume': result.get('remaining_volume', 0),
                    'reserved_fee': result.get('reserved_fee', 0),
                    'remaining_fee': result.get('remaining_fee', 0),
                    'paid_fee': result.get('paid_fee', 0),
                    'locked': result.get('locked', 0),
                    'executed_volume': result.get('executed_volume', 0),
                    'trades_count': result.get('trades_count', 0)
                }
            
            return None
            
        except Exception as e:
            log_error(e, f"매수 주문 실패: {ticker} {price:,.0f}원")
            self._handle_api_error("buy_market_order", e)
    
    def sell_market_order(self, ticker: str, volume: float) -> Optional[Dict[str, Any]]:
        """시장가 매도 주문"""
        if not self.upbit:
            raise UpbitAPIError("API 인증 정보가 설정되지 않았습니다")
        
        if settings.TRADING_MODE == "paper":
            # 모의거래 모드
            current_price = self.get_current_price(ticker)
            if current_price:
                amount = volume * current_price
                return self._simulate_order(ticker, "ask", "market", volume=volume, amount=amount)
            return None
        
        try:
            self._check_rate_limit()
            
            result = self.upbit.sell_market_order(ticker, volume)
            
            if result:
                # 거래 로그 기록
                log_trade(
                    side="sell",
                    market=ticker,
                    price=0,  # 시장가는 체결가가 나중에 결정됨
                    volume=volume,
                    amount=0,  # 시장가는 체결금액이 나중에 결정됨
                    strategy="manual",
                    order_type="market",
                    upbit_uuid=result.get('uuid')
                )
                
                self.logger.info(f"매도 주문 완료: {ticker} {volume:.6f}")
                
                return {
                    'uuid': result['uuid'],
                    'side': result['side'],
                    'ord_type': result['ord_type'],
                    'price': result.get('price', 0),
                    'state': result['state'],
                    'market': result['market'],
                    'created_at': result['created_at'],
                    'volume': result.get('volume', 0),
                    'remaining_volume': result.get('remaining_volume', 0),
                    'reserved_fee': result.get('reserved_fee', 0),
                    'remaining_fee': result.get('remaining_fee', 0),
                    'paid_fee': result.get('paid_fee', 0),
                    'locked': result.get('locked', 0),
                    'executed_volume': result.get('executed_volume', 0),
                    'trades_count': result.get('trades_count', 0)
                }
            
            return None
            
        except Exception as e:
            log_error(e, f"매도 주문 실패: {ticker} {volume:.6f}")
            self._handle_api_error("sell_market_order", e)
    
    def buy_limit_order(self, ticker: str, price: float, volume: float) -> Optional[Dict[str, Any]]:
        """지정가 매수 주문"""
        if not self.upbit:
            raise UpbitAPIError("API 인증 정보가 설정되지 않았습니다")
        
        if settings.TRADING_MODE == "paper":
            # 모의거래 모드
            amount = price * volume
            return self._simulate_order(ticker, "bid", "limit", price=price, volume=volume, amount=amount)
        
        try:
            self._check_rate_limit()
            
            result = self.upbit.buy_limit_order(ticker, price, volume)
            
            if result:
                log_trade(
                    side="buy",
                    market=ticker,
                    price=price,
                    volume=volume,
                    amount=price * volume,
                    strategy="manual",
                    order_type="limit",
                    upbit_uuid=result.get('uuid')
                )
                
                self.logger.info(f"지정가 매수 주문 완료: {ticker} {price:,.0f}원 x {volume:.6f}")
                return result
            
            return None
            
        except Exception as e:
            log_error(e, f"지정가 매수 주문 실패: {ticker} {price:,.0f}원 x {volume:.6f}")
            self._handle_api_error("buy_limit_order", e)
    
    def sell_limit_order(self, ticker: str, price: float, volume: float) -> Optional[Dict[str, Any]]:
        """지정가 매도 주문"""
        if not self.upbit:
            raise UpbitAPIError("API 인증 정보가 설정되지 않았습니다")
        
        if settings.TRADING_MODE == "paper":
            # 모의거래 모드
            amount = price * volume
            return self._simulate_order(ticker, "ask", "limit", price=price, volume=volume, amount=amount)
        
        try:
            self._check_rate_limit()
            
            result = self.upbit.sell_limit_order(ticker, price, volume)
            
            if result:
                log_trade(
                    side="sell",
                    market=ticker,
                    price=price,
                    volume=volume,
                    amount=price * volume,
                    strategy="manual",
                    order_type="limit",
                    upbit_uuid=result.get('uuid')
                )
                
                self.logger.info(f"지정가 매도 주문 완료: {ticker} {price:,.0f}원 x {volume:.6f}")
                return result
            
            return None
            
        except Exception as e:
            log_error(e, f"지정가 매도 주문 실패: {ticker} {price:,.0f}원 x {volume:.6f}")
            self._handle_api_error("sell_limit_order", e)
    
    def cancel_order(self, uuid: str) -> Optional[Dict[str, Any]]:
        """주문 취소"""
        if not self.upbit:
            raise UpbitAPIError("API 인증 정보가 설정되지 않았습니다")
        
        try:
            self._check_rate_limit()
            
            result = self.upbit.cancel_order(uuid)
            
            if result:
                self.logger.info(f"주문 취소 완료: {uuid}")
                return result
            
            return None
            
        except Exception as e:
            log_error(e, f"주문 취소 실패: {uuid}")
            self._handle_api_error("cancel_order", e)
    
    def get_order(self, uuid: str) -> Optional[Dict[str, Any]]:
        """주문 상세 조회"""
        if not self.upbit:
            raise UpbitAPIError("API 인증 정보가 설정되지 않았습니다")
        
        try:
            self._check_rate_limit()
            
            result = self.upbit.get_order(uuid)
            
            if result:
                self.logger.debug(f"주문 조회 완료: {uuid}")
                return result
            
            return None
            
        except Exception as e:
            log_error(e, f"주문 조회 실패: {uuid}")
            self._handle_api_error("get_order", e)
    
    def get_orders(self, market: str = None, state: str = "wait", limit: int = 100) -> List[Dict[str, Any]]:
        """주문 목록 조회"""
        if not self.upbit:
            raise UpbitAPIError("API 인증 정보가 설정되지 않았습니다")
        
        try:
            self._check_rate_limit()
            
            orders = self.upbit.get_orders(market=market, state=state)
            
            if not orders:
                return []
            
            # 제한된 수만 반환
            result = orders[:limit] if limit else orders
            
            self.logger.debug(f"주문 목록 조회: {len(result)}개")
            return result
            
        except Exception as e:
            log_error(e, "주문 목록 조회 실패")
            self._handle_api_error("get_orders", e)
    
    # ===========================================
    # 모의거래 메서드
    # ===========================================
    
    def _simulate_order(self, ticker: str, side: str, ord_type: str, 
                       price: float = 0, volume: float = 0, amount: float = 0) -> Dict[str, Any]:
        """모의거래 주문 시뮬레이션"""
        import uuid
        from datetime import datetime
        
        # 현재가 조회
        if not price and side == "ask":
            current_price = self.get_current_price(ticker)
            if current_price:
                price = current_price
                amount = price * volume
        
        # 시뮬레이션 결과 생성
        order_uuid = str(uuid.uuid4())
        
        result = {
            'uuid': order_uuid,
            'side': side,
            'ord_type': ord_type,
            'price': str(price) if price else "0",
            'state': 'done',  # 모의거래에서는 즉시 체결
            'market': ticker,
            'created_at': datetime.now().isoformat(),
            'volume': str(volume) if volume else "0",
            'remaining_volume': "0",
            'reserved_fee': "0",
            'remaining_fee': "0", 
            'paid_fee': str(amount * 0.0005) if amount else "0",  # 0.05% 수수료
            'locked': "0",
            'executed_volume': str(volume) if volume else "0",
            'trades_count': 1,
            'simulated': True  # 모의거래 표시
        }
        
        self.logger.info(f"[모의거래] {side.upper()} {ticker} - 가격: {price:,.0f}, 수량: {volume:.6f}")
        
        return result
    
    # ===========================================
    # 유틸리티 메서드
    # ===========================================
    
    def is_authenticated(self) -> bool:
        """API 인증 상태 확인"""
        return bool(self.access_key and self.secret_key and self.upbit)
    
    def get_api_info(self) -> Dict[str, Any]:
        """API 정보 조회"""
        return {
            "authenticated": self.is_authenticated(),
            "trading_mode": settings.TRADING_MODE,
            "server_url": self.server_url,
            "rate_limit": {
                "requests_per_second": self.max_requests_per_second,
                "requests_per_minute": self.max_requests_per_minute,
                "current_count": self.request_count
            }
        }

# 전역 Upbit 클라이언트 인스턴스
upbit_client = UpbitClient()

