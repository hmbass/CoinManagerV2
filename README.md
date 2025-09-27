# CoinTrader v1.0 🚀

> **단타 코인 트레이딩 자동매매 시스템**  
> Upbit API 기반 실시간 자동매매 플랫폼

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 📋 시스템 개요

CoinTrader는 Upbit API를 활용한 단타 코인 트레이딩 자동매매 시스템입니다. 실시간 시장 분석, 자동 주문 실행, 리스크 관리, 텔레그램 알림 등의 기능을 제공합니다.

### 🎯 주요 특징

- **🤖 자동매매**: 스캘핑 전략 기반 실시간 거래
- **📊 실시간 모니터링**: WebSocket 기반 시장 데이터 수신
- **⚠️ 리스크 관리**: 손절매, 익절매, 일일 손실 한도 관리
- **📱 텔레그램 알림**: 거래 및 시스템 상태 실시간 알림
- **🌐 웹 대시보드**: Next.js 기반 모니터링 인터페이스
- **🔒 보안**: 환경 변수 기반 API 키 관리

## 🏗️ 시스템 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │   Databases     │
│   (Next.js)     │◄──►│   (FastAPI)     │◄──►│  (SQLite/PG)    │
│                 │    │                 │    │                 │
│ - 대시보드       │    │ - 자동매매 엔진  │    │ - 거래 기록     │
│ - 성과 분석     │    │ - API 서버      │    │ - 설정 정보     │
│ - 설정 관리     │    │ - WebSocket     │    │ - 포트폴리오    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Telegram Bot   │    │   Upbit API     │    │  Strategy       │
│                 │    │                 │    │  Manager        │
│ - 실시간 알림    │    │ - 시장 데이터    │    │                 │
│ - 봇 명령어     │    │ - 주문 실행      │    │ - 스캘핑 전략   │
│ - 상태 조회     │    │ - 잔고 조회      │    │ - 기술적 지표   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 빠른 시작

### 1. 환경 준비

```bash
# 프로젝트 클론
git clone <repository-url>
cd CoinManagerV2

# 환경 설정 파일 생성
cp .env.example .env

# 환경 설정 편집 (API 키 입력 필수)
nano .env
```

### 2. 초기 설정

```bash
# 초기 설정 스크립트 실행
./scripts/setup.sh

# 환경 설정 검증
./scripts/validate-config.sh
```

### 3. 서버 시작

```bash
# 모든 서비스 시작
./scripts/server-manager.sh start

# 상태 확인
./scripts/server-manager.sh status
```

### 4. 접속 확인

- **웹 대시보드**: http://localhost:3000
- **API 문서**: http://localhost:8000/docs
- **백엔드 상태**: http://localhost:8000/health

## 📊 주요 기능

### 🤖 자동매매 엔진

```python
# 스캘핑 전략 예시
- RSI 과매도/과매수 기반 진입
- 거래량 급증 감지
- 0.3-0.5% 목표 수익률
- 0.5% 손절매 설정
```

### 📱 텔레그램 봇 명령어

```
/start          - 봇 시작
/status         - 시스템 상태
/portfolio      - 포트폴리오 현황
/trading_start  - 거래 시작
/trading_stop   - 거래 중지
/emergency_stop - 긴급 정지
```

### ⚠️ 리스크 관리

- **일일 손실 한도**: 50,000원 (기본값)
- **최대 동시 포지션**: 3개
- **포지션 크기 제한**: 100,000원
- **자동 손절매**: 설정된 비율 도달 시

## 🔧 설정 가이드

### 필수 환경 변수

```bash
# Upbit API (실거래 시 필수)
UPBIT_ACCESS_KEY=your_access_key
UPBIT_SECRET_KEY=your_secret_key

# 텔레그램 봇 (알림 기능)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# 거래 모드
TRADING_MODE=paper  # paper(모의) 또는 live(실거래)
```

### 거래 전략 설정

