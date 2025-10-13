import { Suspense } from 'react'
import { Metadata } from 'next'
import { PerformanceCards } from '@/components/dashboard/PerformanceCards'
import { MarketStatus } from '@/components/dashboard/MarketStatus'
import { RecentTrades } from '@/components/dashboard/RecentTrades'
import { SystemStatus } from '@/components/dashboard/SystemStatus'

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

// 실제 API와 연결된 대시보드 컴포넌트
function Dashboard() {
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
      <PerformanceCards />

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

        <MarketStatus />
      </div>

      {/* 최근 거래 */}
      <RecentTrades />

      {/* 시스템 상태 */}
      <SystemStatus />
    </div>
  )
}

export default function DashboardPage() {
  return (
    <div className="container mx-auto p-6">
      <Suspense fallback={<DashboardSkeleton />}>
        <Dashboard />
      </Suspense>
    </div>
  )
}

