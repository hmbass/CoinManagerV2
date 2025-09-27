"""
CoinTrader Backend - FastAPI 메인 애플리케이션
단타 코인 트레이딩 시스템 API 서버
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from .config import settings
from .database.connection import init_db
from .api.routes import trades, config, status, analytics
from .utils.logger import setup_logger

# 전역 인스턴스들
logger = setup_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    try:
        # 시작 시 초기화
        logger.info("CoinTrader API 서버 시작 중...")
        
        # 데이터베이스 초기화
        await init_db()
        logger.info("데이터베이스 초기화 완료")
        
        logger.info("CoinTrader API 서버 시작 완료")
        
        yield
        
    finally:
        # 종료 시 정리
        logger.info("CoinTrader API 서버 종료 중...")
        logger.info("CoinTrader API 서버 종료 완료")

# FastAPI 앱 생성
app = FastAPI(
    title="CoinTrader API",
    description="단타 코인 트레이딩 시스템 API 서버",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)

# 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# API 라우터 등록
app.include_router(trades.router, prefix="/api/v1/trades", tags=["trades"])
app.include_router(config.router, prefix="/api/v1/config", tags=["config"])
app.include_router(status.router, prefix="/api/v1/status", tags=["status"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "CoinTrader API Server",
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs" if settings.DEBUG else "disabled"
    }

@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트"""
    return {
        "status": "healthy",
        "timestamp": asyncio.get_event_loop().time(),
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )

