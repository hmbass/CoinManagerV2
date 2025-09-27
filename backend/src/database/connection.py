"""
CoinTrader Backend - 데이터베이스 연결 관리
SQLAlchemy 엔진 및 세션 관리
"""
from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import asyncio
import logging

from ..config import settings
from .models import Base

logger = logging.getLogger(__name__)

# 동기 엔진 (마이그레이션용)
if settings.DATABASE_URL.startswith("sqlite"):
    # SQLite 설정
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=settings.DEBUG
    )
    
    # SQLite에서 Foreign Key 제약 조건 활성화
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
        
else:
    # PostgreSQL 설정
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=settings.DEBUG
    )

# 비동기 엔진 (런타임용)
if settings.DATABASE_URL.startswith("sqlite"):
    async_database_url = settings.DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://")
    async_engine = create_async_engine(
        async_database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=settings.DEBUG
    )
else:
    async_database_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    async_engine = create_async_engine(
        async_database_url,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=settings.DEBUG
    )

# 세션 팩토리
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncSessionLocal = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

class DatabaseManager:
    """데이터베이스 관리 클래스"""
    
    def __init__(self):
        self.engine = engine
        self.async_engine = async_engine
        
    async def init_db(self):
        """데이터베이스 초기화"""
        try:
            # 테이블 생성 (동기)
            Base.metadata.create_all(bind=self.engine)
            logger.info("데이터베이스 테이블 생성 완료")
            
            # 초기 데이터 설정
            await self._setup_initial_data()
            
            logger.info("데이터베이스 초기화 완료")
            
        except Exception as e:
            logger.error(f"데이터베이스 초기화 실패: {e}")
            raise
    
    async def _setup_initial_data(self):
        """초기 데이터 설정"""
        from .models import TradingConfig
        
        async with AsyncSessionLocal() as session:
            try:
                # 기본 거래 설정이 없으면 생성
                result = await session.execute(
                    text("SELECT COUNT(*) FROM trading_configs WHERE name = 'default'")
                )
                count = result.scalar()
                
                if count == 0:
                    default_config = TradingConfig(
                        name="default",
                        enabled=settings.TRADING_ENABLED,
                        trading_mode=settings.TRADING_MODE,
                        markets='["KRW-BTC"]',
                        max_position_size=settings.MAX_POSITION_SIZE,
                        stop_loss_percent=settings.STOP_LOSS_PERCENT,
                        take_profit_percent=settings.TAKE_PROFIT_PERCENT,
                        max_daily_loss=settings.MAX_DAILY_LOSS,
                        description="기본 거래 설정"
                    )
                    session.add(default_config)
                    await session.commit()
                    logger.info("기본 거래 설정 생성 완료")
                    
            except Exception as e:
                await session.rollback()
                logger.error(f"초기 데이터 설정 실패: {e}")
                raise
    
    def get_session(self) -> Session:
        """동기 세션 생성"""
        return SessionLocal()
    
    async def get_async_session(self) -> AsyncSession:
        """비동기 세션 생성"""
        return AsyncSessionLocal()
    
    async def close(self):
        """데이터베이스 연결 종료"""
        await self.async_engine.dispose()
        self.engine.dispose()
        logger.info("데이터베이스 연결 종료")

# 전역 데이터베이스 매니저
db_manager = DatabaseManager()

# 의존성 주입용 함수들
def get_db() -> Session:
    """동기 데이터베이스 세션 의존성"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_async_db() -> AsyncSession:
    """비동기 데이터베이스 세션 의존성"""
    async with AsyncSessionLocal() as session:
        yield session

# 초기화 함수
async def init_db():
    """데이터베이스 초기화 (애플리케이션 시작 시 호출)"""
    await db_manager.init_db()

# 종료 함수
async def close_db():
    """데이터베이스 연결 종료 (애플리케이션 종료 시 호출)"""
    await db_manager.close()

# 테스트용 함수들
def create_test_db():
    """테스트용 데이터베이스 생성"""
    Base.metadata.create_all(bind=engine)

def drop_test_db():
    """테스트용 데이터베이스 삭제"""
    Base.metadata.drop_all(bind=engine)

# 헬스체크용 함수
async def check_db_health() -> bool:
    """데이터베이스 상태 확인"""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(f"데이터베이스 헬스체크 실패: {e}")
        return False

