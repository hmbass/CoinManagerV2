"""
CoinTrader 리스크 관리자
거래 위험 요소를 모니터링하고 제어하는 모듈
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from decimal import Decimal

from ..config import settings
from ..database.repositories.trade_repository import TradeRepository
from ..utils.logger import setup_logger

class RiskManager:
    """
    리스크 관리자
    
    주요 기능:
    - 일일 손실 한도 관리
    - 포지션 크기 제한
    - 최대 동시 포지션 제어
    - 급격한 시장 변동 감지
    - 거래 빈도 제한
    - 연속 손실 방지
    """
    
    def __init__(self):
        self.logger = setup_logger("risk.manager")
        self.trade_repository = TradeRepository()
        
        # 리스크 설정 (설정 파일에서 로드)
        self.max_daily_loss = settings.MAX_DAILY_LOSS
        self.max_position_size = settings.MAX_POSITION_SIZE
        self.max_concurrent_positions = settings.MAX_CONCURRENT_POSITIONS
        self.position_size_percent = settings.POSITION_SIZE_PERCENT
        
        # 실시간 추적 변수
        self.daily_pnl = 0.0
        self.current_positions = {}
        self.recent_trades = []
        self.consecutive_losses = 0
        self.last_trade_time = {}
        
        # 위험 상태
        self.risk_alerts = []
        self.emergency_stop = False
        
        self.logger.info("리스크 매니저 초기화 완료")
    
    async def initialize(self):
        """리스크 매니저 초기화"""
        try:
            # 오늘의 거래 기록 로드
            await self._load_daily_trades()
            
            # 현재 포지션 상태 로드
            await self._load_current_positions()
            
            # 연속 손실 계산
            await self._calculate_consecutive_losses()
            
            self.logger.info(
                f"리스크 매니저 초기화 완료 - "
                f"일일 손익: {self.daily_pnl:+,.0f}, "
                f"포지션: {len(self.current_positions)}, "
                f"연속 손실: {self.consecutive_losses}"
            )
            
        except Exception as e:
            self.logger.error(f"리스크 매니저 초기화 오류: {e}")
            raise
    
    async def validate_buy_order(self, market: str, price: float, amount: Optional[float] = None) -> bool:
        """
        매수 주문 검증
        
        Args:
            market: 거래 마켓
            price: 주문 가격
            amount: 주문 금액 (None이면 자동 계산)
            
        Returns:
            bool: 주문 허용 여부
        """
        try:
            # 1. 긴급 정지 상태 확인
            if self.emergency_stop:
                self.logger.warning("긴급 정지 상태 - 모든 거래 차단")
                return False
            
            # 2. 일일 손실 한도 확인
            if not await self._check_daily_loss_limit():
                return False
            
            # 3. 최대 동시 포지션 확인
            if not await self._check_max_positions():
                return False
            
            # 4. 포지션 크기 확인
            if amount and not await self._check_position_size(amount):
                return False
            
            # 5. 거래 빈도 확인
            if not await self._check_trading_frequency(market):
                return False
            
            # 6. 연속 손실 확인
            if not await self._check_consecutive_losses():
                return False
            
            # 7. 시장 변동성 확인
            if not await self._check_market_volatility(market, price):
                return False
            
            # 8. 중복 포지션 확인
            if not await self._check_duplicate_position(market):
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"매수 주문 검증 오류: {e}")
            return False
    
    async def validate_sell_order(self, market: str, volume: float) -> bool:
        """
        매도 주문 검증
        
        Args:
            market: 거래 마켓
            volume: 매도 수량
            
        Returns:
            bool: 주문 허용 여부
        """
        try:
            # 1. 포지션 존재 확인
            if market not in self.current_positions:
                self.logger.warning(f"포지션 없음: {market}")
                return False
            
            # 2. 수량 확인
            available_volume = self.current_positions[market].get('volume', 0)
            if volume > available_volume:
                self.logger.warning(f"수량 부족: {market} - 요청: {volume}, 보유: {available_volume}")
                return False
            
            # 3. 최소 매도 금액 확인
            current_price = self.current_positions[market].get('current_price', 0)
            sell_amount = volume * current_price
            
            if sell_amount < 1000:  # 최소 1,000원
                self.logger.warning(f"최소 매도 금액 미달: {market} - {sell_amount:,.0f}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"매도 주문 검증 오류: {e}")
            return False
    
    async def _check_daily_loss_limit(self) -> bool:
        """일일 손실 한도 확인"""
        if self.daily_pnl <= -self.max_daily_loss:
            await self._add_risk_alert(
                "DAILY_LOSS_LIMIT",
                f"일일 손실 한도 도달: {self.daily_pnl:+,.0f} <= -{self.max_daily_loss:,.0f}"
            )
            return False
        
        # 80% 도달 시 경고
        if self.daily_pnl <= -self.max_daily_loss * 0.8:
            await self._add_risk_alert(
                "DAILY_LOSS_WARNING",
                f"일일 손실 80% 도달: {self.daily_pnl:+,.0f}"
            )
        
        return True
    
    async def _check_max_positions(self) -> bool:
        """최대 동시 포지션 확인"""
        current_count = len(self.current_positions)
        
        if current_count >= self.max_concurrent_positions:
            await self._add_risk_alert(
                "MAX_POSITIONS",
                f"최대 동시 포지션 도달: {current_count} >= {self.max_concurrent_positions}"
            )
            return False
        
        return True
    
    async def _check_position_size(self, amount: float) -> bool:
        """포지션 크기 확인"""
        if amount > self.max_position_size:
            await self._add_risk_alert(
                "POSITION_SIZE",
                f"포지션 크기 초과: {amount:,.0f} > {self.max_position_size:,.0f}"
            )
            return False
        
        return True
    
    async def _check_trading_frequency(self, market: str) -> bool:
        """거래 빈도 확인"""
        if market in self.last_trade_time:
            last_time = self.last_trade_time[market]
            time_diff = (datetime.now() - last_time).total_seconds()
            
            min_interval = 300  # 5분 최소 간격
            
            if time_diff < min_interval:
                await self._add_risk_alert(
                    "TRADING_FREQUENCY",
                    f"거래 빈도 초과: {market} - {time_diff:.0f}초 < {min_interval}초"
                )
                return False
        
        return True
    
    async def _check_consecutive_losses(self) -> bool:
        """연속 손실 확인"""
        max_consecutive_losses = 5
        
        if self.consecutive_losses >= max_consecutive_losses:
            await self._add_risk_alert(
                "CONSECUTIVE_LOSSES",
                f"연속 손실 한도 도달: {self.consecutive_losses} >= {max_consecutive_losses}"
            )
            return False
        
        # 3회 연속 손실 시 경고
        if self.consecutive_losses >= 3:
            await self._add_risk_alert(
                "CONSECUTIVE_LOSSES_WARNING",
                f"연속 손실 경고: {self.consecutive_losses}회"
            )
        
        return True
    
    async def _check_market_volatility(self, market: str, current_price: float) -> bool:
        """시장 변동성 확인"""
        try:
            # 최근 거래에서 해당 마켓의 가격 변동 확인
            recent_market_trades = [
                trade for trade in self.recent_trades[-10:]  # 최근 10건
                if trade.get('market') == market
            ]
            
            if len(recent_market_trades) < 2:
                return True  # 데이터 부족 시 통과
            
            # 최근 가격들
            recent_prices = [trade.get('price', 0) for trade in recent_market_trades]
            avg_price = sum(recent_prices) / len(recent_prices)
            
            # 현재 가격이 평균 대비 10% 이상 차이나면 위험
            price_diff_ratio = abs(current_price - avg_price) / avg_price
            
            if price_diff_ratio > 0.1:  # 10% 이상 차이
                await self._add_risk_alert(
                    "HIGH_VOLATILITY",
                    f"높은 변동성 감지: {market} - {price_diff_ratio:.1%}"
                )
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"시장 변동성 확인 오류: {e}")
            return True  # 오류 시 통과
    
    async def _check_duplicate_position(self, market: str) -> bool:
        """중복 포지션 확인"""
        if market in self.current_positions:
            volume = self.current_positions[market].get('volume', 0)
            if volume > 0:
                await self._add_risk_alert(
                    "DUPLICATE_POSITION",
                    f"이미 포지션 보유 중: {market} - {volume:.6f}"
                )
                return False
        
        return True
    
    async def update_performance_tracking(self, trade_data: Dict[str, Any]):
        """성과 추적 업데이트"""
        try:
            market = trade_data.get('market')
            side = trade_data.get('side')
            amount = trade_data.get('amount', 0)
            
            # 거래 기록 추가
            self.recent_trades.append(trade_data)
            
            # 최근 100건만 유지
            if len(self.recent_trades) > 100:
                self.recent_trades = self.recent_trades[-100:]
            
            # 마지막 거래 시간 업데이트
            self.last_trade_time[market] = datetime.now()
            
            # 포지션 업데이트
            if side == 'buy':
                await self._update_position_on_buy(trade_data)
            elif side == 'sell':
                await self._update_position_on_sell(trade_data)
            
            # 일일 손익 업데이트 (매도 시에만)
            if side == 'sell':
                profit_loss = trade_data.get('profit_loss', 0)
                self.daily_pnl += profit_loss
                
                # 연속 손실 업데이트
                if profit_loss < 0:
                    self.consecutive_losses += 1
                else:
                    self.consecutive_losses = 0
            
            self.logger.debug(f"성과 추적 업데이트: {trade_data}")
            
        except Exception as e:
            self.logger.error(f"성과 추적 업데이트 오류: {e}")
    
    async def _update_position_on_buy(self, trade_data: Dict[str, Any]):
        """매수 시 포지션 업데이트"""
        market = trade_data.get('market')
        volume = trade_data.get('volume', 0)
        price = trade_data.get('price', 0)
        amount = trade_data.get('amount', 0)
        
        if market not in self.current_positions:
            self.current_positions[market] = {
                'volume': 0,
                'avg_price': 0,
                'total_amount': 0
            }
        
        position = self.current_positions[market]
        
        # 평균 매수가 계산
        new_total_volume = position['volume'] + volume
        new_total_amount = position['total_amount'] + amount
        new_avg_price = new_total_amount / new_total_volume if new_total_volume > 0 else 0
        
        position.update({
            'volume': new_total_volume,
            'avg_price': new_avg_price,
            'total_amount': new_total_amount,
            'last_update': datetime.now()
        })
    
    async def _update_position_on_sell(self, trade_data: Dict[str, Any]):
        """매도 시 포지션 업데이트"""
        market = trade_data.get('market')
        volume = trade_data.get('volume', 0)
        
        if market in self.current_positions:
            position = self.current_positions[market]
            new_volume = position['volume'] - volume
            
            if new_volume <= 0:
                # 포지션 완전 청산
                del self.current_positions[market]
            else:
                # 부분 매도
                position['volume'] = new_volume
                position['last_update'] = datetime.now()
    
    async def _load_daily_trades(self):
        """오늘의 거래 기록 로드"""
        try:
            today = datetime.now().date()
            daily_trades = await self.trade_repository.get_trades_by_date(today)
            
            # 일일 손익 계산
            self.daily_pnl = sum(
                trade.get('profit_loss', 0) 
                for trade in daily_trades 
                if trade.get('side') == 'sell'
            )
            
            # 최근 거래 기록 설정
            self.recent_trades = daily_trades[-50:] if daily_trades else []
            
        except Exception as e:
            self.logger.error(f"일일 거래 기록 로드 오류: {e}")
    
    async def _load_current_positions(self):
        """현재 포지션 상태 로드"""
        try:
            # 실제 구현에서는 포트폴리오 매니저에서 가져오기
            # 여기서는 빈 상태로 시작
            self.current_positions = {}
            
        except Exception as e:
            self.logger.error(f"현재 포지션 로드 오류: {e}")
    
    async def _calculate_consecutive_losses(self):
        """연속 손실 계산"""
        try:
            self.consecutive_losses = 0
            
            # 최근 매도 거래에서 연속 손실 계산
            sell_trades = [
                trade for trade in reversed(self.recent_trades)
                if trade.get('side') == 'sell'
            ]
            
            for trade in sell_trades:
                profit_loss = trade.get('profit_loss', 0)
                if profit_loss < 0:
                    self.consecutive_losses += 1
                else:
                    break
            
        except Exception as e:
            self.logger.error(f"연속 손실 계산 오류: {e}")
    
    async def _add_risk_alert(self, alert_type: str, message: str):
        """리스크 알림 추가"""
        alert = {
            'type': alert_type,
            'message': message,
            'timestamp': datetime.now(),
            'level': 'WARNING' if 'WARNING' in alert_type else 'ERROR'
        }
        
        self.risk_alerts.append(alert)
        
        # 최근 50개만 유지
        if len(self.risk_alerts) > 50:
            self.risk_alerts = self.risk_alerts[-50:]
        
        # 심각한 알림은 긴급 정지 고려
        if alert['level'] == 'ERROR':
            await self._consider_emergency_stop(alert)
        
        self.logger.warning(f"리스크 알림: {alert_type} - {message}")
    
    async def _consider_emergency_stop(self, alert: Dict[str, Any]):
        """긴급 정지 고려"""
        critical_alerts = [
            'DAILY_LOSS_LIMIT',
            'CONSECUTIVE_LOSSES'
        ]
        
        if alert['type'] in critical_alerts:
            self.emergency_stop = True
            self.logger.critical(f"긴급 정지 활성화: {alert['message']}")
    
    # 공개 메서드들
    
    async def get_risk_status(self) -> Dict[str, Any]:
        """리스크 상태 반환"""
        return {
            'emergency_stop': self.emergency_stop,
            'daily_pnl': self.daily_pnl,
            'daily_loss_usage': abs(self.daily_pnl) / self.max_daily_loss * 100,
            'current_positions_count': len(self.current_positions),
            'max_positions_usage': len(self.current_positions) / self.max_concurrent_positions * 100,
            'consecutive_losses': self.consecutive_losses,
            'recent_alerts_count': len(self.risk_alerts),
            'risk_level': self._calculate_risk_level()
        }
    
    def _calculate_risk_level(self) -> str:
        """리스크 레벨 계산"""
        if self.emergency_stop:
            return 'CRITICAL'
        
        # 일일 손실 기준
        loss_ratio = abs(self.daily_pnl) / self.max_daily_loss
        
        # 연속 손실 기준
        consecutive_ratio = self.consecutive_losses / 5
        
        # 포지션 수 기준
        position_ratio = len(self.current_positions) / self.max_concurrent_positions
        
        max_ratio = max(loss_ratio, consecutive_ratio, position_ratio)
        
        if max_ratio >= 0.8:
            return 'HIGH'
        elif max_ratio >= 0.5:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    async def get_statistics(self) -> Dict[str, Any]:
        """리스크 관리 통계"""
        return {
            'risk_status': await self.get_risk_status(),
            'limits': {
                'max_daily_loss': self.max_daily_loss,
                'max_position_size': self.max_position_size,
                'max_concurrent_positions': self.max_concurrent_positions,
                'position_size_percent': self.position_size_percent
            },
            'current_state': {
                'daily_pnl': self.daily_pnl,
                'current_positions': len(self.current_positions),
                'consecutive_losses': self.consecutive_losses,
                'recent_trades_count': len(self.recent_trades)
            },
            'recent_alerts': self.risk_alerts[-10:],  # 최근 10개 알림
        }
    
    async def reset_daily_tracking(self):
        """일일 추적 데이터 초기화"""
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        self.recent_trades.clear()
        self.risk_alerts.clear()
        self.emergency_stop = False
        
        self.logger.info("일일 추적 데이터 초기화 완료")
    
    async def force_emergency_stop(self, reason: str):
        """강제 긴급 정지"""
        self.emergency_stop = True
        await self._add_risk_alert('FORCE_STOP', f"강제 긴급 정지: {reason}")
        
    async def release_emergency_stop(self, reason: str):
        """긴급 정지 해제"""
        self.emergency_stop = False
        await self._add_risk_alert('STOP_RELEASED', f"긴급 정지 해제: {reason}")
        self.logger.info(f"긴급 정지 해제: {reason}")

