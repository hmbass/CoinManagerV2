"""
CoinTrader API - 분석 및 성과 라우터
거래 성과 분석, 차트 데이터, 통계 API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json

from ...database.connection import get_db
from ...database.models import Trade, Portfolio, PerformanceMetrics
from ...utils.logger import setup_logger

router = APIRouter()
logger = setup_logger("api.analytics")

@router.get("/performance", response_model=dict)
async def get_performance_summary(
    days: int = Query(30, ge=1, le=365, description="조회 일수"),
    market: Optional[str] = Query(None, description="마켓 필터"),
    db: Session = Depends(get_db)
):
    """성과 요약 조회"""
    try:
        # 기간 설정
        start_date = datetime.now() - timedelta(days=days)
        
        query = db.query(Trade).filter(Trade.created_at >= start_date)
        if market:
            query = query.filter(Trade.market == market)
        
        trades = query.all()
        
        if not trades:
            return {
                "period_days": days,
                "total_trades": 0,
                "total_profit": 0,
                "total_profit_rate": 0,
                "win_rate": 0,
                "profit_factor": 0,
                "max_drawdown": 0,
                "sharpe_ratio": 0,
                "avg_profit_per_trade": 0,
                "best_trade": 0,
                "worst_trade": 0
            }
        
        # 기본 통계
        total_trades = len(trades)
        total_profit = sum(t.profit_loss for t in trades if t.profit_loss)
        
        winning_trades = [t for t in trades if t.profit_loss > 0]
        losing_trades = [t for t in trades if t.profit_loss < 0]
        
        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0
        
        # 수익률 계산
        total_invested = sum(t.amount for t in trades if t.side == "buy")
        total_profit_rate = (total_profit / total_invested * 100) if total_invested > 0 else 0
        
        # Profit Factor (총 수익 / 총 손실)
        total_wins = sum(t.profit_loss for t in winning_trades)
        total_losses = abs(sum(t.profit_loss for t in losing_trades))
        profit_factor = (total_wins / total_losses) if total_losses > 0 else float('inf')
        
        # 최대 낙폭 계산 (간단 버전)
        cumulative_profit = 0
        peak = 0
        max_drawdown = 0
        
        for trade in sorted(trades, key=lambda x: x.created_at):
            if trade.profit_loss:
                cumulative_profit += trade.profit_loss
                if cumulative_profit > peak:
                    peak = cumulative_profit
                drawdown = (peak - cumulative_profit) / peak * 100 if peak > 0 else 0
                max_drawdown = max(max_drawdown, drawdown)
        
        # 기타 통계
        avg_profit_per_trade = total_profit / total_trades if total_trades > 0 else 0
        best_trade = max(t.profit_loss for t in trades if t.profit_loss) if trades else 0
        worst_trade = min(t.profit_loss for t in trades if t.profit_loss) if trades else 0
        
        # 샤프 비율 (간단 버전)
        profit_list = [t.profit_loss for t in trades if t.profit_loss]
        if len(profit_list) > 1:
            import statistics
            mean_return = statistics.mean(profit_list)
            std_return = statistics.stdev(profit_list)
            sharpe_ratio = (mean_return / std_return) if std_return > 0 else 0
        else:
            sharpe_ratio = 0
        
        result = {
            "period_days": days,
            "total_trades": total_trades,
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "total_profit": total_profit,
            "total_profit_rate": total_profit_rate,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe_ratio,
            "avg_profit_per_trade": avg_profit_per_trade,
            "best_trade": best_trade,
            "worst_trade": worst_trade,
            "total_invested": total_invested
        }
        
        logger.info(f"성과 요약 조회: {days}일, {total_trades}건")
        return result
        
    except Exception as e:
        logger.error(f"성과 요약 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="성과 분석에 실패했습니다")

@router.get("/equity-curve", response_model=List[dict])
async def get_equity_curve(
    days: int = Query(30, ge=1, le=365, description="조회 일수"),
    market: Optional[str] = Query(None, description="마켓 필터"),
    db: Session = Depends(get_db)
):
    """에쿼티 커브 데이터"""
    try:
        # 기간 설정
        start_date = datetime.now() - timedelta(days=days)
        
        query = db.query(Trade).filter(Trade.created_at >= start_date)
        if market:
            query = query.filter(Trade.market == market)
        
        trades = query.order_by(Trade.created_at).all()
        
        if not trades:
            return []
        
        # 누적 수익 계산
        equity_data = []
        cumulative_profit = 0
        initial_balance = 1000000  # 기본 시작 자본
        
        for trade in trades:
            if trade.profit_loss:
                cumulative_profit += trade.profit_loss
            
            equity_data.append({
                "date": trade.created_at.isoformat(),
                "equity": initial_balance + cumulative_profit,
                "profit": cumulative_profit,
                "trade_id": trade.id,
                "market": trade.market,
                "side": trade.side,
                "amount": trade.amount
            })
        
        logger.info(f"에쿼티 커브 조회: {days}일, {len(equity_data)}포인트")
        return equity_data
        
    except Exception as e:
        logger.error(f"에쿼티 커브 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="에쿼티 커브 조회에 실패했습니다")

@router.get("/portfolio", response_model=dict)
async def get_portfolio_status(db: Session = Depends(get_db)):
    """현재 포트폴리오 상태"""
    try:
        portfolios = db.query(Portfolio).all()
        
        total_value = 0
        total_profit = 0
        positions = []
        
        for portfolio in portfolios:
            if portfolio.volume > 0:  # 보유 중인 포지션만
                position_value = portfolio.volume * (portfolio.avg_buy_price or 0)
                total_value += position_value
                total_profit += portfolio.realized_profit + portfolio.unrealized_profit
                
                positions.append({
                    "market": portfolio.market,
                    "volume": portfolio.volume,
                    "avg_buy_price": portfolio.avg_buy_price,
                    "position_value": position_value,
                    "unrealized_profit": portfolio.unrealized_profit,
                    "realized_profit": portfolio.realized_profit,
                    "total_profit": portfolio.total_profit,
                    "profit_rate": portfolio.profit_rate,
                    "buy_count": portfolio.buy_count,
                    "sell_count": portfolio.sell_count,
                    "win_count": portfolio.win_count,
                    "loss_count": portfolio.loss_count
                })
        
        result = {
            "total_positions": len(positions),
            "total_portfolio_value": total_value,
            "total_profit": total_profit,
            "positions": positions,
            "updated_at": datetime.now().isoformat()
        }
        
        logger.info(f"포트폴리오 상태 조회: {len(positions)}개 포지션")
        return result
        
    except Exception as e:
        logger.error(f"포트폴리오 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="포트폴리오 조회에 실패했습니다")

@router.get("/market-analysis", response_model=dict)
async def get_market_analysis(
    days: int = Query(30, ge=1, le=365, description="조회 일수"),
    db: Session = Depends(get_db)
):
    """마켓별 분석"""
    try:
        # 기간 설정
        start_date = datetime.now() - timedelta(days=days)
        
        trades = db.query(Trade).filter(Trade.created_at >= start_date).all()
        
        if not trades:
            return {"markets": [], "period_days": days}
        
        # 마켓별 그룹화
        market_stats = {}
        for trade in trades:
            if trade.market not in market_stats:
                market_stats[trade.market] = {
                    "market": trade.market,
                    "total_trades": 0,
                    "buy_trades": 0,
                    "sell_trades": 0,
                    "total_volume": 0,
                    "total_profit": 0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "best_trade": 0,
                    "worst_trade": 0
                }
            
            stats = market_stats[trade.market]
            stats["total_trades"] += 1
            
            if trade.side == "buy":
                stats["buy_trades"] += 1
            else:
                stats["sell_trades"] += 1
            
            stats["total_volume"] += trade.amount
            
            if trade.profit_loss:
                stats["total_profit"] += trade.profit_loss
                if trade.profit_loss > 0:
                    stats["winning_trades"] += 1
                    stats["best_trade"] = max(stats["best_trade"], trade.profit_loss)
                else:
                    stats["losing_trades"] += 1
                    stats["worst_trade"] = min(stats["worst_trade"], trade.profit_loss)
        
        # 승률 및 기타 지표 계산
        for stats in market_stats.values():
            total_with_profit = stats["winning_trades"] + stats["losing_trades"]
            stats["win_rate"] = (stats["winning_trades"] / total_with_profit * 100) if total_with_profit > 0 else 0
            stats["avg_profit_per_trade"] = stats["total_profit"] / stats["total_trades"] if stats["total_trades"] > 0 else 0
            stats["profit_rate"] = (stats["total_profit"] / stats["total_volume"] * 100) if stats["total_volume"] > 0 else 0
        
        # 수익순 정렬
        markets = sorted(market_stats.values(), key=lambda x: x["total_profit"], reverse=True)
        
        result = {
            "period_days": days,
            "total_markets": len(markets),
            "markets": markets
        }
        
        logger.info(f"마켓 분석 조회: {days}일, {len(markets)}개 마켓")
        return result
        
    except Exception as e:
        logger.error(f"마켓 분석 실패: {e}")
        raise HTTPException(status_code=500, detail="마켓 분석에 실패했습니다")

@router.get("/strategy-analysis", response_model=dict)
async def get_strategy_analysis(
    days: int = Query(30, ge=1, le=365, description="조회 일수"),
    db: Session = Depends(get_db)
):
    """전략별 분석"""
    try:
        # 기간 설정
        start_date = datetime.now() - timedelta(days=days)
        
        trades = db.query(Trade).filter(
            Trade.created_at >= start_date,
            Trade.strategy.isnot(None)
        ).all()
        
        if not trades:
            return {"strategies": [], "period_days": days}
        
        # 전략별 그룹화
        strategy_stats = {}
        for trade in trades:
            strategy = trade.strategy or "unknown"
            
            if strategy not in strategy_stats:
                strategy_stats[strategy] = {
                    "strategy": strategy,
                    "total_trades": 0,
                    "total_profit": 0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "total_volume": 0,
                    "avg_holding_time": 0,  # 추후 구현
                    "markets_used": set()
                }
            
            stats = strategy_stats[strategy]
            stats["total_trades"] += 1
            stats["total_volume"] += trade.amount
            stats["markets_used"].add(trade.market)
            
            if trade.profit_loss:
                stats["total_profit"] += trade.profit_loss
                if trade.profit_loss > 0:
                    stats["winning_trades"] += 1
                else:
                    stats["losing_trades"] += 1
        
        # 승률 계산 및 set을 list로 변환
        for stats in strategy_stats.values():
            total_with_profit = stats["winning_trades"] + stats["losing_trades"]
            stats["win_rate"] = (stats["winning_trades"] / total_with_profit * 100) if total_with_profit > 0 else 0
            stats["avg_profit_per_trade"] = stats["total_profit"] / stats["total_trades"] if stats["total_trades"] > 0 else 0
            stats["profit_rate"] = (stats["total_profit"] / stats["total_volume"] * 100) if stats["total_volume"] > 0 else 0
            stats["markets_used"] = list(stats["markets_used"])
        
        # 수익순 정렬
        strategies = sorted(strategy_stats.values(), key=lambda x: x["total_profit"], reverse=True)
        
        result = {
            "period_days": days,
            "total_strategies": len(strategies),
            "strategies": strategies
        }
        
        logger.info(f"전략 분석 조회: {days}일, {len(strategies)}개 전략")
        return result
        
    except Exception as e:
        logger.error(f"전략 분석 실패: {e}")
        raise HTTPException(status_code=500, detail="전략 분석에 실패했습니다")

