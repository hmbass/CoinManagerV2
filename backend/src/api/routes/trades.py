"""
CoinTrader API - 거래 관련 라우터
거래 기록 조회, 생성, 분석 API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from ...database.connection import get_db
from ...database.models import Trade
from ...utils.logger import setup_logger

router = APIRouter()
logger = setup_logger("api.trades")

@router.get("/", response_model=List[dict])
async def get_trades(
    skip: int = Query(0, ge=0, description="건너뛸 항목 수"),
    limit: int = Query(100, ge=1, le=1000, description="조회할 항목 수"),
    market: Optional[str] = Query(None, description="마켓 필터 (예: KRW-BTC)"),
    side: Optional[str] = Query(None, description="거래 구분 (buy/sell)"),
    strategy: Optional[str] = Query(None, description="전략 필터"),
    start_date: Optional[datetime] = Query(None, description="시작 날짜"),
    end_date: Optional[datetime] = Query(None, description="종료 날짜"),
    db: Session = Depends(get_db)
):
    """거래 기록 목록 조회"""
    try:
        query = db.query(Trade)
        
        # 필터 적용
        if market:
            query = query.filter(Trade.market == market)
        if side:
            query = query.filter(Trade.side == side)
        if strategy:
            query = query.filter(Trade.strategy == strategy)
        if start_date:
            query = query.filter(Trade.created_at >= start_date)
        if end_date:
            query = query.filter(Trade.created_at <= end_date)
        
        # 정렬 및 페이징
        trades = query.order_by(Trade.created_at.desc()).offset(skip).limit(limit).all()
        
        # 응답 데이터 변환
        result = []
        for trade in trades:
            result.append({
                "id": trade.id,
                "market": trade.market,
                "side": trade.side,
                "order_type": trade.order_type,
                "price": trade.price,
                "volume": trade.volume,
                "amount": trade.amount,
                "fee": trade.fee,
                "strategy": trade.strategy,
                "profit_loss": trade.profit_loss,
                "profit_rate": trade.profit_rate,
                "created_at": trade.created_at.isoformat(),
                "notes": trade.notes
            })
        
        logger.info(f"거래 기록 조회: {len(result)}건 (필터: market={market}, side={side})")
        return result
        
    except Exception as e:
        logger.error(f"거래 기록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="거래 기록 조회에 실패했습니다")

@router.get("/{trade_id}", response_model=dict)
async def get_trade(
    trade_id: int,
    db: Session = Depends(get_db)
):
    """특정 거래 기록 조회"""
    try:
        trade = db.query(Trade).filter(Trade.id == trade_id).first()
        
        if not trade:
            raise HTTPException(status_code=404, detail="거래 기록을 찾을 수 없습니다")
        
        result = {
            "id": trade.id,
            "market": trade.market,
            "side": trade.side,
            "order_type": trade.order_type,
            "price": trade.price,
            "volume": trade.volume,
            "amount": trade.amount,
            "fee": trade.fee,
            "strategy": trade.strategy,
            "profit_loss": trade.profit_loss,
            "profit_rate": trade.profit_rate,
            "upbit_uuid": trade.upbit_uuid,
            "created_at": trade.created_at.isoformat(),
            "updated_at": trade.updated_at.isoformat() if trade.updated_at else None,
            "notes": trade.notes
        }
        
        logger.info(f"거래 기록 상세 조회: ID {trade_id}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"거래 기록 상세 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="거래 기록 조회에 실패했습니다")

@router.get("/stats/summary", response_model=dict)
async def get_trade_summary(
    days: int = Query(30, ge=1, le=365, description="조회 일수"),
    market: Optional[str] = Query(None, description="마켓 필터"),
    db: Session = Depends(get_db)
):
    """거래 통계 요약"""
    try:
        # 기간 설정
        start_date = datetime.now() - timedelta(days=days)
        
        query = db.query(Trade).filter(Trade.created_at >= start_date)
        
        if market:
            query = query.filter(Trade.market == market)
        
        trades = query.all()
        
        if not trades:
            return {
                "total_trades": 0,
                "total_amount": 0,
                "total_profit": 0,
                "win_rate": 0,
                "avg_profit_per_trade": 0,
                "period_days": days
            }
        
        # 통계 계산
        total_trades = len(trades)
        total_amount = sum(trade.amount for trade in trades)
        total_profit = sum(trade.profit_loss for trade in trades)
        
        profitable_trades = [t for t in trades if t.profit_loss > 0]
        win_rate = (len(profitable_trades) / total_trades) * 100 if total_trades > 0 else 0
        avg_profit_per_trade = total_profit / total_trades if total_trades > 0 else 0
        
        # 마켓별 통계
        market_stats = {}
        for trade in trades:
            if trade.market not in market_stats:
                market_stats[trade.market] = {
                    "count": 0,
                    "amount": 0,
                    "profit": 0
                }
            market_stats[trade.market]["count"] += 1
            market_stats[trade.market]["amount"] += trade.amount
            market_stats[trade.market]["profit"] += trade.profit_loss
        
        result = {
            "total_trades": total_trades,
            "total_amount": total_amount,
            "total_profit": total_profit,
            "win_rate": win_rate,
            "avg_profit_per_trade": avg_profit_per_trade,
            "period_days": days,
            "market_stats": market_stats
        }
        
        logger.info(f"거래 통계 요약 조회: {days}일, {total_trades}건")
        return result
        
    except Exception as e:
        logger.error(f"거래 통계 요약 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="거래 통계 조회에 실패했습니다")

@router.get("/stats/daily", response_model=List[dict])
async def get_daily_stats(
    days: int = Query(30, ge=1, le=365, description="조회 일수"),
    market: Optional[str] = Query(None, description="마켓 필터"),
    db: Session = Depends(get_db)
):
    """일별 거래 통계"""
    try:
        # 기간 설정
        start_date = datetime.now() - timedelta(days=days)
        
        query = db.query(Trade).filter(Trade.created_at >= start_date)
        
        if market:
            query = query.filter(Trade.market == market)
        
        trades = query.all()
        
        # 일별 그룹화
        daily_stats = {}
        for trade in trades:
            date_key = trade.created_at.date().isoformat()
            
            if date_key not in daily_stats:
                daily_stats[date_key] = {
                    "date": date_key,
                    "trade_count": 0,
                    "total_amount": 0,
                    "total_profit": 0,
                    "win_count": 0,
                    "loss_count": 0
                }
            
            daily_stats[date_key]["trade_count"] += 1
            daily_stats[date_key]["total_amount"] += trade.amount
            daily_stats[date_key]["total_profit"] += trade.profit_loss
            
            if trade.profit_loss > 0:
                daily_stats[date_key]["win_count"] += 1
            elif trade.profit_loss < 0:
                daily_stats[date_key]["loss_count"] += 1
        
        # 승률 계산
        for stats in daily_stats.values():
            total = stats["win_count"] + stats["loss_count"]
            stats["win_rate"] = (stats["win_count"] / total * 100) if total > 0 else 0
        
        # 날짜순 정렬
        result = sorted(daily_stats.values(), key=lambda x: x["date"])
        
        logger.info(f"일별 거래 통계 조회: {days}일, {len(result)}일 데이터")
        return result
        
    except Exception as e:
        logger.error(f"일별 거래 통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="일별 통계 조회에 실패했습니다")

