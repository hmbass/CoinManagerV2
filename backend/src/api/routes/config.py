"""
CoinTrader API - 설정 관련 라우터
거래 설정 조회, 수정 API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
import json

from ...database.connection import get_db
from ...database.models import TradingConfig
from ...config import settings
from ...utils.logger import setup_logger

router = APIRouter()
logger = setup_logger("api.config")

@router.get("/", response_model=dict)
async def get_config(
    config_name: str = "default",
    db: Session = Depends(get_db)
):
    """거래 설정 조회"""
    try:
        config = db.query(TradingConfig).filter(TradingConfig.name == config_name).first()
        
        if not config:
            # 기본 설정 반환
            return {
                "name": "default",
                "enabled": settings.TRADING_ENABLED,
                "trading_mode": settings.TRADING_MODE,
                "markets": ["KRW-BTC"],
                "max_position_size": settings.MAX_POSITION_SIZE,
                "stop_loss_percent": settings.STOP_LOSS_PERCENT,
                "take_profit_percent": settings.TAKE_PROFIT_PERCENT,
                "max_daily_loss": settings.MAX_DAILY_LOSS,
                "max_concurrent_positions": 3,
                "strategy_config": {},
                "description": "기본 설정 (환경 변수 기반)"
            }
        
        # 데이터베이스 설정 반환
        result = {
            "id": config.id,
            "name": config.name,
            "enabled": config.enabled,
            "trading_mode": config.trading_mode,
            "markets": json.loads(config.markets) if config.markets else [],
            "max_position_size": config.max_position_size,
            "stop_loss_percent": config.stop_loss_percent,
            "take_profit_percent": config.take_profit_percent,
            "max_daily_loss": config.max_daily_loss,
            "max_concurrent_positions": config.max_concurrent_positions,
            "strategy_config": json.loads(config.strategy_config) if config.strategy_config else {},
            "description": config.description,
            "created_at": config.created_at.isoformat(),
            "updated_at": config.updated_at.isoformat() if config.updated_at else None
        }
        
        logger.info(f"거래 설정 조회: {config_name}")
        return result
        
    except Exception as e:
        logger.error(f"거래 설정 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="설정 조회에 실패했습니다")

@router.put("/", response_model=dict)
async def update_config(
    config_data: dict,
    config_name: str = "default",
    db: Session = Depends(get_db)
):
    """거래 설정 수정"""
    try:
        config = db.query(TradingConfig).filter(TradingConfig.name == config_name).first()
        
        if not config:
            # 새 설정 생성
            config = TradingConfig(name=config_name)
            db.add(config)
        
        # 설정 업데이트
        if "enabled" in config_data:
            config.enabled = config_data["enabled"]
        if "trading_mode" in config_data:
            config.trading_mode = config_data["trading_mode"]
        if "markets" in config_data:
            config.markets = json.dumps(config_data["markets"])
        if "max_position_size" in config_data:
            config.max_position_size = config_data["max_position_size"]
        if "stop_loss_percent" in config_data:
            config.stop_loss_percent = config_data["stop_loss_percent"]
        if "take_profit_percent" in config_data:
            config.take_profit_percent = config_data["take_profit_percent"]
        if "max_daily_loss" in config_data:
            config.max_daily_loss = config_data["max_daily_loss"]
        if "max_concurrent_positions" in config_data:
            config.max_concurrent_positions = config_data["max_concurrent_positions"]
        if "strategy_config" in config_data:
            config.strategy_config = json.dumps(config_data["strategy_config"])
        if "description" in config_data:
            config.description = config_data["description"]
        
        db.commit()
        db.refresh(config)
        
        result = {
            "id": config.id,
            "name": config.name,
            "enabled": config.enabled,
            "trading_mode": config.trading_mode,
            "markets": json.loads(config.markets) if config.markets else [],
            "max_position_size": config.max_position_size,
            "stop_loss_percent": config.stop_loss_percent,
            "take_profit_percent": config.take_profit_percent,
            "max_daily_loss": config.max_daily_loss,
            "max_concurrent_positions": config.max_concurrent_positions,
            "strategy_config": json.loads(config.strategy_config) if config.strategy_config else {},
            "description": config.description,
            "updated_at": config.updated_at.isoformat() if config.updated_at else None
        }
        
        logger.info(f"거래 설정 수정 완료: {config_name}")
        return result
        
    except Exception as e:
        db.rollback()
        logger.error(f"거래 설정 수정 실패: {e}")
        raise HTTPException(status_code=500, detail="설정 수정에 실패했습니다")

@router.get("/system", response_model=dict)
async def get_system_config():
    """시스템 설정 조회 (읽기 전용)"""
    try:
        result = {
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
            "api_host": settings.API_HOST,
            "api_port": settings.API_PORT,
            "database_url": settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else settings.DATABASE_URL,  # 보안상 일부만 표시
            "trading_enabled": settings.TRADING_ENABLED,
            "trading_mode": settings.TRADING_MODE,
            "telegram_enabled": settings.TELEGRAM_ENABLED,
            "upbit_connected": bool(settings.UPBIT_ACCESS_KEY and settings.UPBIT_SECRET_KEY),
            "telegram_configured": bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID),
            "log_level": settings.LOG_LEVEL,
            "allowed_origins": settings.ALLOWED_ORIGINS
        }
        
        logger.info("시스템 설정 조회")
        return result
        
    except Exception as e:
        logger.error(f"시스템 설정 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="시스템 설정 조회에 실패했습니다")

@router.get("/validate", response_model=dict)
async def validate_config():
    """설정 유효성 검증"""
    try:
        issues = []
        warnings = []
        
        # 필수 API 키 확인
        missing_keys = settings.validate_required_keys()
        if missing_keys:
            issues.extend([f"필수 환경 변수 누락: {key}" for key in missing_keys])
        
        # 거래 설정 검증
        if settings.TRADING_ENABLED:
            if settings.MIN_ORDER_AMOUNT < 5000:
                warnings.append("최소 주문 금액이 5,000원보다 작습니다")
            if settings.MAX_POSITION_SIZE > 1000000:
                warnings.append("최대 포지션 크기가 100만원을 초과합니다")
            if settings.STOP_LOSS_PERCENT <= 0:
                issues.append("손절매 비율이 0% 이하입니다")
            if settings.TAKE_PROFIT_PERCENT <= 0:
                issues.append("익절매 비율이 0% 이하입니다")
        
        # 실거래 모드 특별 검증
        if settings.is_live_trading:
            if not settings.UPBIT_ACCESS_KEY or settings.UPBIT_ACCESS_KEY == "your_upbit_access_key_here":
                issues.append("실거래 모드에서 Upbit API 키가 설정되지 않았습니다")
            if settings.TRADING_MODE == "live" and settings.DEBUG:
                warnings.append("실거래 모드에서 디버그 모드가 활성화되어 있습니다")
        
        result = {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "environment": settings.ENVIRONMENT,
            "trading_mode": settings.TRADING_MODE,
            "checks_passed": {
                "api_keys": len([k for k in missing_keys if "API" in k or "TOKEN" in k]) == 0,
                "trading_config": settings.TRADING_ENABLED and settings.MIN_ORDER_AMOUNT >= 5000,
                "security": not (settings.is_live_trading and settings.DEBUG)
            }
        }
        
        logger.info(f"설정 검증 완료: {'통과' if result['valid'] else '실패'}")
        return result
        
    except Exception as e:
        logger.error(f"설정 검증 실패: {e}")
        raise HTTPException(status_code=500, detail="설정 검증에 실패했습니다")

