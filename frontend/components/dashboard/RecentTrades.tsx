'use client';

import { useTrades } from '@/hooks/useApi';

export function RecentTrades() {
  const { trades, loading, error } = useTrades(5);

  if (loading) {
    return (
      <div className="rounded-lg border bg-card text-card-foreground shadow-sm">
        <div className="p-6">
          <h3 className="text-lg font-semibold">최근 거래</h3>
          <p className="text-sm text-muted-foreground">최근 24시간 거래 내역</p>
        </div>
        <div className="p-6 pt-0">
          <div className="space-y-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="h-8 w-8 bg-muted animate-pulse rounded-full" />
                  <div className="space-y-1">
                    <div className="h-4 w-16 bg-muted animate-pulse rounded" />
                    <div className="h-3 w-24 bg-muted animate-pulse rounded" />
                  </div>
                </div>
                <div className="text-right space-y-1">
                  <div className="h-4 w-20 bg-muted animate-pulse rounded" />
                  <div className="h-3 w-12 bg-muted animate-pulse rounded" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border bg-card text-card-foreground shadow-sm">
        <div className="p-6">
          <h3 className="text-lg font-semibold">최근 거래</h3>
          <p className="text-sm text-muted-foreground">최근 24시간 거래 내역</p>
        </div>
        <div className="p-6 pt-0">
          <div className="text-center text-muted-foreground">
            <p>데이터 로딩 오류</p>
            <p className="text-sm text-red-500">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  if (!trades || trades.length === 0) {
    return (
      <div className="rounded-lg border bg-card text-card-foreground shadow-sm">
        <div className="p-6">
          <h3 className="text-lg font-semibold">최근 거래</h3>
          <p className="text-sm text-muted-foreground">최근 24시간 거래 내역</p>
        </div>
        <div className="p-6 pt-0">
          <div className="text-center text-muted-foreground">
            <p>거래 내역이 없습니다</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border bg-card text-card-foreground shadow-sm">
      <div className="p-6">
        <h3 className="text-lg font-semibold">최근 거래</h3>
        <p className="text-sm text-muted-foreground">최근 24시간 거래 내역</p>
      </div>
      <div className="p-6 pt-0">
        <div className="space-y-4">
          {trades.map((trade) => (
            <div key={trade.id} className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className={`h-8 w-8 rounded-full flex items-center justify-center ${
                  trade.side === 'buy' ? 'bg-green-100' : 'bg-red-100'
                }`}>
                  <span className={`text-xs font-medium ${
                    trade.side === 'buy' ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {trade.side === 'buy' ? '매수' : '매도'}
                  </span>
                </div>
                <div>
                  <div className="font-medium">{trade.market}</div>
                  <div className="text-sm text-muted-foreground">
                    {new Date(trade.created_at).toLocaleString('ko-KR')}
                  </div>
                </div>
              </div>
              <div className="text-right">
                <div className="font-mono">{trade.price.toLocaleString()}원</div>
                {trade.profit_loss !== undefined && (
                  <div className={`text-sm ${
                    trade.profit_loss >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {trade.profit_loss >= 0 ? '+' : ''}{trade.profit_loss.toLocaleString()}원
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

