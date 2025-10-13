'use client';

import { useSystemStatus } from '@/hooks/useApi';

export function SystemStatus() {
  const { status, loading, error } = useSystemStatus();

  if (loading) {
    return (
      <div className="grid gap-4 md:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="rounded-lg border bg-card text-card-foreground shadow-sm p-6">
            <div className="h-4 w-20 bg-muted animate-pulse rounded mb-2" />
            <div className="flex items-center space-x-2 mt-2">
              <div className="h-2 w-2 bg-muted animate-pulse rounded-full" />
              <div className="h-4 w-16 bg-muted animate-pulse rounded" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-lg border bg-card text-card-foreground shadow-sm p-6">
          <h3 className="font-semibold text-sm text-muted-foreground">시스템 상태</h3>
          <div className="text-center text-red-500 mt-2">
            <p className="text-sm">연결 오류</p>
          </div>
        </div>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-lg border bg-card text-card-foreground shadow-sm p-6">
          <h3 className="font-semibold text-sm text-muted-foreground">시스템 상태</h3>
          <div className="text-center text-muted-foreground mt-2">
            <p className="text-sm">데이터 없음</p>
          </div>
        </div>
      </div>
    );
  }

  const statusItems = [
    {
      title: '거래 엔진',
      status: status.trading_engine,
      label: status.trading_engine ? '정상 작동 중' : '중지됨'
    },
    {
      title: 'Upbit 연결',
      status: status.upbit_connection,
      label: status.upbit_connection ? '연결됨' : '연결 실패'
    },
    {
      title: '알림 시스템',
      status: status.notifications,
      label: status.notifications ? '활성화' : '비활성화'
    }
  ];

  return (
    <div className="grid gap-4 md:grid-cols-3">
      {statusItems.map((item, index) => (
        <div key={index} className="rounded-lg border bg-card text-card-foreground shadow-sm p-6">
          <h3 className="font-semibold text-sm text-muted-foreground">{item.title}</h3>
          <div className="flex items-center space-x-2 mt-2">
            <div className={`h-2 w-2 rounded-full ${
              item.status ? 'bg-green-500' : 'bg-red-500'
            }`} />
            <span className={`text-sm ${
              item.status ? 'text-green-600' : 'text-red-600'
            }`}>
              {item.label}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}