```bash
# 스캘핑 전략
SCALPING_ENABLED=true
SCALPING_RSI_OVERSOLD=30
SCALPING_RSI_OVERBOUGHT=70
SCALPING_MIN_PROFIT=0.5
SCALPING_MAX_LOSS=0.3
```

## 📁 프로젝트 구조

```
CoinManagerV2/
├── frontend/           # Next.js 웹 대시보드
│   ├── app/           # 페이지 및 컴포넌트
│   ├── components/    # 재사용 컴포넌트
│   └── lib/          # 유틸리티 및 API
├── backend/           # Python 백엔드
│   ├── src/
│   │   ├── api/      # FastAPI 라우터
│   │   ├── trading/  # 자동매매 엔진
│   │   ├── upbit/    # Upbit API 클라이언트
│   │   ├── telegram/ # 텔레그램 봇
│   │   └── database/ # 데이터베이스 모델
│   └── tests/        # 테스트 코드
├── scripts/          # 관리 스크립트
│   ├── server-manager.sh
│   ├── setup.sh
│   └── validate-config.sh
└── logs/            # 로그 파일
```

## 🛡️ 보안 및 주의사항

### ⚠️ 중요 경고

1. **실거래 주의**: `TRADING_MODE=live` 설정 시 실제 자금이 투입됩니다
2. **API 키 보안**: `.env` 파일을 절대 공유하지 마세요
3. **손실 위험**: 자동매매는 손실 위험이 있습니다
4. **백테스팅**: 실거래 전 충분한 모의거래 테스트 필요

### 🔒 보안 모범 사례

```bash
# .env 파일 권한 설정
chmod 600 .env

# Git에서 .env 파일 제외 확인
echo ".env" >> .gitignore

# API 키 권한 최소화 (거래권한만)
# Upbit API 키 생성 시 IP 제한 설정 권장
```

## 📊 모니터링 및 로그

### 로그 파일 위치

```
logs/
├── system.log      # 시스템 통합 로그
├── trading.log     # 거래 관련 로그
├── frontend.log    # Frontend 로그
├── backend.log     # Backend 로그
└── errors.log      # 오류 전용 로그
```

### 로그 모니터링

```bash
# 실시간 로그 모니터링
./scripts/server-manager.sh logs system

# 특정 서비스 로그
./scripts/server-manager.sh logs backend
./scripts/server-manager.sh logs frontend
```

## 🧪 테스트

### 단위 테스트

```bash
# Backend 테스트
cd backend
python -m pytest tests/

# Frontend 테스트
cd frontend
npm test
```

### 통합 테스트

```bash
# 전체 시스템 테스트
./scripts/test-system.sh
```

## 🚀 배포

### 개발 환경

```bash
# 개발 서버 시작
./scripts/server-manager.sh start
```

### 프로덕션 환경

```bash
# 환경 변수 설정
export ENVIRONMENT=production
export TRADING_MODE=live

# 프로덕션 배포
./scripts/deploy.sh
```

## 🤝 기여 가이드

1. **Fork** 프로젝트
2. **Feature Branch** 생성 (`git checkout -b feature/AmazingFeature`)
3. **Commit** 변경사항 (`git commit -m 'Add some AmazingFeature'`)
4. **Push** to Branch (`git push origin feature/AmazingFeature`)
5. **Pull Request** 생성

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 📞 지원

- **문제 신고**: [Issues](../../issues)
- **문서**: [Wiki](../../wiki)
- **이메일**: support@cointrader.com

## 🔄 변경 로그

### v1.0.0 (2024-01-XX)
- 초기 릴리스
- 스캘핑 전략 구현
- 텔레그램 봇 연동
- 웹 대시보드 제공

---

> **⚠️ 법적 고지**: 이 소프트웨어는 교육 및 연구 목적으로 제공됩니다. 실제 거래에서 발생하는 모든 손실에 대해 개발자는 책임지지 않습니다. 투자는 본인의 판단과 책임 하에 수행하시기 바랍니다.

**Happy Trading! 📈🚀**

