# Cursor 일괄 실행 요구사항서 — 단타 코인 트레이딩 시스템 v1

> 이 문서는 **한 번의 프롬프트 실행**으로 프로젝트 전체(설계→코드→테스트→문서)를 생성하기 위한 **원샷 패키지**입니다. Cursor에 아래 “원샷 프롬프트” 블록을 그대로 붙여넣어 실행하세요.

---

## 0) 프로젝트 개요

* **목표**: 단타 코인 트레이더를 위한 **리스크 관리 · 트레이드 일지 · 성과 대시보드** 웹앱(MVP)
* **범위**: 조회/기록/분석 기능만. **거래소 연동 및 자동주문 미구현(금지)**
* **핵심 지표**: 승률, 평균 R, 기대값 E[R], 누적 PnL, 최대 낙폭(MDD), 에쿼티 커브
* **원칙**: 정확한 계산식, 단순한 UX, 투명한 공식 주석, 테스트 우선, 보안 기본수준

---

## 1) 기술 스택 & 표준

* **FE/BE**: Next.js(App Router) + TypeScript
* **DB/ORM**: Prisma + SQLite(로컬) → (옵션) Supabase/Postgres로 확장 가능
* **UI**: TailwindCSS + shadcn/ui + lucide-react
* **Chart**: recharts
* **검증**: zod + react-hook-form
* **상태**: 서버 액션 + 최소한의 클라이언트 훅
* **테스트**: Vitest + Testing Library, Playwright(E2E)
* **품질**: ESLint, Prettier, strict TS, 접근성 점검

---

## 2) 데이터 모델(Prisma)

```prisma
model Config {
  id                      Int      @id @default(autoincrement())
  accountBalance          Float
  tradeRiskPct            Float    // 예: 0.005 (0.5%)
  dailyMaxDDPct           Float    // 예: 0.015 (1.5%)
  feePct                  Float    // 예: 0.0008 (0.08% 왕복)
  representativeStrategy  String   // 'Breakout' | 'Pullback' | 'MeanReversion'
  createdAt               DateTime @default(now())
  updatedAt               DateTime @updatedAt
}

model Trade {
  id            Int      @id @default(autoincrement())
  datetime      DateTime
  exchange      String?
  symbol        String
  setup         String   // 'Breakout'|'Pullback'|'MeanReversion'
  planNotes     String?
  entryPrice    Float
  stopPrice     Float?
  targetPrice   Float?
  side          String   // 'Long'|'Short'
  positionSize  Float    // KRW 등 계정 통화 기준
  qty           Float
  fees          Float
  exitPrice     Float
  exitTime      DateTime?
  pnl           Float
  rMultiple     Float
  notes         String?
  screenshotUrl String?
  ruleViolations String?
  tagTrend      String?  // 'Up'|'Down'|'Range'
  tagLiquidity  String?  // 'High'|'Low'
  createdAt     DateTime @default(now())
  updatedAt     DateTime @updatedAt
}
```

---

## 3) 계산 명세(공식)

* **RiskAmount** = `positionSize * tradeRiskPct(Config)`
* **Fees(기본)** = `positionSize * feePct(Config)`
* **Qty(기본)** = `positionSize / entryPrice`
* **PnL(Long)** = `(exitPrice - entryPrice) * qty - fees`
* **PnL(Short)** = `(entryPrice - exitPrice) * qty - fees`
* **R-multiple** = `PnL / RiskAmount`
* **EquityCurve** = 시간순 `Σ PnL`
* **MDD** = equityCurve에서 `max(peak - trough)`

---

## 4) 페이지 구성

* **/** (Dashboard): KPI 카드(총 거래수, 승률, 평균R, 기대값, 누적PnL, MDD) + 에쿼티 커브(LineChart)
* **/config**: 계좌/리스크/수수료 CRUD 폼 (zod 검증, 헬프텍스트에 공식 설명)
* **/risk-calc**: 진입가/손절거리(%) 입력 → 권장 진입금액/수량/예상비용/R 계산 즉시 표시
* **/trades**: 트레이드 리스트/필터/정렬 + 생성/수정 모달(서버 액션으로 계산 필드 보정)

---

## 5) 비기능 요구(NFR)

