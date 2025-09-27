"""
CoinTrader Backend - 로깅 유틸리티
구조화된 로깅 시스템
"""
import logging
import logging.handlers
import sys
from pathlib import Path
from datetime import datetime
import json
from typing import Dict, Any, Optional

from ..config import settings

class CoinTraderFormatter(logging.Formatter):
    """CoinTrader 전용 로그 포맷터"""
    
    def __init__(self):
        super().__init__()
        
    def format(self, record: logging.LogRecord) -> str:
        # 기본 정보
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # 예외 정보 추가
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        # 추가 컨텍스트 정보
        if hasattr(record, 'extra_data'):
            log_data.update(record.extra_data)
            
        # 개발 모드에서는 읽기 쉬운 형태로
        if settings.DEBUG:
            timestamp = log_data["timestamp"]
            level = log_data["level"]
            logger_name = log_data["logger"]
            message = log_data["message"]
            
            # 색상 코드
            colors = {
                'DEBUG': '\033[36m',    # 청록색
                'INFO': '\033[32m',     # 녹색
                'WARNING': '\033[33m',  # 노란색
                'ERROR': '\033[31m',    # 빨간색
                'CRITICAL': '\033[35m', # 자주색
                'RESET': '\033[0m'      # 리셋
            }
            
            color = colors.get(level, colors['RESET'])
            reset = colors['RESET']
            
            formatted = f"{color}[{timestamp}] [{level}] {logger_name}: {message}{reset}"
            
            if record.exc_info:
                formatted += f"\n{log_data['exception']}"
                
            return formatted
        else:
            # 프로덕션에서는 JSON 형태로
            return json.dumps(log_data, ensure_ascii=False)

class CoinTraderLogger:
    """CoinTrader 로거 관리 클래스"""
    
    def __init__(self):
        self.loggers: Dict[str, logging.Logger] = {}
        self._setup_root_logger()
        
    def _setup_root_logger(self):
        """루트 로거 설정"""
        # 로그 디렉토리 생성
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # 루트 로거 설정
        root_logger = logging.getLogger("cointrader")
        root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
        
        # 기존 핸들러 제거
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            
        # 콘솔 핸들러
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
        console_handler.setFormatter(CoinTraderFormatter())
        root_logger.addHandler(console_handler)
        
        # 파일 핸들러 (일반 로그)
        file_handler = logging.handlers.RotatingFileHandler(
            settings.LOG_FILE,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(CoinTraderFormatter())
        root_logger.addHandler(file_handler)
        
        # 에러 전용 파일 핸들러
        error_handler = logging.handlers.RotatingFileHandler(
            "logs/errors.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(CoinTraderFormatter())
        root_logger.addHandler(error_handler)
        
        # 거래 전용 로그 핸들러
        trade_handler = logging.handlers.RotatingFileHandler(
            "logs/trades.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=10,
            encoding='utf-8'
        )
        trade_handler.setLevel(logging.INFO)
        trade_handler.setFormatter(CoinTraderFormatter())
        
        # 거래 로거 별도 설정
        trade_logger = logging.getLogger("cointrader.trading")
        trade_logger.addHandler(trade_handler)
        trade_logger.setLevel(logging.INFO)
        
    def get_logger(self, name: str) -> logging.Logger:
        """로거 인스턴스 반환"""
        if name not in self.loggers:
            # cointrader 네임스페이스 하위로 생성
            full_name = f"cointrader.{name}" if not name.startswith("cointrader") else name
            self.loggers[name] = logging.getLogger(full_name)
            
        return self.loggers[name]

# 전역 로거 매니저
_logger_manager = CoinTraderLogger()

def setup_logger(name: str) -> logging.Logger:
    """로거 설정 및 반환"""
    return _logger_manager.get_logger(name)

def get_logger(name: str) -> logging.Logger:
    """로거 인스턴스 반환"""
    return _logger_manager.get_logger(name)

# 특별한 로깅 함수들
def log_trade(
    side: str,
    market: str,
    price: float,
    volume: float,
    amount: float,
    strategy: str = "",
    **kwargs
):
    """거래 로그 기록"""
    trade_logger = get_logger("trading")
    
    trade_data = {
        "event": "trade",
        "side": side,
        "market": market,
        "price": price,
        "volume": volume,
        "amount": amount,
        "strategy": strategy,
        **kwargs
    }
    
    # LogRecord에 extra_data 추가
    record = logging.LogRecord(
        name=trade_logger.name,
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg=f"거래 체결: {side.upper()} {market} {amount:,.0f}원",
        args=(),
        exc_info=None
    )
    record.extra_data = trade_data
    
    trade_logger.handle(record)

def log_error(
    error: Exception,
    context: str = "",
    extra_data: Optional[Dict[str, Any]] = None
):
    """에러 로그 기록"""
    logger = get_logger("error")
    
    error_data = {
        "event": "error",
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": context
    }
    
    if extra_data:
        error_data.update(extra_data)
    
    record = logging.LogRecord(
        name=logger.name,
        level=logging.ERROR,
        pathname="",
        lineno=0,
        msg=f"오류 발생: {error}",
        args=(),
        exc_info=(type(error), error, error.__traceback__)
    )
    record.extra_data = error_data
    
    logger.handle(record)

def log_system_event(
    event: str,
    message: str,
    level: str = "INFO",
    extra_data: Optional[Dict[str, Any]] = None
):
    """시스템 이벤트 로그 기록"""
    logger = get_logger("system")
    
    system_data = {
        "event": event,
        "timestamp": datetime.now().isoformat()
    }
    
    if extra_data:
        system_data.update(extra_data)
    
    log_level = getattr(logging, level.upper())
    
    record = logging.LogRecord(
        name=logger.name,
        level=log_level,
        pathname="",
        lineno=0,
        msg=message,
        args=(),
        exc_info=None
    )
    record.extra_data = system_data
    
    logger.handle(record)

# 성능 로깅 데코레이터
import functools
import time

def log_performance(logger_name: str = "performance"):
    """성능 로깅 데코레이터"""
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_logger(logger_name)
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                logger.info(
                    f"함수 실행 완료: {func.__name__} ({execution_time:.3f}초)",
                    extra={"extra_data": {
                        "event": "performance",
                        "function": func.__name__,
                        "execution_time": execution_time,
                        "status": "success"
                    }}
                )
                
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                
                logger.error(
                    f"함수 실행 실패: {func.__name__} ({execution_time:.3f}초) - {e}",
                    extra={"extra_data": {
                        "event": "performance",
                        "function": func.__name__,
                        "execution_time": execution_time,
                        "status": "error",
                        "error": str(e)
                    }}
                )
                
                raise
                
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = get_logger(logger_name)
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                logger.info(
                    f"함수 실행 완료: {func.__name__} ({execution_time:.3f}초)",
                    extra={"extra_data": {
                        "event": "performance",
                        "function": func.__name__,
                        "execution_time": execution_time,
                        "status": "success"
                    }}
                )
                
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                
                logger.error(
                    f"함수 실행 실패: {func.__name__} ({execution_time:.3f}초) - {e}",
                    extra={"extra_data": {
                        "event": "performance",
                        "function": func.__name__,
                        "execution_time": execution_time,
                        "status": "error",
                        "error": str(e)
                    }}
                )
                
                raise
                
        if asyncio and asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
            
    return decorator

