"""
CoinTrader 포트폴리오 관리자
포트폴리오 현황, 잔고, 수익률 등을 관리하는 모듈
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from decimal import Decimal

from ..config import settings
from ..upbit.client import UpbitClient
from ..database.repositories.trade_repository import TradeRepository
from ..utils.logger import setup_logger

class Portfolio:
    """
    포트폴리오 관리자
    
    주요 기능:
    - 잔고 관리 및 추적
    - 포지션별 손익 계산
    - 포트폴리오 성과 분석
    - 자산 배분 모니터링
    - 리밸런싱 지원
    """
    
    def __init__(self):
        self.logger = setup_logger("portfolio.manager")
        self.upbit_client = UpbitClient()
        self.trade_repository = TradeRepository()
        
        # 포트폴리오 상태
        self.positions = {}  # market -> position_info
        self.balances = {}   # currency -> balance_info
        self.total_krw_value = 0.0
        self.initial_krw_value = 0.0
        
        # 성과 추적
        self.daily_pnl = 0.0
        self.total_pnl = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        
        # 통계
        self.last_updated = None
        self.update_interval = 60  # 1분마다 업데이트
        
        self.logger.info("포트폴리오 매니저 초기화 완료")
    
    async def initialize(self):
        """포트폴리오 매니저 초기화"""
        try:
            # 1. 현재 잔고 로드
            await self._load_balances()
            
            # 2. 기존 포지션 복원
            await self._restore_positions()
            
            # 3. 초기 자산 가치 설정
            await self._calculate_total_value()
            if self.initial_krw_value == 0:
                self.initial_krw_value = self.total_krw_value
            
            # 4. 성과 데이터 로드
            await self._load_performance_data()
            
            self.last_updated = datetime.now()
            
            self.logger.info(
                f"포트폴리오 초기화 완료 - "
                f"총 자산: {self.total_krw_value:,.0f}원, "
                f"포지션: {len(self.positions)}개"
            )
            
        except Exception as e:
            self.logger.error(f"포트폴리오 초기화 오류: {e}")
            raise
    
    async def get_available_balance(self, currency: str = "KRW") -> float:
        """
        사용 가능한 잔고 조회
        
        Args:
            currency: 통화 코드 (기본값: KRW)
            
        Returns:
            float: 사용 가능한 잔고
        """
        try:
            await self._update_balances()
            
            if currency in self.balances:
                return float(self.balances[currency].get('balance', 0))
            
            return 0.0
            
        except Exception as e:
            self.logger.error(f"잔고 조회 오류: {e}")
            return 0.0
    
    async def get_position(self, market: str) -> Optional[Dict[str, Any]]:
        """
        특정 마켓의 포지션 정보 조회
        
        Args:
            market: 마켓 코드 (예: KRW-BTC)
            
        Returns:
            Optional[Dict]: 포지션 정보 또는 None
        """
        try:
            await self._update_positions()
            return self.positions.get(market)
            
        except Exception as e:
            self.logger.error(f"포지션 조회 오류: {e}")
            return None
    
    async def update_position(self, order_result: Dict[str, Any]):
        """
        주문 결과를 바탕으로 포지션 업데이트
        
        Args:
            order_result: 주문 체결 결과
        """
        try:
            market = order_result.get('market')
            side = order_result.get('side')
            price = float(order_result.get('price', 0))
            volume = float(order_result.get('executed_volume', 0)) or float(order_result.get('volume', 0))
            
            if not market or not side or price <= 0 or volume <= 0:
                self.logger.warning(f"유효하지 않은 주문 결과: {order_result}")
                return
            
            # 거래 방향 정규화
            normalized_side = 'buy' if side == 'bid' else 'sell'
            
            if normalized_side == 'buy':
                await self._update_position_on_buy(market, price, volume, order_result)
            else:
                await self._update_position_on_sell(market, price, volume, order_result)
            
            # 잔고 업데이트
            await self._update_balances()
            
            # 총 자산 가치 재계산
            await self._calculate_total_value()
            
            self.logger.info(f"포지션 업데이트 완료: {market} {normalized_side} {volume:.6f} @ {price:,.0f}")
            
        except Exception as e:
            self.logger.error(f"포지션 업데이트 오류: {e}")
    
    async def _update_position_on_buy(self, market: str, price: float, volume: float, order_result: Dict[str, Any]):
        """매수 시 포지션 업데이트"""
        if market not in self.positions:
            # 새로운 포지션 생성
            self.positions[market] = {
                'market': market,
                'volume': 0.0,
                'avg_buy_price': 0.0,
                'total_buy_amount': 0.0,
                'realized_pnl': 0.0,
                'unrealized_pnl': 0.0,
                'trade_count': 0,
                'first_buy_at': datetime.now(),
                'last_update': datetime.now()
            }
        
        position = self.positions[market]
        
        # 평균 매수가 계산
        current_volume = position['volume']
        current_total = position['total_buy_amount']
        
        new_volume = current_volume + volume
        new_total = current_total + (price * volume)
        new_avg_price = new_total / new_volume if new_volume > 0 else 0
        
        # 포지션 정보 업데이트
        position.update({
            'volume': new_volume,
            'avg_buy_price': new_avg_price,
            'total_buy_amount': new_total,
            'trade_count': position['trade_count'] + 1,
            'last_update': datetime.now(),
            'last_order': order_result
        })
        
        self.total_trades += 1
        
        self.logger.debug(f"매수 포지션 업데이트: {market} - 수량: {new_volume:.6f}, 평균가: {new_avg_price:,.0f}")
    
    async def _update_position_on_sell(self, market: str, price: float, volume: float, order_result: Dict[str, Any]):
        """매도 시 포지션 업데이트"""
        if market not in self.positions:
            self.logger.warning(f"매도할 포지션이 없음: {market}")
            return
        
        position = self.positions[market]
        current_volume = position['volume']
        
        if volume > current_volume:
            self.logger.warning(f"매도 수량 초과: {market} - 요청: {volume}, 보유: {current_volume}")
            volume = current_volume
        
        # 손익 계산
        avg_buy_price = position['avg_buy_price']
        sell_amount = price * volume
        buy_amount = avg_buy_price * volume
        trade_pnl = sell_amount - buy_amount
        
        # 실현 손익 업데이트
        position['realized_pnl'] += trade_pnl
        self.total_pnl += trade_pnl
        self.daily_pnl += trade_pnl
        
        # 거래 통계 업데이트
        if trade_pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
        
        # 포지션 수량 업데이트
        remaining_volume = current_volume - volume
        
        if remaining_volume <= 0.000001:  # 거의 0에 가까우면 포지션 완전 청산
            self.logger.info(f"포지션 완전 청산: {market} - 실현 손익: {position['realized_pnl']:+,.0f}원")
            del self.positions[market]
        else:
            # 부분 매도
            position.update({
                'volume': remaining_volume,
                'trade_count': position['trade_count'] + 1,
                'last_update': datetime.now(),
                'last_order': order_result
            })
            
            self.logger.debug(f"부분 매도: {market} - 남은 수량: {remaining_volume:.6f}, 실현 손익: {trade_pnl:+,.0f}원")
        
        self.total_trades += 1
    
    async def _load_balances(self):
        """Upbit에서 잔고 정보 로드"""
        try:
            upbit_balances = await self.upbit_client.get_balances()
            
            if upbit_balances:
                self.balances = {}
                for balance in upbit_balances:
                    currency = balance.get('currency')
                    if currency:
                        self.balances[currency] = {
                            'currency': currency,
                            'balance': float(balance.get('balance', 0)),
                            'locked': float(balance.get('locked', 0)),
                            'avg_buy_price': float(balance.get('avg_buy_price', 0)),
                            'avg_buy_price_modified': balance.get('avg_buy_price_modified', False),
                            'unit_currency': balance.get('unit_currency')
                        }
                
                self.logger.debug(f"잔고 로드 완료: {len(self.balances)}개 통화")
            
        except Exception as e:
            self.logger.error(f"잔고 로드 오류: {e}")
    
    async def _update_balances(self):
        """잔고 정보 업데이트"""
        current_time = datetime.now()
        
        # 업데이트 간격 확인
        if (self.last_updated and 
            (current_time - self.last_updated).total_seconds() < self.update_interval):
            return
        
        await self._load_balances()
        self.last_updated = current_time
    
    async def _restore_positions(self):
        """거래 기록에서 포지션 복원"""
        try:
            # 최근 30일간의 거래 기록에서 포지션 복원
            recent_trades = await self.trade_repository.get_recent_trades(days=30)
            
            # 마켓별로 거래 기록 분석
            market_trades = {}
            for trade in recent_trades:
                market = trade.get('market')
                if market:
                    if market not in market_trades:
                        market_trades[market] = []
                    market_trades[market].append(trade)
            
            # 각 마켓의 현재 포지션 계산
            for market, trades in market_trades.items():
                await self._calculate_position_from_trades(market, trades)
            
            self.logger.info(f"포지션 복원 완료: {len(self.positions)}개 포지션")
            
        except Exception as e:
            self.logger.error(f"포지션 복원 오류: {e}")
    
    async def _calculate_position_from_trades(self, market: str, trades: List[Dict[str, Any]]):
        """거래 기록에서 포지션 계산"""
        try:
            # 거래 시간순 정렬
            sorted_trades = sorted(trades, key=lambda x: x.get('created_at', datetime.min))
            
            total_buy_volume = 0.0
            total_buy_amount = 0.0
            total_sell_volume = 0.0
            realized_pnl = 0.0
            trade_count = 0
            first_buy_at = None
            
            for trade in sorted_trades:
                side = trade.get('side')
                volume = float(trade.get('volume', 0))
                price = float(trade.get('price', 0))
                amount = float(trade.get('amount', 0))
                
                if side == 'buy':
                    total_buy_volume += volume
                    total_buy_amount += amount
                    if not first_buy_at:
                        first_buy_at = trade.get('created_at')
                elif side == 'sell':
                    total_sell_volume += volume
                    # 간단한 FIFO 방식으로 손익 계산
                    if total_buy_volume > 0:
                        avg_buy_price = total_buy_amount / total_buy_volume
                        trade_pnl = (price - avg_buy_price) * volume
                        realized_pnl += trade_pnl
                
                trade_count += 1
            
            # 현재 보유 수량 계산
            current_volume = total_buy_volume - total_sell_volume
            
            # 포지션이 있으면 등록
            if current_volume > 0.000001:
                current_avg_price = total_buy_amount / total_buy_volume if total_buy_volume > 0 else 0
                
                self.positions[market] = {
                    'market': market,
                    'volume': current_volume,
                    'avg_buy_price': current_avg_price,
                    'total_buy_amount': total_buy_amount,
                    'realized_pnl': realized_pnl,
                    'unrealized_pnl': 0.0,  # 나중에 계산
                    'trade_count': trade_count,
                    'first_buy_at': first_buy_at,
                    'last_update': datetime.now()
                }
            
        except Exception as e:
            self.logger.error(f"포지션 계산 오류 ({market}): {e}")
    
    async def _update_positions(self):
        """포지션 정보 업데이트 (미실현 손익 계산)"""
        try:
            for market, position in self.positions.items():
                # 현재가 조회
                current_price = await self.upbit_client.get_current_price(market)
                if current_price:
                    volume = position['volume']
                    avg_buy_price = position['avg_buy_price']
                    
                    # 미실현 손익 계산
                    current_value = current_price * volume
                    buy_value = avg_buy_price * volume
                    unrealized_pnl = current_value - buy_value
                    
                    position.update({
                        'current_price': current_price,
                        'current_value': current_value,
                        'unrealized_pnl': unrealized_pnl,
                        'profit_rate': ((current_price - avg_buy_price) / avg_buy_price) * 100
                    })
            
        except Exception as e:
            self.logger.error(f"포지션 업데이트 오류: {e}")
    
    async def _calculate_total_value(self):
        """총 자산 가치 계산"""
        try:
            total_value = 0.0
            
            # KRW 잔고
            krw_balance = self.balances.get('KRW', {}).get('balance', 0)
            total_value += krw_balance
            
            # 각 포지션의 현재 가치
            for market, position in self.positions.items():
                current_price = await self.upbit_client.get_current_price(market)
                if current_price:
                    volume = position['volume']
                    position_value = current_price * volume
                    total_value += position_value
            
            self.total_krw_value = total_value
            
        except Exception as e:
            self.logger.error(f"총 자산 가치 계산 오류: {e}")
    
    async def _load_performance_data(self):
        """성과 데이터 로드"""
        try:
            # 오늘의 거래에서 손익 계산
            today = datetime.now().date()
            today_trades = await self.trade_repository.get_trades_by_date(today)
            
            self.daily_pnl = sum(
                trade.get('profit_loss', 0) 
                for trade in today_trades 
                if trade.get('side') == 'sell'
            )
            
            # 전체 거래 통계
            all_trades = await self.trade_repository.get_recent_trades(days=365)
            
            self.total_trades = len(all_trades)
            self.winning_trades = len([t for t in all_trades if t.get('profit_loss', 0) > 0])
            self.losing_trades = len([t for t in all_trades if t.get('profit_loss', 0) < 0])
            
            self.total_pnl = sum(
                trade.get('profit_loss', 0) 
                for trade in all_trades 
                if trade.get('side') == 'sell'
            )
            
        except Exception as e:
            self.logger.error(f"성과 데이터 로드 오류: {e}")
    
    # 공개 메서드들
    
    async def get_portfolio_summary(self) -> Dict[str, Any]:
        """포트폴리오 요약 정보"""
        await self._update_positions()
        await self._calculate_total_value()
        
        # 총 미실현 손익
        total_unrealized_pnl = sum(
            position.get('unrealized_pnl', 0) 
            for position in self.positions.values()
        )
        
        # 총 수익률
        total_return_rate = 0.0
        if self.initial_krw_value > 0:
            total_return_rate = ((self.total_krw_value - self.initial_krw_value) / self.initial_krw_value) * 100
        
        # 승률 계산
        win_rate = 0.0
        if self.total_trades > 0:
            win_rate = (self.winning_trades / self.total_trades) * 100
        
        return {
            'total_krw_value': self.total_krw_value,
            'initial_krw_value': self.initial_krw_value,
            'krw_balance': self.balances.get('KRW', {}).get('balance', 0),
            'positions_count': len(self.positions),
            'positions_value': self.total_krw_value - self.balances.get('KRW', {}).get('balance', 0),
            'daily_pnl': self.daily_pnl,
            'total_pnl': self.total_pnl,
            'total_unrealized_pnl': total_unrealized_pnl,
            'total_return_rate': total_return_rate,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': win_rate,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }
    
    async def get_positions_detail(self) -> List[Dict[str, Any]]:
        """포지션 상세 정보"""
        await self._update_positions()
        
        positions_list = []
        for market, position in self.positions.items():
            position_detail = position.copy()
            position_detail['market'] = market
            positions_list.append(position_detail)
        
        # 포지션 가치 기준 내림차순 정렬
        positions_list.sort(key=lambda x: x.get('current_value', 0), reverse=True)
        
        return positions_list
    
    async def get_balances_detail(self) -> List[Dict[str, Any]]:
        """잔고 상세 정보"""
        await self._update_balances()
        
        balances_list = []
        for currency, balance in self.balances.items():
            balance_detail = balance.copy()
            
            # KRW가 아닌 경우 현재 가치 계산
            if currency != 'KRW' and balance['balance'] > 0:
                market = f"KRW-{currency}"
                current_price = await self.upbit_client.get_current_price(market)
                if current_price:
                    balance_detail['current_price'] = current_price
                    balance_detail['krw_value'] = current_price * balance['balance']
                else:
                    balance_detail['krw_value'] = 0
            elif currency == 'KRW':
                balance_detail['krw_value'] = balance['balance']
            
            balances_list.append(balance_detail)
        
        # KRW 가치 기준 내림차순 정렬
        balances_list.sort(key=lambda x: x.get('krw_value', 0), reverse=True)
        
        return balances_list
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """성과 지표"""
        await self._load_performance_data()
        
        # Sharpe Ratio 계산 (간단 버전)
        if self.total_trades > 0:
            avg_trade_return = self.total_pnl / self.total_trades
            # 실제로는 변동성 계산 필요
            sharpe_ratio = avg_trade_return / max(abs(avg_trade_return), 1) if avg_trade_return != 0 else 0
        else:
            sharpe_ratio = 0
        
        # 최대 손실
        max_loss = 0
        if self.losing_trades > 0:
            recent_trades = await self.trade_repository.get_recent_trades(days=30)
            losses = [trade.get('profit_loss', 0) for trade in recent_trades if trade.get('profit_loss', 0) < 0]
            if losses:
                max_loss = min(losses)
        
        return {
            'total_return': self.total_pnl,
            'daily_return': self.daily_pnl,
            'win_rate': (self.winning_trades / max(self.total_trades, 1)) * 100,
            'avg_win': (self.total_pnl / max(self.winning_trades, 1)) if self.winning_trades > 0 else 0,
            'avg_loss': (self.total_pnl / max(self.losing_trades, 1)) if self.losing_trades > 0 else 0,
            'profit_factor': abs(self.total_pnl / max(abs(self.total_pnl - self.total_pnl), 1)) if self.total_pnl != 0 else 0,
            'sharpe_ratio': sharpe_ratio,
            'max_loss': max_loss,
            'total_trades': self.total_trades,
        }
    
    async def reset_daily_performance(self):
        """일일 성과 초기화"""
        self.daily_pnl = 0.0
        self.logger.info("일일 성과 초기화 완료")
    
    def get_statistics(self) -> Dict[str, Any]:
        """포트폴리오 통계"""
        return {
            'total_krw_value': self.total_krw_value,
            'positions_count': len(self.positions),
            'balances_count': len(self.balances),
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'daily_pnl': self.daily_pnl,
            'total_pnl': self.total_pnl,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }

