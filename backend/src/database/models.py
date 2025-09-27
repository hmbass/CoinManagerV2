"""
CoinTrader Backend - 데이터베이스 모델
SQLAlchemy ORM 모델 정의
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional

Base = declarative_base()

class Trade(Base):
    """거래 기록 테이블"""
    __tablename__ = "trades"
    
    # 기본 필드
    id = Column(Integer, primary_key=True, index=True)
    market = Column(String(20), nullable=False, index=True)  # KRW-BTC
    side = Column(String(10), nullable=False)  # buy, sell
    order_type = Column(String(20), nullable=False, default="market")  # market, limit
    
    # 거래 정보
    price = Column(Float, nullable=False)  # 체결 가격
    volume = Column(Float, nullable=False)  # 거래 수량
    amount = Column(Float, nullable=False)  # 거래 금액 (price * volume)
    fee = Column(Float, default=0.0)  # 수수료
    
    # Upbit 관련
    upbit_uuid = Column(String(100), unique=True, index=True)  # Upbit 주문 UUID
    upbit_side = Column(String(10))  # Upbit API 응답의 side
    
    # 전략 및 성과
    strategy = Column(String(50), index=True)  # 사용된 전략
    profit_loss = Column(Float, default=0.0)  # 실현 손익
    profit_rate = Column(Float, default=0.0)  # 수익률 (%)
    
    # 메타 정보
    notes = Column(Text)  # 거래 메모
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 인덱스
    __table_args__ = (
        Index('idx_market_created', 'market', 'created_at'),
        Index('idx_side_created', 'side', 'created_at'),
        Index('idx_strategy_created', 'strategy', 'created_at'),
    )

class TradingConfig(Base):
    """거래 설정 테이블"""
    __tablename__ = "trading_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)  # 설정 이름
    
    # 거래 기본 설정
    enabled = Column(Boolean, default=True)
    trading_mode = Column(String(10), default="paper")  # live, paper
    markets = Column(Text)  # JSON 문자열로 마켓 목록 저장
    
    # 리스크 관리
    max_position_size = Column(Float, default=100000.0)  # 최대 포지션 크기
    stop_loss_percent = Column(Float, default=3.0)  # 손절매 %
    take_profit_percent = Column(Float, default=2.0)  # 익절매 %
    max_daily_loss = Column(Float, default=50000.0)  # 일일 최대 손실
    max_concurrent_positions = Column(Integer, default=3)  # 동시 포지션 수
    
    # 전략 설정
    strategy_config = Column(Text)  # JSON 문자열로 전략 설정
    
    # 메타 정보
    description = Column(Text)  # 설정 설명
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Portfolio(Base):
    """포트폴리오 현황 테이블"""
    __tablename__ = "portfolio"
    
    id = Column(Integer, primary_key=True, index=True)
    market = Column(String(20), nullable=False, unique=True, index=True)
    
    # 포지션 정보
    volume = Column(Float, default=0.0)  # 보유 수량
    avg_buy_price = Column(Float, default=0.0)  # 평균 매수가
    total_amount = Column(Float, default=0.0)  # 총 투자금액
    
    # 성과 정보
    unrealized_profit = Column(Float, default=0.0)  # 미실현 손익
    realized_profit = Column(Float, default=0.0)  # 실현 손익
    total_profit = Column(Float, default=0.0)  # 총 손익
    profit_rate = Column(Float, default=0.0)  # 수익률 (%)
    
    # 거래 통계
    buy_count = Column(Integer, default=0)  # 매수 횟수
    sell_count = Column(Integer, default=0)  # 매도 횟수
    win_count = Column(Integer, default=0)  # 승리 횟수
    loss_count = Column(Integer, default=0)  # 손실 횟수
    
    # 리스크 관리
    max_drawdown = Column(Float, default=0.0)  # 최대 손실률
    
    # 메타 정보
    first_trade_at = Column(DateTime(timezone=True))  # 첫 거래 시간
    last_trade_at = Column(DateTime(timezone=True))  # 마지막 거래 시간
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class SystemLog(Base):
    """시스템 로그 테이블"""
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(10), nullable=False, index=True)  # INFO, WARNING, ERROR, DEBUG
    module = Column(String(100), index=True)  # 로그 발생 모듈
    message = Column(Text, nullable=False)  # 로그 메시지
    details = Column(Text)  # 추가 상세 정보 (JSON 등)
    
    # 컨텍스트 정보
    user_id = Column(String(50))  # 사용자 ID (있는 경우)
    request_id = Column(String(100))  # 요청 ID (있는 경우)
    market = Column(String(20))  # 관련 마켓 (있는 경우)
    
    # 메타 정보
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # 인덱스
    __table_args__ = (
        Index('idx_level_created', 'level', 'created_at'),
        Index('idx_module_created', 'module', 'created_at'),
    )

class PerformanceMetrics(Base):
    """성과 지표 테이블"""
    __tablename__ = "performance_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime(timezone=True), nullable=False, index=True)  # 기준 날짜
    
    # 기본 성과 지표
    total_trades = Column(Integer, default=0)  # 총 거래 횟수
    win_trades = Column(Integer, default=0)  # 수익 거래
    loss_trades = Column(Integer, default=0)  # 손실 거래
    win_rate = Column(Float, default=0.0)  # 승률 (%)
    
    # 수익 지표
    total_profit = Column(Float, default=0.0)  # 총 손익
    realized_profit = Column(Float, default=0.0)  # 실현 손익
    unrealized_profit = Column(Float, default=0.0)  # 미실현 손익
    profit_rate = Column(Float, default=0.0)  # 수익률 (%)
    
    # 리스크 지표
    max_drawdown = Column(Float, default=0.0)  # 최대 낙폭 (%)
    sharpe_ratio = Column(Float, default=0.0)  # 샤프 비율
    volatility = Column(Float, default=0.0)  # 변동성
    
    # 거래 통계
    avg_profit_per_trade = Column(Float, default=0.0)  # 거래당 평균 손익
    avg_profit_rate = Column(Float, default=0.0)  # 평균 수익률
    max_profit = Column(Float, default=0.0)  # 최대 수익
    max_loss = Column(Float, default=0.0)  # 최대 손실
    
    # 포트폴리오 정보
    total_equity = Column(Float, default=0.0)  # 총 자산
    cash_balance = Column(Float, default=0.0)  # 현금 잔고
    position_value = Column(Float, default=0.0)  # 포지션 가치
    
    # 메타 정보
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 인덱스
    __table_args__ = (
        Index('idx_date_unique', 'date', unique=True),
    )

class Notification(Base):
    """알림 기록 테이블"""
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(50), nullable=False, index=True)  # trade, error, summary, system
    title = Column(String(200), nullable=False)  # 알림 제목
    message = Column(Text, nullable=False)  # 알림 내용
    
    # 발송 정보
    channel = Column(String(50), nullable=False)  # telegram, email, sms 등
    status = Column(String(20), default="pending")  # pending, sent, failed
    sent_at = Column(DateTime(timezone=True))  # 발송 시간
    error_message = Column(Text)  # 발송 실패 시 오류 메시지
    
    # 관련 정보
    trade_id = Column(Integer)  # 관련 거래 ID (있는 경우)
    market = Column(String(20))  # 관련 마켓 (있는 경우)
    
    # 메타 정보
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # 인덱스
    __table_args__ = (
        Index('idx_type_created', 'type', 'created_at'),
        Index('idx_status_created', 'status', 'created_at'),
    )

