import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: {
    default: 'CoinTrader - 단타 코인 트레이딩 시스템',
    template: '%s | CoinTrader'
  },
  description: '실시간 자동매매 시스템으로 효율적인 단타 코인 트레이딩을 경험하세요',
  keywords: ['코인', '트레이딩', '자동매매', '단타', '비트코인', 'Upbit'],
  authors: [{ name: 'CoinTrader Team' }],
  creator: 'CoinTrader',
  publisher: 'CoinTrader',
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  robots: {
    index: false,
    follow: false,
  },
  viewport: {
    width: 'device-width',
    initialScale: 1,
    maximumScale: 1,
  },
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: 'white' },
    { media: '(prefers-color-scheme: dark)', color: 'black' },
  ],
  manifest: '/manifest.json',
  icons: {
    icon: '/favicon.ico',
    shortcut: '/favicon-16x16.png',
    apple: '/apple-touch-icon.png',
  },
  openGraph: {
    type: 'website',
    locale: 'ko_KR',
    url: process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000',
    siteName: 'CoinTrader',
    title: 'CoinTrader - 단타 코인 트레이딩 시스템',
    description: '실시간 자동매매 시스템으로 효율적인 단타 코인 트레이딩을 경험하세요',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'CoinTrader 대시보드',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'CoinTrader - 단타 코인 트레이딩 시스템',
    description: '실시간 자동매매 시스템으로 효율적인 단타 코인 트레이딩을 경험하세요',
    images: ['/og-image.png'],
  },
}

interface RootLayoutProps {
  children: React.ReactNode
}

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link 
          rel="preconnect" 
          href="https://fonts.gstatic.com" 
          crossOrigin="anonymous" 
        />
      </head>
      <body 
        className={`${inter.className} antialiased min-h-screen bg-background`}
        suppressHydrationWarning
      >
        <div className="relative flex min-h-screen flex-col">
          <div className="flex-1">
            {children}
          </div>
        </div>
        
        {/* 개발 환경에서만 표시되는 환경 표시기 */}
        {process.env.NODE_ENV === 'development' && (
          <div className="fixed bottom-4 left-4 z-50">
            <div className="rounded-md bg-blue-600 px-2 py-1 text-xs text-white shadow-lg">
              DEV
            </div>
          </div>
        )}
        
        {/* 프로덕션에서 서비스 워커 등록 스크립트 */}
        {process.env.NODE_ENV === 'production' && (
          <script
            dangerouslySetInnerHTML={{
              __html: `
                if ('serviceWorker' in navigator) {
                  window.addEventListener('load', function() {
                    navigator.serviceWorker.register('/sw.js');
                  });
                }
              `,
            }}
          />
        )}
      </body>
    </html>
  )
}

