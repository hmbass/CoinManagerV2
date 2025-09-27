"""
CoinTrader 기본 거래 전략
모든 거래 전략의 기본 클래스
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, List
from datetime import datetime
import logging

from ...utils.logger import setup_logger

class BaseStrategy(ABC):
    """기본 거래 전략 추상 클래스"""
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
        self.logger = setup_logger(f"strategy.{name}")
        
        # 기본 설정값
        self.default_config = {
            'enabled': True,
            'min_volume_24h': 1000000,  # 최소 24시간 거래량
            'max_position_size': 100000,  # 최대 포지션 크기
            'stop_loss_percent': 3.0,  # 손절매 %
            'take_profit_percent': 2.0,  # 익절매 %
            'cooldown_minutes': 5,  # 쿨다운 시간 (분)
        }
        
        # 설정 병합
        self.config = {**self.default_config, **self.config}
        
        # 상태 정보
        self.last_signal_time = {}  # 마켓별 마지막 신호 시간
        self.signal_count = 0
        self.buy_signals = 0
        self.sell_signals = 0
        
        self.logger.info(f"전략 초기화: {self.name}")
    
    @abstractmethod
    async def should_buy(self, market_data: Dict[str, Any]) -> bool:
        """
        매수 신호 판단
        
        Args:
            market_data: 시장 데이터 (가격, 거래량 등)
            
        Returns:
            bool: 매수 신호 여부
        """
        pass
    
    @abstractmethod
    async def should_sell(self, market_data: Dict[str, Any], position: Dict[str, Any]) -> bool:
        """
        매도 신호 판단
        
        Args:
            market_data: 시장 데이터
            position: 현재 포지션 정보
            
        Returns:
            bool: 매도 신호 여부
        """
        pass
    
    async def should_trade(self, market_data: Dict[str, Any]) -> bool:
        """
        거래 가능 여부 판단 (기본 필터링)
        
        Args:
            market_data: 시장 데이터
            
        Returns:
            bool: 거래 가능 여부
        """
        try:
            # 전략 활성화 확인
            if not self.config.get('enabled', True):
                return False
            
            # 기본 데이터 확인
            code = market_data.get('code')
            if not code:
                return False
            
            # 거래량 확인
            volume_24h = market_data.get('acc_trade_price_24h', 0)
            min_volume = self.config.get('min_volume_24h', 1000000)
            
            if volume_24h < min_volume:
                self.logger.debug(f"거래량 부족: {code} - {volume_24h:,.0f} < {min_volume:,.0f}")
                return False
            
            # 쿨다운 확인
            if await self._is_in_cooldown(code):
                return False
            
            # 시장 상태 확인
            market_state = market_data.get('market_state')
            if market_state != 'ACTIVE':
                self.logger.debug(f"시장 비활성 상태: {code} - {market_state}")
                return False
            
            # 거래 정지 확인
            if market_data.get('is_trading_suspended', False):
                self.logger.debug(f"거래 정지: {code}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"거래 가능성 판단 오류: {e}")
            return False
    
    async def _is_in_cooldown(self, code: str) -> bool:
        """쿨다운 상태 확인"""
        if code not in self.last_signal_time:
            return False
        
        cooldown_minutes = self.config.get('cooldown_minutes', 5)
        last_time = self.last_signal_time[code]
        now = datetime.now()
        
        time_diff = (now - last_time).total_seconds() / 60
        
        if time_diff < cooldown_minutes:
            self.logger.debug(f"쿨다운 중: {code} - {time_diff:.1f}분 < {cooldown_minutes}분")
            return True
        
        return False
    
    async def _update_signal_time(self, code: str):
        """신호 시간 업데이트"""
        self.last_signal_time[code] = datetime.now()
        self.signal_count += 1
    
    async def calculate_position_size(self, market_data: Dict[str, Any], 
                                    available_balance: float) -> float:
        """
        포지션 크기 계산
        
        Args:
            market_data: 시장 데이터
            available_balance: 사용 가능한 잔고
            
        Returns:
            float: 투자할 금액
        """
        try:
            max_position = self.config.get('max_position_size', 100000)
            
            # 사용 가능한 잔고와 최대 포지션 크기 중 작은 값
            position_size = min(available_balance * 0.1, max_position)  # 잔고의 10%
            position_size = min(position_size, max_position)
            
            # 최소 주문 금액 확인
            min_order = 5000  # 5,000원
            if position_size < min_order:
                return 0
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"포지션 크기 계산 오류: {e}")
            return 0
    
    async def calculate_stop_loss_price(self, entry_price: float, side: str = "buy") -> float:
        """
        손절매 가격 계산
        
        Args:
            entry_price: 진입 가격
            side: 거래 방향 (buy/sell)
            
        Returns:
            float: 손절매 가격
        """
        stop_loss_percent = self.config.get('stop_loss_percent', 3.0) / 100
        
        if side == "buy":
            return entry_price * (1 - stop_loss_percent)
        else:
            return entry_price * (1 + stop_loss_percent)
    
    async def calculate_take_profit_price(self, entry_price: float, side: str = "buy") -> float:
        """
        익절매 가격 계산
        
        Args:
            entry_price: 진입 가격
            side: 거래 방향 (buy/sell)
            
        Returns:
            float: 익절매 가격
        """
        take_profit_percent = self.config.get('take_profit_percent', 2.0) / 100
        
        if side == "buy":
            return entry_price * (1 + take_profit_percent)
        else:
            return entry_price * (1 - take_profit_percent)
    
    def get_config(self) -> Dict[str, Any]:
        """설정 반환"""
        return self.config.copy()
    
    def update_config(self, new_config: Dict[str, Any]):
        """설정 업데이트"""
        self.config.update(new_config)
        self.logger.info(f"전략 설정 업데이트: {self.name}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """통계 정보 반환"""
        return {
            'name': self.name,
            'enabled': self.config.get('enabled', True),
            'signal_count': self.signal_count,
            'buy_signals': self.buy_signals,
            'sell_signals': self.sell_signals,
            'active_markets': len(self.last_signal_time),
            'config': self.get_config()
        }
    
    async def reset_statistics(self):
        """통계 초기화"""
        self.signal_count = 0
        self.buy_signals = 0
        self.sell_signals = 0
        self.last_signal_time.clear()
        
        self.logger.info(f"전략 통계 초기화: {self.name}")
    
    def __str__(self) -> str:
        return f"Strategy({self.name})"
    
    def __repr__(self) -> str:
        return f"Strategy(name='{self.name}', enabled={self.config.get('enabled', True)})"

class StrategyManager:
    """전략 관리자"""
    
    def __init__(self):
        self.strategies: Dict[str, BaseStrategy] = {}
        self.logger = setup_logger("strategy.manager")
    
    def register_strategy(self, strategy: BaseStrategy):
        """전략 등록"""
        self.strategies[strategy.name] = strategy
        self.logger.info(f"전략 등록: {strategy.name}")
    
    def unregister_strategy(self, name: str):
        """전략 등록 해제"""
        if name in self.strategies:
            del self.strategies[name]
            self.logger.info(f"전략 등록 해제: {name}")
    
    def get_strategy(self, name: str) -> Optional[BaseStrategy]:
        """전략 반환"""
        return self.strategies.get(name)
    
    def get_all_strategies(self) -> Dict[str, BaseStrategy]:
        """모든 전략 반환"""
        return self.strategies.copy()
    
    def get_enabled_strategies(self) -> Dict[str, BaseStrategy]:
        """활성화된 전략만 반환"""
        return {
            name: strategy 
            for name, strategy in self.strategies.items() 
            if strategy.config.get('enabled', True)
        }
    
    async def update_strategy_config(self, name: str, config: Dict[str, Any]):
        """전략 설정 업데이트"""
        if name in self.strategies:
            self.strategies[name].update_config(config)
            self.logger.info(f"전략 설정 업데이트: {name}")
        else:
            self.logger.warning(f"존재하지 않는 전략: {name}")
    
    def get_manager_statistics(self) -> Dict[str, Any]:
        """관리자 통계"""
        total_strategies = len(self.strategies)
        enabled_strategies = len(self.get_enabled_strategies())
        
        return {
            'total_strategies': total_strategies,
            'enabled_strategies': enabled_strategies,
            'disabled_strategies': total_strategies - enabled_strategies,
            'strategies': {
                name: strategy.get_statistics() 
                for name, strategy in self.strategies.items()
            }
        }

# 전역 전략 매니저
strategy_manager = StrategyManager()

