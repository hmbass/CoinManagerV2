"""
CoinTrader API - 마켓 데이터 라우터
실시간 시장 데이터, 가격 정보 API
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict
import asyncio
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# 임시 마켓 데이터 (실제로는 Upbit API에서 가져옴)
MOCK_MARKET_DATA = [
    {
        "symbol": "KRW-BTC",
        "price": 89450000,
        "change": 2050000,
        "changePercent": 2.3
    },
    {
        "symbol": "KRW-ETH",
        "price": 2890000,
        "change": -23000,
        "changePercent": -0.8
    },
    {
        "symbol": "KRW-XRP",
        "price": 658,
        "change": 8,
        "changePercent": 1.2
    }
]

@router.get("", response_model=List[Dict])
async def get_market_data():
    """마켓 데이터 조회"""
    try:
        # 실제 구현에서는 Upbit API나 WebSocket을 통해 실시간 데이터 가져옴
        # 현재는 임시 데이터 반환
        logger.debug("마켓 데이터 조회")
        return MOCK_MARKET_DATA
        
    except Exception as e:
        logger.error(f"마켓 데이터 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="마켓 데이터 조회에 실패했습니다")

@router.get("/{symbol}", response_model=Dict)
async def get_market_by_symbol(symbol: str):
    """특정 마켓 데이터 조회"""
    try:
        # 심볼로 마켓 데이터 찾기
        market = next((m for m in MOCK_MARKET_DATA if m["symbol"] == symbol), None)
        
        if not market:
            raise HTTPException(status_code=404, detail=f"마켓을 찾을 수 없습니다: {symbol}")
        
        logger.debug(f"마켓 데이터 조회: {symbol}")
        return market
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"마켓 데이터 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="마켓 데이터 조회에 실패했습니다")

