'use client';

import { usePerformance } from '@/hooks/useApi';

export function PerformanceCards() {
  const { data, loading, error } = usePerformance();

  if (loading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-32 bg-muted animate-pulse rounded-lg" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-lg border bg-card text-card-foreground shadow-sm p-6">
          <div className="text-center text-muted-foreground">
            <p>데이터 로딩 오류</p>
            <p className="text-sm">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-lg border bg-card text-card-foreground shadow-sm p-6">
          <div className="text-center text-muted-foreground">
            <p>데이터 없음</p>
          </div>
        </div>
      </div>
    );
  }

  const cards = [
    {
      title: '총 수익',
      value: `${data.totalProfit >= 0 ? '+' : ''}${data.totalProfit.toLocaleString()}원`,
      icon: '💰',
      trend: data.totalProfit > 0 ? 'up' : 'down',
      className: data.totalProfit > 0 ? 'text-green-600' : 'text-red-600',
      subtitle: `${data.profitRate >= 0 ? '+' : ''}${data.profitRate.toFixed(2)}% 전일 대비`
    },
    {
      title: '총 거래수',
      value: data.totalTrades.toString(),
      icon: '📊',
      trend: 'neutral',
      className: '',
      subtitle: '전체 거래'
    },
    {
      title: '승률',
      value: `${data.winRate.toFixed(1)}%`,
      icon: '🎯',
      trend: data.winRate > 50 ? 'up' : 'down',
      className: data.winRate > 50 ? 'text-green-600' : 'text-red-600',
      subtitle: '최근 30일'
    },
    {
      title: '일일 수익',
      value: `${data.dailyProfit >= 0 ? '+' : ''}${data.dailyProfit.toLocaleString()}원`,
      icon: '📈',
      trend: data.dailyProfit > 0 ? 'up' : 'down',
      className: data.dailyProfit > 0 ? 'text-green-600' : 'text-red-600',
      subtitle: '오늘'
    }
  ];

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {cards.map((card, index) => (
        <div key={index} className="rounded-lg border bg-card text-card-foreground shadow-sm p-6">
          <div className="flex flex-row items-center justify-between space-y-0 pb-2">
            <h3 className="tracking-tight text-sm font-medium">{card.title}</h3>
            <span className="text-lg">{card.icon}</span>
          </div>
          <div className={`text-2xl font-bold ${card.className}`}>
            {card.value}
          </div>
          <p className="text-xs text-muted-foreground">{card.subtitle}</p>
        </div>
      ))}
    </div>
  );
}

