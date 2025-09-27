"""
CoinTrader 거래 데이터 저장소
거래 기록의 생성, 조회, 수정, 삭제를 담당하는 모듈
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func

from ..connection import get_db
from ..models import Trade, TradingConfig, Portfolio, SystemLog
from ...utils.logger import setup_logger

class TradeRepository:
    """
    거래 데이터 저장소
    
    주요 기능:
    - 거래 기록 저장 및 조회
    - 거래 통계 계산
    - 성과 분석 데이터 제공
    - 거래 이력 관리
    """
    
    def __init__(self):
        self.logger = setup_logger("trade.repository")
    
    async def create_trade(self, trade_data: Dict[str, Any]) -> Optional[Trade]:
        """
        새로운 거래 기록 생성
        
        Args:
            trade_data: 거래 정보 딕셔너리
            
        Returns:
            Optional[Trade]: 생성된 거래 객체 또는 None
        """
        try:
            db = next(get_db())
            
            # 거래 객체 생성
            trade = Trade(
                market=trade_data.get('market'),
                side=trade_data.get('side'),
                order_type=trade_data.get('order_type', 'market'),
                price=float(trade_data.get('price', 0)),
                volume=float(trade_data.get('volume', 0)),
                amount=float(trade_data.get('amount', 0)),
                fee=float(trade_data.get('fee', 0)),
                strategy=trade_data.get('strategy'),
                upbit_uuid=trade_data.get('upbit_uuid'),
                profit_loss=float(trade_data.get('profit_loss', 0)),
                profit_rate=float(trade_data.get('profit_rate', 0)),
                notes=trade_data.get('notes')
            )
            
            db.add(trade)
            db.commit()
            db.refresh(trade)
            
            self.logger.info(f"거래 기록 생성: {trade.id} - {trade.market} {trade.side}")
            return trade
            
        except Exception as e:
            self.logger.error(f"거래 기록 생성 오류: {e}")
            db.rollback()
            return None
        finally:
            db.close()
    
    async def get_trade_by_id(self, trade_id: int) -> Optional[Trade]:
        """거래 ID로 조회"""
        try:
            db = next(get_db())
            trade = db.query(Trade).filter(Trade.id == trade_id).first()
            return trade
            
        except Exception as e:
            self.logger.error(f"거래 조회 오류: {e}")
            return None
        finally:
            db.close()
    
    async def get_trade_by_uuid(self, upbit_uuid: str) -> Optional[Trade]:
        """Upbit UUID로 조회"""
        try:
            db = next(get_db())
            trade = db.query(Trade).filter(Trade.upbit_uuid == upbit_uuid).first()
            return trade
            
        except Exception as e:
            self.logger.error(f"거래 UUID 조회 오류: {e}")
            return None
        finally:
            db.close()
    
    async def get_trades_by_market(self, market: str, limit: int = 100) -> List[Trade]:
        """마켓별 거래 기록 조회"""
        try:
            db = next(get_db())
            trades = (db.query(Trade)
                     .filter(Trade.market == market)
                     .order_by(desc(Trade.created_at))
                     .limit(limit)
                     .all())
            return trades
            
        except Exception as e:
            self.logger.error(f"마켓별 거래 조회 오류: {e}")
            return []
        finally:
            db.close()
    
    async def get_trades_by_date(self, target_date: date) -> List[Dict[str, Any]]:
        """특정 날짜의 거래 기록 조회"""
        try:
            db = next(get_db())
            
            start_datetime = datetime.combine(target_date, datetime.min.time())
            end_datetime = datetime.combine(target_date, datetime.max.time())
            
            trades = (db.query(Trade)
                     .filter(and_(
                         Trade.created_at >= start_datetime,
                         Trade.created_at <= end_datetime
                     ))
                     .order_by(desc(Trade.created_at))
                     .all())
            
            # 딕셔너리 형태로 변환
            trade_list = []
            for trade in trades:
                trade_dict = {
                    'id': trade.id,
                    'market': trade.market,
                    'side': trade.side,
                    'order_type': trade.order_type,
                    'price': trade.price,
                    'volume': trade.volume,
                    'amount': trade.amount,
                    'fee': trade.fee,
                    'strategy': trade.strategy,
                    'upbit_uuid': trade.upbit_uuid,
                    'profit_loss': trade.profit_loss,
                    'profit_rate': trade.profit_rate,
                    'notes': trade.notes,
                    'created_at': trade.created_at,
                    'updated_at': trade.updated_at
                }
                trade_list.append(trade_dict)
            
            return trade_list
            
        except Exception as e:
            self.logger.error(f"날짜별 거래 조회 오류: {e}")
            return []
        finally:
            db.close()
    
    async def get_recent_trades(self, days: int = 7, limit: int = 1000) -> List[Dict[str, Any]]:
        """최근 거래 기록 조회"""
        try:
            db = next(get_db())
            
            start_date = datetime.now() - timedelta(days=days)
            
            trades = (db.query(Trade)
                     .filter(Trade.created_at >= start_date)
                     .order_by(desc(Trade.created_at))
                     .limit(limit)
                     .all())
            
            # 딕셔너리 형태로 변환
            trade_list = []
            for trade in trades:
                trade_dict = {
                    'id': trade.id,
                    'market': trade.market,
                    'side': trade.side,
                    'order_type': trade.order_type,
                    'price': trade.price,
                    'volume': trade.volume,
                    'amount': trade.amount,
                    'fee': trade.fee,
                    'strategy': trade.strategy,
                    'upbit_uuid': trade.upbit_uuid,
                    'profit_loss': trade.profit_loss,
                    'profit_rate': trade.profit_rate,
                    'notes': trade.notes,
                    'created_at': trade.created_at,
                    'updated_at': trade.updated_at
                }
                trade_list.append(trade_dict)
            
            return trade_list
            
        except Exception as e:
            self.logger.error(f"최근 거래 조회 오류: {e}")
            return []
        finally:
            db.close()
    
    async def get_trades_by_strategy(self, strategy: str, days: int = 30) -> List[Trade]:
        """전략별 거래 기록 조회"""
        try:
            db = next(get_db())
            
            start_date = datetime.now() - timedelta(days=days)
            
            trades = (db.query(Trade)
                     .filter(and_(
                         Trade.strategy == strategy,
                         Trade.created_at >= start_date
                     ))
                     .order_by(desc(Trade.created_at))
                     .all())
            
            return trades
            
        except Exception as e:
            self.logger.error(f"전략별 거래 조회 오류: {e}")
            return []
        finally:
            db.close()
    
    async def update_trade_profit(self, trade_id: int, profit_loss: float, profit_rate: float) -> bool:
        """거래 손익 업데이트"""
        try:
            db = next(get_db())
            
            trade = db.query(Trade).filter(Trade.id == trade_id).first()
            if trade:
                trade.profit_loss = profit_loss
                trade.profit_rate = profit_rate
                trade.updated_at = datetime.now()
                
                db.commit()
                
                self.logger.info(f"거래 손익 업데이트: {trade_id} - {profit_loss:+,.0f}원")
                return True
            else:
                self.logger.warning(f"거래를 찾을 수 없음: {trade_id}")
                return False
            
        except Exception as e:
            self.logger.error(f"거래 손익 업데이트 오류: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    async def get_daily_statistics(self, target_date: date) -> Dict[str, Any]:
        """일일 거래 통계"""
        try:
            db = next(get_db())
            
            start_datetime = datetime.combine(target_date, datetime.min.time())
            end_datetime = datetime.combine(target_date, datetime.max.time())
            
            # 기본 통계
            total_trades = (db.query(func.count(Trade.id))
                           .filter(and_(
                               Trade.created_at >= start_datetime,
                               Trade.created_at <= end_datetime
                           ))
                           .scalar()) or 0
            
            total_amount = (db.query(func.sum(Trade.amount))
                           .filter(and_(
                               Trade.created_at >= start_datetime,
                               Trade.created_at <= end_datetime
                           ))
                           .scalar()) or 0
            
            # 매수/매도 분리 통계
            buy_trades = (db.query(func.count(Trade.id))
                         .filter(and_(
                             Trade.created_at >= start_datetime,
                             Trade.created_at <= end_datetime,
                             Trade.side == 'buy'
                         ))
                         .scalar()) or 0
            
            sell_trades = (db.query(func.count(Trade.id))
                          .filter(and_(
                              Trade.created_at >= start_datetime,
                              Trade.created_at <= end_datetime,
                              Trade.side == 'sell'
                          ))
                          .scalar()) or 0
            
            # 손익 통계 (매도 거래만)
            total_profit = (db.query(func.sum(Trade.profit_loss))
                           .filter(and_(
                               Trade.created_at >= start_datetime,
                               Trade.created_at <= end_datetime,
                               Trade.side == 'sell'
                           ))
                           .scalar()) or 0
            
            winning_trades = (db.query(func.count(Trade.id))
                             .filter(and_(
                                 Trade.created_at >= start_datetime,
                                 Trade.created_at <= end_datetime,
                                 Trade.side == 'sell',
                                 Trade.profit_loss > 0
                             ))
                             .scalar()) or 0
            
            losing_trades = (db.query(func.count(Trade.id))
                            .filter(and_(
                                Trade.created_at >= start_datetime,
                                Trade.created_at <= end_datetime,
                                Trade.side == 'sell',
                                Trade.profit_loss < 0
                            ))
                            .scalar()) or 0
            
            # 승률 계산
            win_rate = (winning_trades / max(sell_trades, 1)) * 100
            
            # 수익률 계산
            profit_rate = (total_profit / max(total_amount, 1)) * 100
            
            return {
                'date': target_date.isoformat(),
                'total_trades': total_trades,
                'buy_trades': buy_trades,
                'sell_trades': sell_trades,
                'total_amount': float(total_amount),
                'total_profit': float(total_profit),
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'profit_rate': profit_rate
            }
            
        except Exception as e:
            self.logger.error(f"일일 통계 조회 오류: {e}")
            return {}
        finally:
            db.close()
    
    async def get_strategy_performance(self, days: int = 30) -> Dict[str, Dict[str, Any]]:
        """전략별 성과 분석"""
        try:
            db = next(get_db())
            
            start_date = datetime.now() - timedelta(days=days)
            
            # 전략별 통계 쿼리
            strategy_stats = (db.query(
                Trade.strategy,
                func.count(Trade.id).label('total_trades'),
                func.sum(Trade.amount).label('total_amount'),
                func.sum(Trade.profit_loss).label('total_profit'),
                func.count(Trade.id).filter(Trade.profit_loss > 0).label('winning_trades'),
                func.count(Trade.id).filter(Trade.profit_loss < 0).label('losing_trades')
            )
            .filter(and_(
                Trade.created_at >= start_date,
                Trade.side == 'sell'
            ))
            .group_by(Trade.strategy)
            .all())
            
            strategy_performance = {}
            
            for stat in strategy_stats:
                strategy_name = stat.strategy or 'unknown'
                total_trades = stat.total_trades or 0
                total_amount = float(stat.total_amount or 0)
                total_profit = float(stat.total_profit or 0)
                winning_trades = stat.winning_trades or 0
                losing_trades = stat.losing_trades or 0
                
                win_rate = (winning_trades / max(total_trades, 1)) * 100
                profit_rate = (total_profit / max(total_amount, 1)) * 100
                
                strategy_performance[strategy_name] = {
                    'total_trades': total_trades,
                    'total_amount': total_amount,
                    'total_profit': total_profit,
                    'winning_trades': winning_trades,
                    'losing_trades': losing_trades,
                    'win_rate': win_rate,
                    'profit_rate': profit_rate
                }
            
            return strategy_performance
            
        except Exception as e:
            self.logger.error(f"전략별 성과 분석 오류: {e}")
            return {}
        finally:
            db.close()
    
    async def get_market_performance(self, days: int = 30) -> Dict[str, Dict[str, Any]]:
        """마켓별 성과 분석"""
        try:
            db = next(get_db())
            
            start_date = datetime.now() - timedelta(days=days)
            
            # 마켓별 통계 쿼리
            market_stats = (db.query(
                Trade.market,
                func.count(Trade.id).label('total_trades'),
                func.sum(Trade.amount).label('total_amount'),
                func.sum(Trade.profit_loss).label('total_profit'),
                func.count(Trade.id).filter(Trade.profit_loss > 0).label('winning_trades'),
                func.count(Trade.id).filter(Trade.profit_loss < 0).label('losing_trades')
            )
            .filter(and_(
                Trade.created_at >= start_date,
                Trade.side == 'sell'
            ))
            .group_by(Trade.market)
            .all())
            
            market_performance = {}
            
            for stat in market_stats:
                market_name = stat.market
                total_trades = stat.total_trades or 0
                total_amount = float(stat.total_amount or 0)
                total_profit = float(stat.total_profit or 0)
                winning_trades = stat.winning_trades or 0
                losing_trades = stat.losing_trades or 0
                
                win_rate = (winning_trades / max(total_trades, 1)) * 100
                profit_rate = (total_profit / max(total_amount, 1)) * 100
                
                market_performance[market_name] = {
                    'total_trades': total_trades,
                    'total_amount': total_amount,
                    'total_profit': total_profit,
                    'winning_trades': winning_trades,
                    'losing_trades': losing_trades,
                    'win_rate': win_rate,
                    'profit_rate': profit_rate
                }
            
            return market_performance
            
        except Exception as e:
            self.logger.error(f"마켓별 성과 분석 오류: {e}")
            return {}
        finally:
            db.close()
    
    async def get_hourly_trading_volume(self, days: int = 7) -> List[Dict[str, Any]]:
        """시간대별 거래량 분석"""
        try:
            db = next(get_db())
            
            start_date = datetime.now() - timedelta(days=days)
            
            # 시간대별 거래량 쿼리
            hourly_volume = (db.query(
                func.extract('hour', Trade.created_at).label('hour'),
                func.count(Trade.id).label('trade_count'),
                func.sum(Trade.amount).label('total_amount')
            )
            .filter(Trade.created_at >= start_date)
            .group_by(func.extract('hour', Trade.created_at))
            .order_by(func.extract('hour', Trade.created_at))
            .all())
            
            hourly_data = []
            for hour_stat in hourly_volume:
                hourly_data.append({
                    'hour': int(hour_stat.hour),
                    'trade_count': hour_stat.trade_count or 0,
                    'total_amount': float(hour_stat.total_amount or 0)
                })
            
            return hourly_data
            
        except Exception as e:
            self.logger.error(f"시간대별 거래량 분석 오류: {e}")
            return []
        finally:
            db.close()
    
    async def delete_old_trades(self, days: int = 365) -> int:
        """오래된 거래 기록 삭제"""
        try:
            db = next(get_db())
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            deleted_count = (db.query(Trade)
                           .filter(Trade.created_at < cutoff_date)
                           .delete())
            
            db.commit()
            
            self.logger.info(f"오래된 거래 기록 삭제: {deleted_count}건")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"거래 기록 삭제 오류: {e}")
            db.rollback()
            return 0
        finally:
            db.close()
    
    def get_statistics(self) -> Dict[str, Any]:
        """저장소 통계"""
        try:
            db = next(get_db())
            
            total_trades = db.query(func.count(Trade.id)).scalar() or 0
            today_trades = (db.query(func.count(Trade.id))
                           .filter(func.date(Trade.created_at) == date.today())
                           .scalar()) or 0
            
            return {
                'total_trades': total_trades,
                'today_trades': today_trades,
                'last_trade': db.query(func.max(Trade.created_at)).scalar()
            }
            
        except Exception as e:
            self.logger.error(f"저장소 통계 조회 오류: {e}")
            return {}
        finally:
            db.close()

