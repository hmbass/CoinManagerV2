import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api';

// 성과 데이터 타입
interface PerformanceData {
  totalProfit: number;
  totalTrades: number;
  winRate: number;
  dailyProfit: number;
  profitRate: number;
}

// 거래 데이터 타입
interface Trade {
  id: string;
  market: string;
  side: 'buy' | 'sell';
  price: number;
  volume: number;
  amount: number;
  profit_loss?: number;
  created_at: string;
}

// 마켓 데이터 타입
interface MarketData {
  symbol: string;
  price: number;
  change: number;
  changePercent: number;
}

// 시스템 상태 타입
interface SystemStatus {
  trading_engine: boolean;
  upbit_connection: boolean;
  notifications: boolean;
}

export function usePerformance() {
  const [data, setData] = useState<PerformanceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchPerformance() {
      try {
        setLoading(true);
        setError(null);
        const result = await apiClient.getPerformance();
        setData(result);
      } catch (err) {
        console.error('성과 데이터 로딩 실패:', err);
        setError(err instanceof Error ? err.message : '데이터 로딩 실패');
        // 오류 시 기본값 설정
        setData({
          totalProfit: 0,
          totalTrades: 0,
          winRate: 0,
          dailyProfit: 0,
          profitRate: 0
        });
      } finally {
        setLoading(false);
      }
    }

    fetchPerformance();
  }, []);

  return { data, loading, error, refetch: () => fetchPerformance() };
}

export function useTrades(limit: number = 10) {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchTrades() {
      try {
        setLoading(true);
        setError(null);
        const result = await apiClient.getTrades({ limit });
        setTrades(result);
      } catch (err) {
        console.error('거래 데이터 로딩 실패:', err);
        setError(err instanceof Error ? err.message : '데이터 로딩 실패');
        // 오류 시 빈 배열 설정
        setTrades([]);
      } finally {
        setLoading(false);
      }
    }

    fetchTrades();
  }, [limit]);

  return { trades, loading, error, refetch: () => fetchTrades() };
}

export function useMarketData() {
  const [marketData, setMarketData] = useState<MarketData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchMarketData() {
      try {
        setLoading(true);
        setError(null);
        const result = await apiClient.getMarketData();
        setMarketData(result);
      } catch (err) {
        console.error('마켓 데이터 로딩 실패:', err);
        setError(err instanceof Error ? err.message : '데이터 로딩 실패');
        // 오류 시 기본 마켓 데이터 설정
        setMarketData([
          { symbol: 'KRW-BTC', price: 89450000, change: 0, changePercent: 0 },
          { symbol: 'KRW-ETH', price: 2890000, change: 0, changePercent: 0 },
          { symbol: 'KRW-XRP', price: 658, change: 0, changePercent: 0 }
        ]);
      } finally {
        setLoading(false);
      }
    }

    fetchMarketData();
  }, []);

  return { marketData, loading, error, refetch: () => fetchMarketData() };
}

export function useSystemStatus() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchStatus() {
      try {
        setLoading(true);
        setError(null);
        const result = await apiClient.getSystemStatus();
        setStatus(result);
      } catch (err) {
        console.error('시스템 상태 로딩 실패:', err);
        setError(err instanceof Error ? err.message : '데이터 로딩 실패');
        // 오류 시 기본 상태 설정
        setStatus({
          trading_engine: false,
          upbit_connection: false,
          notifications: false
        });
      } finally {
        setLoading(false);
      }
    }

    fetchStatus();
  }, []);

  return { status, loading, error, refetch: () => fetchStatus() };
}

