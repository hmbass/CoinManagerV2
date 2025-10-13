'use client';

import { useMarketData } from '@/hooks/useApi';

export function MarketStatus() {
  const { marketData, loading, error } = useMarketData();

  if (loading) {
    return (
      <div className="rounded-lg border bg-card text-card-foreground shadow-sm">
        <div className="p-6">
          <h3 className="text-lg font-semibold">마켓 현황</h3>
          <p className="text-sm text-muted-foreground">실시간 가격 정보</p>
        </div>
        <div className="h-80 p-6 pt-0">
          <div className="h-full bg-muted rounded flex items-center justify-center">
            <p className="text-muted-foreground">데이터 로딩 중...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border bg-card text-card-foreground shadow-sm">
        <div className="p-6">
          <h3 className="text-lg font-semibold">마켓 현황</h3>
          <p className="text-sm text-muted-foreground">실시간 가격 정보</p>
        </div>
        <div className="h-80 p-6 pt-0">
          <div className="h-full bg-muted rounded flex items-center justify-center">
            <div className="text-center">
              <p className="text-muted-foreground">데이터 로딩 오류</p>
              <p className="text-sm text-red-500">{error}</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!marketData || marketData.length === 0) {
    return (
      <div className="rounded-lg border bg-card text-card-foreground shadow-sm">
        <div className="p-6">
          <h3 className="text-lg font-semibold">마켓 현황</h3>
          <p className="text-sm text-muted-foreground">실시간 가격 정보</p>
        </div>
        <div className="h-80 p-6 pt-0">
          <div className="h-full bg-muted rounded flex items-center justify-center">
            <p className="text-muted-foreground">데이터 없음</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border bg-card text-card-foreground shadow-sm">
      <div className="p-6">
        <h3 className="text-lg font-semibold">마켓 현황</h3>
        <p className="text-sm text-muted-foreground">실시간 가격 정보</p>
      </div>
      <div className="h-80 p-6 pt-0">
        <div className="space-y-4">
          {marketData.map((market, index) => (
            <div key={index} className="flex items-center justify-between">
              <span className="font-medium">{market.symbol}</span>
              <div className="text-right">
                <div className="font-mono text-lg">
                  {market.price.toLocaleString()}원
                </div>
                <div className={`text-sm ${
                  market.changePercent >= 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {market.changePercent >= 0 ? '+' : ''}{market.changePercent.toFixed(2)}%
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

