"""
CoinTrader Upbit WebSocket 클라이언트
실시간 시장 데이터 수신
"""
import asyncio
import json
import websockets
import uuid
from typing import Callable, List, Dict, Any, Optional
import logging
from datetime import datetime

from ..utils.logger import setup_logger, log_error, log_system_event

class UpbitWebSocketClient:
    """Upbit WebSocket 클라이언트"""
    
    def __init__(self, tickers: List[str], callback: Callable[[Dict], None]):
        self.tickers = tickers
        self.callback = callback
        self.logger = setup_logger("upbit.websocket")
        
        self.ws = None
        self.running = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5  # 초
        
        # 연결 상태
        self.connected = False
        self.last_ping = None
        self.last_message = None
        
        # 메시지 통계
        self.message_count = 0
        self.error_count = 0
        
    async def connect(self):
        """WebSocket 연결 시작"""
        uri = "wss://api.upbit.com/websocket/v1"
        
        # 구독 메시지 생성
        subscribe_message = [
            {"ticket": str(uuid.uuid4())},
            {
                "type": "ticker",
                "codes": self.tickers,
                "isOnlySnapshot": False,
                "isOnlyRealtime": True
            },
            {"format": "DEFAULT"}  # 또는 "SIMPLE"
        ]
        
        while self.running:
            try:
                self.logger.info(f"WebSocket 연결 시도: {uri}")
                log_system_event("websocket_connect_attempt", f"Connecting to {uri}")
                
                async with websockets.connect(
                    uri,
                    ping_interval=30,
                    ping_timeout=10,
                    close_timeout=10
                ) as websocket:
                    self.ws = websocket
                    self.connected = True
                    self.reconnect_attempts = 0
                    
                    # 구독 메시지 전송
                    await self.ws.send(json.dumps(subscribe_message))
                    self.logger.info(f"WebSocket 연결 성공 및 구독 완료: {self.tickers}")
                    log_system_event("websocket_connected", f"Subscribed to {len(self.tickers)} tickers")
                    
                    # 메시지 수신 루프
                    await self._message_loop()
                    
            except websockets.exceptions.ConnectionClosed as e:
                self.connected = False
                self.logger.warning(f"WebSocket 연결 종료: {e}")
                await self._handle_reconnect()
                
            except websockets.exceptions.InvalidURI as e:
                self.connected = False
                self.logger.error(f"WebSocket URI 오류: {e}")
                break
                
            except Exception as e:
                self.connected = False
                log_error(e, "WebSocket 연결 오류")
                await self._handle_reconnect()
    
    async def _message_loop(self):
        """메시지 수신 루프"""
        try:
            async for raw_message in self.ws:
                if not self.running:
                    break
                
                try:
                    # 바이너리 메시지 디코딩
                    if isinstance(raw_message, bytes):
                        message_str = raw_message.decode('utf-8')
                    else:
                        message_str = raw_message
                    
                    # JSON 파싱
                    data = json.loads(message_str)
                    
                    # 메시지 처리
                    await self._process_message(data)
                    
                    # 통계 업데이트
                    self.message_count += 1
                    self.last_message = datetime.now()
                    
                except json.JSONDecodeError as e:
                    self.error_count += 1
                    self.logger.error(f"JSON 파싱 오류: {e}")
                    
                except Exception as e:
                    self.error_count += 1
                    log_error(e, "메시지 처리 오류")
                    
        except websockets.exceptions.ConnectionClosed:
            self.logger.info("WebSocket 연결이 정상적으로 종료됨")
        except Exception as e:
            log_error(e, "메시지 루프 오류")
    
    async def _process_message(self, data: Dict[str, Any]):
        """메시지 처리"""
        try:
            # 메시지 타입 확인
            if 'type' not in data:
                return
            
            # ticker 메시지 처리
            if data['type'] == 'ticker':
                await self._process_ticker_message(data)
            elif data['type'] == 'trade':
                await self._process_trade_message(data)
            elif data['type'] == 'orderbook':
                await self._process_orderbook_message(data)
            else:
                self.logger.debug(f"알 수 없는 메시지 타입: {data.get('type')}")
                
        except Exception as e:
            log_error(e, f"메시지 처리 실패: {data}")
    
    async def _process_ticker_message(self, data: Dict[str, Any]):
        """ticker 메시지 처리"""
        try:
            # 데이터 정규화
            processed_data = {
                'type': 'ticker',
                'code': data.get('code'),
                'trade_price': data.get('trade_price'),
                'trade_volume': data.get('trade_volume'),
                'prev_closing_price': data.get('prev_closing_price'),
                'change': data.get('change'),
                'change_price': data.get('change_price'),
                'change_rate': data.get('change_rate'),
                'signed_change_price': data.get('signed_change_price'),
                'signed_change_rate': data.get('signed_change_rate'),
                'trade_volume': data.get('trade_volume'),
                'acc_trade_volume': data.get('acc_trade_volume'),
                'acc_trade_volume_24h': data.get('acc_trade_volume_24h'),
                'acc_trade_price': data.get('acc_trade_price'),
                'acc_trade_price_24h': data.get('acc_trade_price_24h'),
                'trade_date': data.get('trade_date'),
                'trade_time': data.get('trade_time'),
                'trade_timestamp': data.get('trade_timestamp'),
                'ask_bid': data.get('ask_bid'),
                'acc_ask_volume': data.get('acc_ask_volume'),
                'acc_bid_volume': data.get('acc_bid_volume'),
                'highest_52_week_price': data.get('highest_52_week_price'),
                'highest_52_week_date': data.get('highest_52_week_date'),
                'lowest_52_week_price': data.get('lowest_52_week_price'),
                'lowest_52_week_date': data.get('lowest_52_week_date'),
                'market_state': data.get('market_state'),
                'is_trading_suspended': data.get('is_trading_suspended'),
                'delisting_date': data.get('delisting_date'),
                'market_warning': data.get('market_warning'),
                'timestamp': data.get('timestamp'),
                'stream_type': data.get('stream_type'),
                'received_at': datetime.now().isoformat()
            }
            
            # 콜백 함수 호출
            if self.callback:
                if asyncio.iscoroutinefunction(self.callback):
                    await self.callback(processed_data)
                else:
                    self.callback(processed_data)
                    
            self.logger.debug(f"Ticker 처리: {processed_data['code']} = {processed_data['trade_price']:,.0f}")
            
        except Exception as e:
            log_error(e, f"Ticker 메시지 처리 실패: {data}")
    
    async def _process_trade_message(self, data: Dict[str, Any]):
        """거래 메시지 처리"""
        try:
            processed_data = {
                'type': 'trade',
                'code': data.get('code'),
                'trade_price': data.get('trade_price'),
                'trade_volume': data.get('trade_volume'),
                'ask_bid': data.get('ask_bid'),
                'prev_closing_price': data.get('prev_closing_price'),
                'change': data.get('change'),
                'change_price': data.get('change_price'),
                'trade_date': data.get('trade_date'),
                'trade_time': data.get('trade_time'),
                'trade_timestamp': data.get('trade_timestamp'),
                'timestamp': data.get('timestamp'),
                'sequential_id': data.get('sequential_id'),
                'stream_type': data.get('stream_type'),
                'received_at': datetime.now().isoformat()
            }
            
            # 콜백 함수 호출
            if self.callback:
                if asyncio.iscoroutinefunction(self.callback):
                    await self.callback(processed_data)
                else:
                    self.callback(processed_data)
                    
            self.logger.debug(f"Trade 처리: {processed_data['code']} {processed_data['ask_bid']} {processed_data['trade_price']:,.0f}")
            
        except Exception as e:
            log_error(e, f"Trade 메시지 처리 실패: {data}")
    
    async def _process_orderbook_message(self, data: Dict[str, Any]):
        """호가 메시지 처리"""
        try:
            processed_data = {
                'type': 'orderbook',
                'code': data.get('code'),
                'total_ask_size': data.get('total_ask_size'),
                'total_bid_size': data.get('total_bid_size'),
                'orderbook_units': data.get('orderbook_units', []),
                'timestamp': data.get('timestamp'),
                'stream_type': data.get('stream_type'),
                'received_at': datetime.now().isoformat()
            }
            
            # 콜백 함수 호출
            if self.callback:
                if asyncio.iscoroutinefunction(self.callback):
                    await self.callback(processed_data)
                else:
                    self.callback(processed_data)
                    
            self.logger.debug(f"Orderbook 처리: {processed_data['code']}")
            
        except Exception as e:
            log_error(e, f"Orderbook 메시지 처리 실패: {data}")
    
    async def _handle_reconnect(self):
        """재연결 처리"""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            self.logger.error(f"최대 재연결 횟수 초과: {self.max_reconnect_attempts}")
            log_system_event("websocket_reconnect_failed", f"Max attempts reached: {self.max_reconnect_attempts}")
            self.running = False
            return
        
        self.reconnect_attempts += 1
        self.logger.info(f"WebSocket 재연결 시도 {self.reconnect_attempts}/{self.max_reconnect_attempts}")
        log_system_event("websocket_reconnect_attempt", f"Attempt {self.reconnect_attempts}")
        
        await asyncio.sleep(self.reconnect_delay)
    
    async def start(self):
        """WebSocket 시작"""
        if self.running:
            self.logger.warning("WebSocket이 이미 실행 중입니다")
            return
        
        self.running = True
        self.logger.info(f"WebSocket 시작: {self.tickers}")
        log_system_event("websocket_start", f"Starting with {len(self.tickers)} tickers")
        
        try:
            await self.connect()
        except Exception as e:
            log_error(e, "WebSocket 시작 실패")
            self.running = False
            raise
    
    async def stop(self):
        """WebSocket 중지"""
        if not self.running:
            return
        
        self.running = False
        self.connected = False
        
        if self.ws:
            try:
                await self.ws.close()
                self.logger.info("WebSocket 연결 종료")
                log_system_event("websocket_stop", "WebSocket connection closed")
            except Exception as e:
                log_error(e, "WebSocket 종료 오류")
    
    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self.connected and self.running
    
    def get_status(self) -> Dict[str, Any]:
        """상태 정보 반환"""
        return {
            'connected': self.connected,
            'running': self.running,
            'tickers': self.tickers,
            'message_count': self.message_count,
            'error_count': self.error_count,
            'reconnect_attempts': self.reconnect_attempts,
            'last_message': self.last_message.isoformat() if self.last_message else None,
            'last_ping': self.last_ping.isoformat() if self.last_ping else None
        }
    
    async def update_subscription(self, new_tickers: List[str]):
        """구독 종목 업데이트"""
        if new_tickers != self.tickers:
            self.tickers = new_tickers
            self.logger.info(f"구독 종목 업데이트: {self.tickers}")
            
            # 재연결 필요 (Upbit WebSocket은 구독 중 변경 불가)
            if self.running:
                await self.stop()
                await asyncio.sleep(1)
                await self.start()

