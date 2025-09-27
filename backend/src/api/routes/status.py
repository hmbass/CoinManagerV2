"""
CoinTrader API - 시스템 상태 라우터
시스템 상태, 헬스체크, 모니터링 API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import asyncio
import psutil
from datetime import datetime, timedelta
from typing import Dict, Any

from ...database.connection import get_db, check_db_health
from ...database.models import Trade, SystemLog
from ...config import settings
from ...utils.logger import setup_logger

router = APIRouter()
logger = setup_logger("api.status")

@router.get("/health", response_model=dict)
async def health_check(db: Session = Depends(get_db)):
    """기본 헬스체크"""
    try:
        # 데이터베이스 연결 확인
        db_healthy = await check_db_health()
        
        # 기본 시스템 정보
        current_time = datetime.now()
        
        result = {
            "status": "healthy" if db_healthy else "unhealthy",
            "timestamp": current_time.isoformat(),
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT,
            "services": {
                "database": "healthy" if db_healthy else "unhealthy",
                "api": "healthy"
            }
        }
        
        if not db_healthy:
            result["status"] = "unhealthy"
            logger.warning("헬스체크 실패: 데이터베이스 연결 문제")
        else:
            logger.debug("헬스체크 통과")
        
        return result
        
    except Exception as e:
        logger.error(f"헬스체크 실패: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

@router.get("/detailed", response_model=dict)
async def detailed_status(db: Session = Depends(get_db)):
    """상세 시스템 상태"""
    try:
        current_time = datetime.now()
        
        # 시스템 리소스 정보
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # 데이터베이스 상태
        db_healthy = await check_db_health()
        
        # 최근 거래 통계
        today = current_time.date()
        recent_trades = db.query(Trade).filter(
            Trade.created_at >= today
        ).count()
        
        # 최근 에러 로그
        recent_errors = db.query(SystemLog).filter(
            SystemLog.level == "ERROR",
            SystemLog.created_at >= current_time - timedelta(hours=1)
        ).count()
        
        result = {
            "timestamp": current_time.isoformat(),
            "status": "healthy" if db_healthy and cpu_percent < 90 and memory.percent < 90 else "warning",
            "uptime": "N/A",  # 실제 구현에서는 프로세스 시작 시간 기준으로 계산
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_mb": memory.available // (1024 * 1024),
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free // (1024 * 1024 * 1024)
            },
            "database": {
                "status": "healthy" if db_healthy else "unhealthy",
                "connection_pool": "N/A"  # SQLAlchemy pool 정보
            },
            "trading": {
                "enabled": settings.TRADING_ENABLED,
                "mode": settings.TRADING_MODE,
                "today_trades": recent_trades
            },
            "monitoring": {
                "recent_errors": recent_errors,
                "log_level": settings.LOG_LEVEL
            },
            "configuration": {
                "environment": settings.ENVIRONMENT,
                "debug": settings.DEBUG,
                "telegram_enabled": settings.TELEGRAM_ENABLED
            }
        }
        
        logger.info("상세 시스템 상태 조회")
        return result
        
    except Exception as e:
        logger.error(f"상세 시스템 상태 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="시스템 상태 조회에 실패했습니다")

@router.get("/metrics", response_model=dict)
async def get_metrics(db: Session = Depends(get_db)):
    """시스템 메트릭스"""
    try:
        current_time = datetime.now()
        
        # 거래 메트릭스 (최근 24시간)
        yesterday = current_time - timedelta(days=1)
        trades_24h = db.query(Trade).filter(Trade.created_at >= yesterday).all()
        
        trade_metrics = {
            "total_trades_24h": len(trades_24h),
            "buy_trades_24h": len([t for t in trades_24h if t.side == "buy"]),
            "sell_trades_24h": len([t for t in trades_24h if t.side == "sell"]),
            "total_volume_24h": sum(t.amount for t in trades_24h),
            "total_profit_24h": sum(t.profit_loss for t in trades_24h if t.profit_loss)
        }
        
        # 시스템 메트릭스
        system_metrics = {
            "cpu_usage": psutil.cpu_percent(),
            "memory_usage": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent
        }
        
        # 로그 메트릭스 (최근 1시간)
        hour_ago = current_time - timedelta(hours=1)
        log_metrics = {
            "errors_1h": db.query(SystemLog).filter(
                SystemLog.level == "ERROR",
                SystemLog.created_at >= hour_ago
            ).count(),
            "warnings_1h": db.query(SystemLog).filter(
                SystemLog.level == "WARNING",
                SystemLog.created_at >= hour_ago
            ).count(),
            "total_logs_1h": db.query(SystemLog).filter(
                SystemLog.created_at >= hour_ago
            ).count()
        }
        
        result = {
            "timestamp": current_time.isoformat(),
            "trading": trade_metrics,
            "system": system_metrics,
            "logs": log_metrics
        }
        
        logger.debug("시스템 메트릭스 조회")
        return result
        
    except Exception as e:
        logger.error(f"메트릭스 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="메트릭스 조회에 실패했습니다")

@router.get("/logs", response_model=dict)
async def get_recent_logs(
    level: str = "INFO",
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """최근 로그 조회"""
    try:
        query = db.query(SystemLog)
        
        # 로그 레벨 필터
        if level and level.upper() != "ALL":
            query = query.filter(SystemLog.level == level.upper())
        
        # 최근 로그 조회
        logs = query.order_by(SystemLog.created_at.desc()).limit(limit).all()
        
        result = {
            "total": len(logs),
            "level_filter": level,
            "logs": [
                {
                    "id": log.id,
                    "level": log.level,
                    "module": log.module,
                    "message": log.message,
                    "created_at": log.created_at.isoformat()
                }
                for log in logs
            ]
        }
        
        logger.debug(f"최근 로그 조회: {level} 레벨, {len(logs)}건")
        return result
        
    except Exception as e:
        logger.error(f"로그 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="로그 조회에 실패했습니다")

@router.post("/test-connection", response_model=dict)
async def test_external_connections():
    """외부 서비스 연결 테스트"""
    try:
        results = {}
        
        # Upbit API 연결 테스트 (API 키 없이도 가능한 공개 API)
        try:
            import requests
            response = requests.get(
                "https://api.upbit.com/v1/market/all",
                timeout=10
            )
            results["upbit_api"] = {
                "status": "healthy" if response.status_code == 200 else "error",
                "response_time_ms": int(response.elapsed.total_seconds() * 1000),
                "status_code": response.status_code
            }
        except Exception as e:
            results["upbit_api"] = {
                "status": "error",
                "error": str(e)
            }
        
        # 텔레그램 API 연결 테스트 (설정된 경우만)
        if settings.TELEGRAM_BOT_TOKEN:
            try:
                import requests
                response = requests.get(
                    f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getMe",
                    timeout=10
                )
                results["telegram_api"] = {
                    "status": "healthy" if response.status_code == 200 else "error",
                    "response_time_ms": int(response.elapsed.total_seconds() * 1000),
                    "configured": True
                }
            except Exception as e:
                results["telegram_api"] = {
                    "status": "error",
                    "error": str(e),
                    "configured": True
                }
        else:
            results["telegram_api"] = {
                "status": "not_configured",
                "configured": False
            }
        
        overall_status = "healthy" if all(
            r.get("status") in ["healthy", "not_configured"] 
            for r in results.values()
        ) else "error"
        
        result = {
            "overall_status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "connections": results
        }
        
        logger.info(f"외부 연결 테스트 완료: {overall_status}")
        return result
        
    except Exception as e:
        logger.error(f"연결 테스트 실패: {e}")
        raise HTTPException(status_code=500, detail="연결 테스트에 실패했습니다")