* **성능**: 거래 1,000건 목록 필터 200ms 내 응답(로컬 기준)
* **보안**: .env로 비밀 분리, 보안 헤더, 입력 검증
* **품질**: 유닛/컴포넌트/E2E 테스트 포함, 계산 로직은 단위테스트 100%
* **접근성**: 폼 레이블/aria, 키보드 내비, 명도 대비

---

## 6) 수용 기준(AC)

* **AC1**: /config 저장값이 /risk-calc와 /trades 재계산에 반영된다.
* **AC2**: /trades 신규 생성 시 대시보드 KPI/차트 즉시 갱신.
* **AC3**: 빈 필드(qty/fees)는 규칙대로 자동 채움.
* **AC4**: 반올림/통화/단위 표기가 일관된다.
* **AC5**: 유닛·컴포넌트·E2E 테스트 통과.

---

## 7) UX 가이드

* 카드 기반 2열 레이아웃, 2xl 라운드, 소프트 섀도, 충분한 패딩
* 포맷터 유틸(/lib/format.ts): 통화(KRW), 소수(2~4자리)
* 색상: PnL 양수(옅은 녹색), 음수(옅은 주황) 행 하이라이트
* 도움말: 계산식 툴팁/헬프텍스트 명시

---

## 8) 테스트 요구

* **Vitest(Unit)**: 사이징/PNL/R/MDD 수치 검증
* **Playwright(E2E)**:

  * 신규 거래 생성 → 대시보드 KPI 반영 확인
  * /config에서 feePct 변경 → /risk-calc 결과 반영 확인

---

## 9) 시드 데이터

* **Config** 1건(예시): `accountBalance=10,000,000`, `tradeRiskPct=0.005`, `dailyMaxDDPct=0.015`, `feePct=0.0008`, `representativeStrategy='Breakout'`
* **Trade** 10건: 양/음수 혼합, 날짜 분산(대시보드 확인용)

---

## 10) 폴더/코드 구조(권장)

```
app/
  (routes)
    page.tsx           // Dashboard
    config/page.tsx
    risk-calc/page.tsx
    trades/page.tsx
  components/
    ui/* (shadcn)
    charts/EquityChart.tsx
    forms/*
  actions/ (서버 액션)
  api/ (필요 시)
lib/
  calc.ts   // PnL, R, MDD, Equity 등 공식 + 단위테스트 대상
  format.ts // 통화/숫자 포맷
prisma/
  schema.prisma
  seed.ts
tests/
  unit/calc.spec.ts
  e2e/* (Playwright)
```

---

## 11) README 요구

* 프로젝트 목적(교육/기록/분석용, 투자자문 아님)
* 설치/실행, .env 예시
* 데이터 모델/계산식 설명
* 로드맵(CSV Import, 클라우드 DB, OAuth(선택), 모바일 최적화)
* 라이선스

---

## 12) 제약/주의

* 실시간 시세/API 의존 없음(수동 입력)
* 자동주문/브로커 연동 금지
* 재무/투자 조언 문구 금지(고지 포함)

---

# ▶ 원샷 프롬프트(그대로 붙여넣기)

**아래 블록 전체를 Cursor에 입력하면, 스캐폴딩→모듈 구현→테스트→시드→README까지 한 번에 진행하도록 하세요.**