class UpbitWebSocketManager:
    """Upbit WebSocket 관리자"""
    
    def __init__(self):
        self.clients: Dict[str, UpbitWebSocketClient] = {}
        self.logger = setup_logger("upbit.websocket_manager")
    
    async def create_client(self, name: str, tickers: List[str], callback: Callable[[Dict], None]) -> UpbitWebSocketClient:
        """WebSocket 클라이언트 생성"""
        if name in self.clients:
            await self.stop_client(name)
        
        client = UpbitWebSocketClient(tickers, callback)
        self.clients[name] = client
        
        self.logger.info(f"WebSocket 클라이언트 생성: {name}")
        return client
    
    async def start_client(self, name: str):
        """클라이언트 시작"""
        if name in self.clients:
            await self.clients[name].start()
            self.logger.info(f"WebSocket 클라이언트 시작: {name}")
    
    async def stop_client(self, name: str):
        """클라이언트 중지"""
        if name in self.clients:
            await self.clients[name].stop()
            del self.clients[name]
            self.logger.info(f"WebSocket 클라이언트 중지: {name}")
    
    async def stop_all(self):
        """모든 클라이언트 중지"""
        for name in list(self.clients.keys()):
            await self.stop_client(name)
        
        self.logger.info("모든 WebSocket 클라이언트 중지")
    
    def get_client(self, name: str) -> Optional[UpbitWebSocketClient]:
        """클라이언트 반환"""
        return self.clients.get(name)
    
    def get_status(self) -> Dict[str, Any]:
        """전체 상태 반환"""
        return {
            'total_clients': len(self.clients),
            'clients': {name: client.get_status() for name, client in self.clients.items()}
        }

# 전역 WebSocket 매니저
websocket_manager = UpbitWebSocketManager()

