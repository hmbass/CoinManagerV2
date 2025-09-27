import { Suspense } from 'react'
import { Metadata } from 'next'

// 컴포넌트들 (나중에 구현)
// import { TradingOverview } from '@/components/dashboard/TradingOverview'
// import { PerformanceCards } from '@/components/dashboard/PerformanceCards'
// import { EquityChart } from '@/components/charts/EquityChart'
// import { RecentTrades } from '@/components/dashboard/RecentTrades'
// import { MarketStatus } from '@/components/dashboard/MarketStatus'

export const metadata: Metadata = {
  title: '대시보드',
  description: '실시간 거래 현황과 성과를 확인하세요',
}

// 임시 로딩 컴포넌트
function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      {/* 성과 카드 스켈레톤 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-32 bg-muted animate-pulse rounded-lg" />
        ))}
      </div>
      
      {/* 차트 스켈레톤 */}
      <div className="grid gap-6 md:grid-cols-2">
        <div className="h-96 bg-muted animate-pulse rounded-lg" />
        <div className="h-96 bg-muted animate-pulse rounded-lg" />
      </div>
      
      {/* 거래 목록 스켈레톤 */}
      <div className="h-64 bg-muted animate-pulse rounded-lg" />
    </div>
  )
}

// 임시 대시보드 컴포넌트
function TempDashboard() {
  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">대시보드</h1>
          <p className="text-muted-foreground">
            실시간 거래 현황과 성과를 확인하세요
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <div className="flex items-center space-x-2">
            <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse" />
            <span className="text-sm text-muted-foreground">실시간 연결됨</span>
          </div>
        </div>
      </div>

      {/* 성과 카드 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-lg border bg-card text-card-foreground shadow-sm p-6">
          <div className="flex flex-row items-center justify-between space-y-0 pb-2">
            <h3 className="tracking-tight text-sm font-medium">총 수익</h3>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              className="h-4 w-4 text-muted-foreground"
            >
              <path d="M12 2v20m5-5l-5 5-5-5" />
            </svg>
          </div>
          <div className="text-2xl font-bold text-green-600">+125,430원</div>
          <p className="text-xs text-muted-foreground">+2.3% 전일 대비</p>
        </div>

        <div className="rounded-lg border bg-card text-card-foreground shadow-sm p-6">
          <div className="flex flex-row items-center justify-between space-y-0 pb-2">
            <h3 className="tracking-tight text-sm font-medium">총 거래수</h3>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              className="h-4 w-4 text-muted-foreground"
            >
              <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
          </div>
          <div className="text-2xl font-bold">847</div>
          <p className="text-xs text-muted-foreground">+12 오늘</p>
        </div>

        <div className="rounded-lg border bg-card text-card-foreground shadow-sm p-6">
          <div className="flex flex-row items-center justify-between space-y-0 pb-2">
            <h3 className="tracking-tight text-sm font-medium">승률</h3>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              className="h-4 w-4 text-muted-foreground"
            >
              <rect width="20" height="14" x="2" y="5" rx="2" />
              <path d="M2 10h20" />
            </svg>
          </div>
          <div className="text-2xl font-bold text-green-600">67.5%</div>
          <p className="text-xs text-muted-foreground">최근 30일</p>
        </div>

        <div className="rounded-lg border bg-card text-card-foreground shadow-sm p-6">
          <div className="flex flex-row items-center justify-between space-y-0 pb-2">
            <h3 className="tracking-tight text-sm font-medium">일일 수익</h3>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              className="h-4 w-4 text-muted-foreground"
            >
              <path d="M22 12h-4l-3 9L9 3l-3 9-4 0" />
            </svg>
          </div>
          <div className="text-2xl font-bold text-green-600">+15,230원</div>
          <p className="text-xs text-muted-foreground">오늘</p>
        </div>
      </div>

      {/* 차트 영역 */}
      <div className="grid gap-6 md:grid-cols-2">
        <div className="rounded-lg border bg-card text-card-foreground shadow-sm">
          <div className="p-6">
            <h3 className="text-lg font-semibold">에쿼티 커브</h3>
            <p className="text-sm text-muted-foreground">누적 수익 추이</p>
          </div>
          <div className="h-80 p-6 pt-0">
            <div className="h-full bg-muted rounded flex items-center justify-center">
              <p className="text-muted-foreground">차트 영역 (구현 예정)</p>
            </div>
          </div>
        </div>

        <div className="rounded-lg border bg-card text-card-foreground shadow-sm">
          <div className="p-6">
            <h3 className="text-lg font-semibold">마켓 현황</h3>
            <p className="text-sm text-muted-foreground">실시간 가격 정보</p>
          </div>
          <div className="h-80 p-6 pt-0">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="font-medium">KRW-BTC</span>
                <div className="text-right">
                  <div className="font-mono text-lg">89,450,000원</div>
                  <div className="text-sm text-green-600">+2.3%</div>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="font-medium">KRW-ETH</span>
                <div className="text-right">
                  <div className="font-mono text-lg">2,890,000원</div>
                  <div className="text-sm text-red-600">-0.8%</div>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="font-medium">KRW-XRP</span>
                <div className="text-right">
                  <div className="font-mono text-lg">658원</div>
                  <div className="text-sm text-green-600">+1.2%</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 최근 거래 */}
      <div className="rounded-lg border bg-card text-card-foreground shadow-sm">
        <div className="p-6">
          <h3 className="text-lg font-semibold">최근 거래</h3>
          <p className="text-sm text-muted-foreground">최근 24시간 거래 내역</p>
        </div>
        <div className="p-6 pt-0">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="h-8 w-8 rounded-full bg-green-100 flex items-center justify-center">
                  <span className="text-xs font-medium text-green-600">매수</span>
                </div>
                <div>
                  <div className="font-medium">KRW-BTC</div>
                  <div className="text-sm text-muted-foreground">2024-09-25 22:15</div>
                </div>
              </div>
              <div className="text-right">
                <div className="font-mono">89,200,000원</div>
                <div className="text-sm text-green-600">+2,450원</div>
              </div>
            </div>
            
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="h-8 w-8 rounded-full bg-red-100 flex items-center justify-center">
                  <span className="text-xs font-medium text-red-600">매도</span>
                </div>
                <div>
                  <div className="font-medium">KRW-ETH</div>
                  <div className="text-sm text-muted-foreground">2024-09-25 22:10</div>
                </div>
              </div>
              <div className="text-right">
                <div className="font-mono">2,895,000원</div>
                <div className="text-sm text-red-600">-1,200원</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 시스템 상태 */}
      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-lg border bg-card text-card-foreground shadow-sm p-6">
          <h3 className="font-semibold text-sm text-muted-foreground">거래 엔진</h3>
          <div className="flex items-center space-x-2 mt-2">
            <div className="h-2 w-2 bg-green-500 rounded-full" />
            <span className="text-sm">정상 작동 중</span>
          </div>
        </div>
        
        <div className="rounded-lg border bg-card text-card-foreground shadow-sm p-6">
          <h3 className="font-semibold text-sm text-muted-foreground">Upbit 연결</h3>
          <div className="flex items-center space-x-2 mt-2">
            <div className="h-2 w-2 bg-green-500 rounded-full" />
            <span className="text-sm">연결됨</span>
          </div>
        </div>
        
        <div className="rounded-lg border bg-card text-card-foreground shadow-sm p-6">
          <h3 className="font-semibold text-sm text-muted-foreground">알림 시스템</h3>
          <div className="flex items-center space-x-2 mt-2">
            <div className="h-2 w-2 bg-green-500 rounded-full" />
            <span className="text-sm">활성화</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function DashboardPage() {
  return (
    <div className="container mx-auto p-6">
      <Suspense fallback={<DashboardSkeleton />}>
        <TempDashboard />
      </Suspense>
    </div>
  )
}

