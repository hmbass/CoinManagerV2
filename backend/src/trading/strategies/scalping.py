"""
CoinTrader 스캘핑 전략
단기 가격 변동을 이용한 빠른 매매 전략
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import numpy as np

from .base import BaseStrategy
from ...utils.logger import setup_logger

class ScalpingStrategy(BaseStrategy):
    """
    스캘핑 전략
    
    특징:
    - 짧은 시간 내 작은 수익을 추구
    - 급격한 가격 변동 감지
    - RSI 과매도/과매수 구간 활용
    - 거래량 급증 감지
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        # 스캘핑 전용 기본 설정
        scalping_config = {
            'enabled': True,
            'min_volume_24h': 2000000,  # 최소 24시간 거래량 (2백만원)
            'max_position_size': 50000,  # 최대 포지션 크기 (5만원)
            'stop_loss_percent': 0.5,   # 손절매 0.5%
            'take_profit_percent': 0.3, # 익절매 0.3%
            'cooldown_minutes': 2,      # 쿨다운 2분
            
            # 스캘핑 특화 설정
            'rsi_period': 14,
            'rsi_oversold': 30,         # RSI 과매도 기준
            'rsi_overbought': 70,       # RSI 과매수 기준
            'price_change_threshold': -0.02,  # 가격 변동 임계값 (-2%)
            'volume_surge_multiplier': 2.0,   # 거래량 급증 배수
            'min_profit_ratio': 0.002,        # 최소 수익률 (0.2%)
            'max_loss_ratio': 0.005,          # 최대 손실률 (0.5%)
            'trend_confirmation_period': 5,   # 트렌드 확인 기간 (분)
        }
        
        # 사용자 설정과 병합
        if config:
            scalping_config.update(config)
        
        super().__init__("scalping", scalping_config)
        
        # 스캘핑 전용 상태
        self.price_history = {}  # 가격 이력
        self.volume_history = {}  # 거래량 이력
        self.rsi_values = {}     # RSI 값들
        
        self.logger.info("스캘핑 전략 초기화 완료")
    
    async def should_buy(self, market_data: Dict[str, Any]) -> bool:
        """
        매수 신호 판단
        
        조건:
        1. 급격한 하락 (-2% 이상)
        2. RSI 과매도 (30 이하)
        3. 거래량 급증 (평균의 2배 이상)
        4. 최근 반등 신호
        """
        try:
            code = market_data.get('code')
            if not code:
                return False
            
            # 기본 거래 가능성 확인
            if not await self.should_trade(market_data):
                return False
            
            current_price = market_data.get('trade_price', 0)
            change_rate = market_data.get('signed_change_rate', 0)
            volume_24h = market_data.get('acc_trade_price_24h', 0)
            
            # 1. 급격한 하락 확인
            price_threshold = self.config.get('price_change_threshold', -0.02)
            if change_rate > price_threshold:  # 하락이 충분하지 않음
                return False
            
            # 2. 가격 이력 업데이트 및 RSI 계산
            await self._update_price_history(code, current_price)
            rsi = await self._calculate_rsi(code)
            
            if rsi is None:
                return False  # RSI 계산 불가
            
            rsi_oversold = self.config.get('rsi_oversold', 30)
            if rsi > rsi_oversold:  # 과매도 상태 아님
                return False
            
            # 3. 거래량 급증 확인
            if not await self._check_volume_surge(code, volume_24h):
                return False
            
            # 4. 반등 신호 확인
            if not await self._check_bounce_signal(code):
                return False
            
            # 5. 추가 안전 장치
            if not await self._additional_buy_checks(market_data):
                return False
            
            # 신호 시간 업데이트
            await self._update_signal_time(code)
            self.buy_signals += 1
            
            self.logger.info(
                f"매수 신호 발생: {code} - "
                f"가격: {current_price:,.0f}, 변동률: {change_rate:.3f}, "
                f"RSI: {rsi:.1f}, 거래량: {volume_24h:,.0f}"
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"매수 신호 판단 오류: {e}")
            return False
    
    async def should_sell(self, market_data: Dict[str, Any], position: Dict[str, Any]) -> bool:
        """
        매도 신호 판단
        
        조건:
        1. 익절매 수익률 달성
        2. 손절매 손실률 도달
        3. RSI 과매수 (70 이상)
        4. 하락 전환 신호
        """
        try:
            code = market_data.get('code')
            current_price = market_data.get('trade_price', 0)
            
            if not code or not current_price or not position:
                return False
            
            entry_price = position.get('avg_buy_price', 0)
            if entry_price == 0:
                return False
            
            # 수익률 계산
            profit_rate = (current_price - entry_price) / entry_price
            
            # 1. 익절매 확인
            min_profit = self.config.get('min_profit_ratio', 0.002)
            if profit_rate >= min_profit:
                self.logger.info(
                    f"익절매 신호: {code} - "
                    f"수익률: {profit_rate:.3f} >= {min_profit:.3f}"
                )
                await self._update_signal_time(code)
                self.sell_signals += 1
                return True
            
            # 2. 손절매 확인
            max_loss = -self.config.get('max_loss_ratio', 0.005)
            if profit_rate <= max_loss:
                self.logger.info(
                    f"손절매 신호: {code} - "
                    f"손실률: {profit_rate:.3f} <= {max_loss:.3f}"
                )
                await self._update_signal_time(code)
                self.sell_signals += 1
                return True
            
            # 3. RSI 과매수 확인
            await self._update_price_history(code, current_price)
            rsi = await self._calculate_rsi(code)
            
            if rsi is not None:
                rsi_overbought = self.config.get('rsi_overbought', 70)
                if rsi >= rsi_overbought and profit_rate > 0:
                    self.logger.info(
                        f"RSI 과매수 매도 신호: {code} - "
                        f"RSI: {rsi:.1f} >= {rsi_overbought}, 수익률: {profit_rate:.3f}"
                    )
                    await self._update_signal_time(code)
                    self.sell_signals += 1
                    return True
            
            # 4. 하락 전환 신호 확인
            if await self._check_downtrend_signal(code):
                if profit_rate > -0.001:  # 최소 손실 (-0.1%) 이상일 때만
                    self.logger.info(
                        f"하락 전환 매도 신호: {code} - 수익률: {profit_rate:.3f}"
                    )
                    await self._update_signal_time(code)
                    self.sell_signals += 1
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"매도 신호 판단 오류: {e}")
            return False
    
    async def _update_price_history(self, code: str, price: float):
        """가격 이력 업데이트"""
        if code not in self.price_history:
            self.price_history[code] = []
        
        self.price_history[code].append({
            'price': price,
            'timestamp': datetime.now()
        })
        
        # 최대 100개 데이터만 유지
        if len(self.price_history[code]) > 100:
            self.price_history[code] = self.price_history[code][-100:]
    
    async def _calculate_rsi(self, code: str, period: Optional[int] = None) -> Optional[float]:
        """RSI 계산"""
        if code not in self.price_history:
            return None
        
        prices = [item['price'] for item in self.price_history[code]]
        if len(prices) < 15:  # RSI 계산을 위한 최소 데이터
            return None
        
        period = period or self.config.get('rsi_period', 14)
        
        try:
            # 가격 변화 계산
            deltas = np.diff(prices)
            
            # 상승/하락 분리
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            
            # 평균 계산
            avg_gain = np.mean(gains[-period:])
            avg_loss = np.mean(losses[-period:])
            
            if avg_loss == 0:
                return 100
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
            
        except Exception as e:
            self.logger.error(f"RSI 계산 오류: {e}")
            return None
    
    async def _check_volume_surge(self, code: str, current_volume: float) -> bool:
        """거래량 급증 확인"""
        try:
            if code not in self.volume_history:
                self.volume_history[code] = []
            
            # 현재 거래량 추가
            self.volume_history[code].append({
                'volume': current_volume,
                'timestamp': datetime.now()
            })
            
            # 최대 50개 데이터만 유지
            if len(self.volume_history[code]) > 50:
                self.volume_history[code] = self.volume_history[code][-50:]
            
            # 평균 거래량 계산 (최근 10개)
            recent_volumes = [item['volume'] for item in self.volume_history[code][-10:]]
            if len(recent_volumes) < 5:
                return True  # 데이터 부족 시 통과
            
            avg_volume = np.mean(recent_volumes[:-1])  # 현재 제외
            surge_multiplier = self.config.get('volume_surge_multiplier', 2.0)
            
            return current_volume >= avg_volume * surge_multiplier
            
        except Exception as e:
            self.logger.error(f"거래량 급증 확인 오류: {e}")
            return False
    
    async def _check_bounce_signal(self, code: str) -> bool:
        """반등 신호 확인"""
        try:
            if code not in self.price_history or len(self.price_history[code]) < 5:
                return True  # 데이터 부족 시 통과
            
            # 최근 5개 가격
            recent_prices = [item['price'] for item in self.price_history[code][-5:]]
            
            # 최근 2개 가격이 상승 추세인지 확인
            if len(recent_prices) >= 3:
                return recent_prices[-1] > recent_prices[-2] > recent_prices[-3]
            
            return True
            
        except Exception as e:
            self.logger.error(f"반등 신호 확인 오류: {e}")
            return False
    
    async def _check_downtrend_signal(self, code: str) -> bool:
        """하락 전환 신호 확인"""
        try:
            if code not in self.price_history or len(self.price_history[code]) < 5:
                return False
            
            # 최근 5개 가격
            recent_prices = [item['price'] for item in self.price_history[code][-5:]]
            
            # 최근 3개 가격이 하락 추세인지 확인
            if len(recent_prices) >= 3:
                return recent_prices[-1] < recent_prices[-2] < recent_prices[-3]
            
            return False
            
        except Exception as e:
            self.logger.error(f"하락 전환 신호 확인 오류: {e}")
            return False
    
    async def _additional_buy_checks(self, market_data: Dict[str, Any]) -> bool:
        """추가 매수 안전 장치"""
        try:
            # 1. 시장 시간 확인 (너무 이른 아침이나 늦은 밤 제외)
            now = datetime.now()
            if now.hour < 6 or now.hour > 23:
                return False
            
            # 2. 급격한 상승 후 하락인지 확인 (불안정 상황 제외)
            high_price = market_data.get('high_price', 0)
            current_price = market_data.get('trade_price', 0)
            
            if high_price > 0:
                high_drop_rate = (current_price - high_price) / high_price
                if high_drop_rate < -0.05:  # 고점 대비 5% 이상 하락 시 제외
                    return False
            
            # 3. 변동성 확인
            change_rate = abs(market_data.get('signed_change_rate', 0))
            if change_rate > 0.1:  # 10% 이상 급변동 시 제외
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"추가 매수 검사 오류: {e}")
            return False
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """전략 정보 반환"""
        base_info = self.get_statistics()
        
        scalping_info = {
            'strategy_type': 'scalping',
            'description': '단기 가격 변동을 이용한 빠른 매매 전략',
            'characteristics': [
                '짧은 보유 기간 (분 단위)',
                '작은 수익률 추구 (0.2-0.5%)',
                'RSI 기반 진입/청산',
                '거래량 급증 감지',
                '빠른 손절매 (0.5%)'
            ],
            'risk_level': 'Medium',
            'recommended_markets': ['KRW-BTC', 'KRW-ETH', 'KRW-XRP'],
            'price_history_count': {
                market: len(history) 
                for market, history in self.price_history.items()
            },
            'volume_history_count': {
                market: len(history) 
                for market, history in self.volume_history.items()
            }
        }
        
        return {**base_info, **scalping_info}
    
    async def reset_market_data(self, code: Optional[str] = None):
        """시장 데이터 초기화"""
        if code:
            # 특정 마켓만 초기화
            self.price_history.pop(code, None)
            self.volume_history.pop(code, None)
            self.rsi_values.pop(code, None)
            self.last_signal_time.pop(code, None)
        else:
            # 전체 초기화
            self.price_history.clear()
            self.volume_history.clear()
            self.rsi_values.clear()
            await self.reset_statistics()
        
        self.logger.info(f"시장 데이터 초기화: {code or '전체'}")