```text
역할: 당신은 단타 코인 트레이딩 웹앱(MVP)의 책임 엔지니어/아키텍트다. 이 메시지에 포함된 "요구사항"을 100% 충족하는 리포지토리를 한 번에 생성하라. 구현이 끝나면 테스트/시드/README까지 완료한 상태여야 한다.

[기술스택]
- Next.js(App Router) + TypeScript
- Prisma + SQLite(로컬)
- Tailwind + shadcn/ui + lucide-react
- recharts
- zod + react-hook-form
- Vitest + Testing Library, Playwright(E2E)
- ESLint + Prettier + strict TS

[데이터 모델]
- Config(id, accountBalance:number, tradeRiskPct:number, dailyMaxDDPct:number, feePct:number, representativeStrategy:string, createdAt, updatedAt)
- Trade(id, datetime:Date, exchange?:string, symbol:string, setup:string, planNotes?:string, entryPrice:number, stopPrice?:number, targetPrice?:number, side:string, positionSize:number, qty:number, fees:number, exitPrice:number, exitTime?:Date, pnl:number, rMultiple:number, notes?:string, screenshotUrl?:string, ruleViolations?:string, tagTrend?:string, tagLiquidity?:string, createdAt, updatedAt)

[계산 공식]
RiskAmount = positionSize * tradeRiskPct(Config)
Fees(기본) = positionSize * feePct(Config)
Qty(기본) = positionSize / entryPrice
PnL(Long) = (exitPrice - entryPrice) * qty - fees
PnL(Short) = (entryPrice - exitPrice) * qty - fees
R-multiple = PnL / RiskAmount
EquityCurve = ΣPnL(시간순)
MDD = equityCurve의 최대 peak-to-trough

[페이지]
- / (Dashboard): KPI 카드(총 거래수, 승률, 평균R, 기대값, 누적PnL, MDD) + 에쿼티 커브(LineChart)
- /config: 계좌/리스크/수수료 CRUD 폼(zod 검증, 공식 툴팁)
- /risk-calc: 진입가/손절거리(%) 입력 → 권장 진입금액/수량/예상비용/R 즉시 계산
- /trades: 리스트/필터/정렬 + 생성/수정 모달(서버 액션으로 계산 필드 자동 보정: qty/fees/pnl/rMultiple)

[UX/가이드]
- 카드 기반 2열, 2xl 라운드, 소프트 섀도우, 적절한 간격
- PnL 양/음수 색 하이라이트, 통화/소수 포맷 유틸(lib/format.ts)
- 계산 로직은 lib/calc.ts로 모듈화하고 주석으로 공식/단위 명시

[테스트]
- Vitest(Unit): 사이징/PNL/R/MDD 수치 검증
- Playwright(E2E): (1) 신규 거래 생성→대시보드 KPI 갱신 (2) /config feePct 변경→/risk-calc 반영

[시드]
- Config 1개: accountBalance=10_000_000, tradeRiskPct=0.005, dailyMaxDDPct=0.015, feePct=0.0008, representativeStrategy='Breakout'
- Trade 10개: 양/음수 혼합, 날짜 분산

[README]
- 프로젝트 목적(교육/기록/분석용, 투자자문 아님), 설치/실행, .env 예시, 데이터 모델/계산식, 로드맵, 라이선스

[품질/보안]
- ESLint/Prettier 적용, 접근성 점검, .env 분리, 보안 헤더 적용

[산출물 체크]
1) `pnpm install && pnpm prisma migrate dev && pnpm prisma db seed` 후 `pnpm dev`로 구동 가능할 것
2) `pnpm test`(Vitest)와 `pnpm exec playwright test` 통과할 것
3) /config 저장값이 /risk-calc와 /trades 계산에 반영될 것
4) 대시보드 KPI/차트가 트레이드 변경에 동기 반영될 것

[진행 방법]
- 패키지/셋업 → Prisma schema → UI scaffold → 계산 유틸 → 페이지 구현 → 서버 액션 계산 보정 → 시드 → 테스트 → README 순으로 자동화.
- 구현 중 스스로 필요한 보일러플레이트/유틸/헬퍼 생성 허용.
- 누락 위험이 보이면 합리적 가정을 문서화(README)하고 구현을 진행.
```

---

## 13) 실행 팁

1. 새로운 빈 리포에서 Cursor 열기 → 위 **원샷 프롬프트** 전체 붙여넣기
2. 패키지 설치/마이그레이션/시드 완료 후 `pnpm dev` 실행
3. 계산 값과 KPI가 기대대로 동작하는지 확인 → 필요 시 문구/필드만 소폭 조정

---

## 14) 로드맵(선택)

* CSV Import 마법사(거래소 체결내역 매핑)
* Supabase(Postgres) 배포 및 Auth(이메일/OTP)
* 모바일 최적화(입력 폼)
* 전략별 성과 비교 리포트(브레이크아웃 vs 풀백)

---

> 필요 시, 위 문서를 기반으로 **Supabase 배포 체크리스트** 또는 **Tauri/Electron 데스크톱 패키징**용 원샷 프롬프트 버전도 추가해 드립니다.
