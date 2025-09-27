"""
CoinTrader Backend - 설정 관리
환경 변수 기반 설정 관리 시스템
"""
from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # 기본 설정
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    API_HOST: str = "localhost"
    API_PORT: int = 8000
    
    # 데이터베이스 설정
    DATABASE_URL: str = "sqlite:///./trading.db"
    
    # Upbit API 설정
    UPBIT_ACCESS_KEY: str = ""
    UPBIT_SECRET_KEY: str = ""
    UPBIT_SERVER_URL: str = "https://api.upbit.com"
    
    # 거래 설정
    TRADING_ENABLED: bool = True
    TRADING_MODE: str = "paper"  # "live" or "paper"
    DEFAULT_MARKET: str = "KRW-BTC"
    MIN_ORDER_AMOUNT: float = 5000.0
    MAX_POSITION_SIZE: float = 100000.0
    MAX_CONCURRENT_POSITIONS: int = 3
    POSITION_SIZE_PERCENT: float = 10.0
    STOP_LOSS_PERCENT: float = 3.0
    TAKE_PROFIT_PERCENT: float = 2.0
    MAX_DAILY_LOSS: float = 50000.0
    
    # 스캘핑 전략 설정
    SCALPING_ENABLED: bool = True
    SCALPING_RSI_OVERSOLD: int = 30
    SCALPING_RSI_OVERBOUGHT: int = 70
    SCALPING_MIN_VOLUME: float = 1000000.0
    SCALPING_MIN_PROFIT: float = 0.5
    SCALPING_MAX_LOSS: float = 0.3
    
    # 텔레그램 봇 설정
    TELEGRAM_ENABLED: bool = True
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    TELEGRAM_NOTIFICATIONS_ENABLED: bool = True
    NOTIFICATION_TRADE_ALERTS: bool = True
    NOTIFICATION_ERROR_ALERTS: bool = True
    NOTIFICATION_DAILY_SUMMARY: bool = True
    NOTIFICATION_SYSTEM_STATUS: bool = True
    
    # CORS 설정
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # 로깅 설정
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/trading.log"
    
    # 보안 설정
    JWT_SECRET_KEY: str = "your_super_secret_jwt_key_here"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 30
    ENCRYPTION_KEY: str = "your_32_byte_encryption_key_here"
    
    # API 보안
    API_RATE_LIMIT: int = 100
    API_RATE_LIMIT_WINDOW: int = 60
    
    # 모니터링 설정
    PERFORMANCE_MONITORING: bool = True
    METRICS_ENDPOINT_ENABLED: bool = True
    HEALTH_CHECK_INTERVAL: int = 60
    
    # 백업 설정
    AUTO_BACKUP_ENABLED: bool = True
    BACKUP_INTERVAL_HOURS: int = 6
    BACKUP_RETENTION_DAYS: int = 30
    BACKUP_PATH: str = "./backups"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # 환경별 설정 조정
        if self.ENVIRONMENT == "development":
            self.DEBUG = True
            self.LOG_LEVEL = "DEBUG"
        elif self.ENVIRONMENT == "production":
            self.DEBUG = False
            self.LOG_LEVEL = "INFO"
            
    @property
    def is_production(self) -> bool:
        """프로덕션 환경 여부"""
        return self.ENVIRONMENT == "production"
    
    @property
    def is_development(self) -> bool:
        """개발 환경 여부"""
        return self.ENVIRONMENT == "development"
    
    @property
    def is_live_trading(self) -> bool:
        """실거래 모드 여부"""
        return self.TRADING_MODE == "live" and self.TRADING_ENABLED
    
    def validate_required_keys(self) -> List[str]:
        """필수 설정 값 검증"""
        missing_keys = []
        
        if self.is_live_trading:
            if not self.UPBIT_ACCESS_KEY or self.UPBIT_ACCESS_KEY == "your_upbit_access_key_here":
                missing_keys.append("UPBIT_ACCESS_KEY")
            if not self.UPBIT_SECRET_KEY or self.UPBIT_SECRET_KEY == "your_upbit_secret_key_here":
                missing_keys.append("UPBIT_SECRET_KEY")
                
        if self.TELEGRAM_ENABLED:
            if not self.TELEGRAM_BOT_TOKEN or self.TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
                missing_keys.append("TELEGRAM_BOT_TOKEN")
            if not self.TELEGRAM_CHAT_ID or self.TELEGRAM_CHAT_ID == "your_telegram_chat_id_here":
                missing_keys.append("TELEGRAM_CHAT_ID")
                
        return missing_keys

# 전역 설정 인스턴스
settings = Settings()

# 시작 시 설정 검증
missing_keys = settings.validate_required_keys()
if missing_keys:
    print(f"⚠️  다음 환경 변수를 설정하세요: {', '.join(missing_keys)}")
    if settings.is_live_trading:
        print("❌ 실거래 모드에서는 모든 API 키가 필수입니다!")
        
print(f"🔧 환경 설정 로드 완료: {settings.ENVIRONMENT} 모드")
print(f"💰 거래 모드: {settings.TRADING_MODE}")
print(f"🤖 텔레그램 알림: {'활성화' if settings.TELEGRAM_ENABLED else '비활성화'}")
