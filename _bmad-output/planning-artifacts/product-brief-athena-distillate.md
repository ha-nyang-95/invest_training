---
title: "Product Brief Distillate: Athena"
type: llm-distillate
source: "product-brief-athena.md"
created: "2026-04-20"
purpose: "Token-efficient context for downstream PRD creation — all overflow detail not in the 1-2 page executive brief"
companion_docs:
  - _bmad-output/brainstorming/brainstorming-session-2026-04-19-2122.md
  - _bmad-output/planning-artifacts/research/domain-korean-short-term-trading-infra-research-2026-04-20.md
---

# Athena — Detail Pack (Distillate)

본 문서는 Executive Brief에서 의도적으로 제외된 상세 컨텍스트를 PRD 작성용 LLM 입력으로 재구성한 것이다. 각 bullet은 브리프를 읽지 않은 reader에게도 단독으로 이해 가능하도록 작성되었다.

---

## 1. 30개 모듈 전체 명세 (MVP 10 + V1.1+ 20)

**MVP 10 (W1-W8 대상, Executive Brief에 포함)**
- **M1 Linguistic Certainty Scorer** (Feature, NLP) — 뉴스 문장의 확실성·단정성을 0-1로 점수화. KB-BERT + finance_sentiment_corpus fine-tune.
- **M2 Narrative Age Tracker** (Feature, NLP) — 동일 서사의 생애 주기(신규→피크→소진) 추적. Omori law 여진 감쇠 모형 이식.
- **M3 Pre-News Drift Z-Detector** (Feature, Microstructure) — 뉴스 공시 전 비정상 가격·거래량 표류 감지 (내부자 또는 세력 사전 포지셔닝).
- **M9 Time-of-Day Regime Multiplier** (Market State) — 장전/동시호가/장초 1h/점심/마감 1h/장후별 가중치. 본인이 감정적으로 약한 시간대 ≒ 세력 기만 최적 시간대의 교차 방어선.
- **M13 Two-Stage Hybrid Scorer** (Scoring Engine) — 1단계 XGBoost 고속 필터 → 2단계 LLM(비동기) 신뢰도 증강. 블로킹 경로엔 LLM 금지.
- **M14 Basket Coherence Gate** (Scoring Engine) — 밸류체인 바스켓 내 선행주·후발주의 일관성을 Transfer Entropy로 측정. 불일치 시 gate 차단.
- **M19 Loss Acceleration Trigger** (Monitor) — 손실 속도(2차 미분) 감지. 정상 하락 vs 파열적 하락 구분.
- **M22 Hard-Locked Stop Loss** (Exit) — 종목 단위 절대 손절. 서버측 OCO 주문으로 이중화. 트레이더 override 불가.
- **F1 Bargaining Language Detector** (Anti-Ego) — 본인 일지/내부 발화에서 "조금만 더", "이번엔 다르다" 류 흥정 패턴 감지. 250건 수작업 라벨 필수.
- **F5 Parameter Hard-Lock** (Anti-Ego) — 장중 파라미터 수정 물리 차단 + append-only 해시체인 로그 + git revert 방어.

**V1.1+ Priority ⭐⭐⭐ (M4-6개월 예상 편입)**
- **M7 Regime Classifier** — Trend/Chop/Crash 3상태 분류. 전이 확률로 모든 모듈 weighting.
- **M11 Valuechain Directed Graph** — 산업 밸류체인 DAG (삼성전자 설비투자 → 반도체 장비 → 유리기판 → 화학). NetworkX.
- **M12 Transfer Entropy + R0 Estimator** — 대장주→후발주 정보 전이량 측정. 전염병학 R0 이식 (R0>1 시 전이 지속).
- **M16 Implied-Vol & Event Proximity Sizer** — 이벤트 근접 시 포지션 자동 축소 (임상 발표 D-3: 50%, D-1: 25%, D-day: 0%).
- **M23 Multi-Trigger Exit Orchestrator** — 단일 stop이 아닌 복합 exit (시간/변동성/모멘텀/뉴스 소멸 교차).
- **M25 Explainable Veto Report Generator** — 거래 후 "왜 진입/거부했는가"를 자동 설명. 감사·법률·본인 학습 동시 지원.

**V1.1+ Priority ⭐⭐ (M6-12개월)**
- **M8 Market Criticality Thermometer** — 시장 전체의 임계성(SOC/Phase transition) 측정.
- **M15 Kelly with Veto Discount** — Kelly criterion에 veto 강도 할인 반영. 과도 레버리지 방지.
- **M18 Lead-Follow Timing** — 대장주 VI 진입 시각 기준 후발주 포착 window (시간차 공격).
- **M20 Anchor Point Decay** — 본인의 매입 단가 anchor를 시간에 따라 지수 감쇠. 앵커링 편향 약화.
- **M24 Bayesian Flag Trust + Shadow Attribution** — 각 veto flag의 사후 적중률 Bayesian 추정. 신뢰도 낮은 flag 자동 격하.

**V1.1+ Supporting Modules**
- **M4 Order Book Wall Life Analyzer** — 대량 호가벽의 생존 시간. 진짜 지지 vs 스푸핑 구분.
- **M5 Trade Size Distribution Monitor** — 체결 크기 분포. 세력 스텔스 매집(작은 체결 누적) vs 개인 추격매수(큰 단발 체결).
- **M6 Deception Keyword Density** — "호재", "급등 임박" 등 기만 키워드 밀도. 독사과 필터 핵심.
- **M10 b-value & Stress Accumulation** — 지진학 Gutenberg-Richter b-value 이식. 작은 변동성 누적 → 대형 이벤트 예측.
- **M17 Cooldown & Randomization Gate** — 진입 타이밍 엔트로피 최대화로 세력 역설계 방어.
- **M21 Momentum Decay Detector** — 모멘텀 감쇠 속도. 추세 지속 vs 되돌림 구분.
- **F2 Self-FOMO Behavioral Sensor** — 본인의 클릭/호가창 응시/심박(옵션) 패턴으로 FOMO 감지.
- **F3 Physiological Override** — 심박·수면부채·시간대 기반 생리적 override 감지.
- **F4 Third-Person Re-decision Prompt** — "친구가 이 종목을 보여줬다면?"으로 재결정 강제.

**V2.x Research Themes (M12+)**
- **#30 Joint Copula Interaction** — 다변량 꼬리 의존성.
- **#78 Integrated Information Φ** — 의식 이론 Φ를 시장 전체의 통합 정보량에 이식.
- **#80 Stackelberg Reverse Engineering** — 세력을 선제자로 모델링, 본인은 후행자 최적 반응. 게임이론.
- **#82 Red Team Auto-Adversary (GAN)** — Athena를 속이려는 GAN을 훈련시켜 시스템 자기 강건화.
- **#84 Common Knowledge Cascade** — 공통지식의 계단식 형성(Morris 1990).
- **#85 Beauty Contest Tracker** — Keynes 미용대회 2차/3차 추론 수준 추적.
- **Hypergraph NN** — 고차 네트워크 관계 모델링 (3자·4자 상호작용).

---

## 2. 9개 타 도메인 수학 이식 계보 (실패 양식 1:1 매핑)

| 이식 수학 | 원 도메인 | Athena 모듈 | 포착 실패 양식 |
|---|---|---|---|
| **SIR / R0 / Herd immunity / Super-spreader** | 전염병학 | M11, M12, M14 | 밸류체인 전이 한계(R0<1), 대장주 super-spreader 식별 |
| **Watts cascade / PageRank / Threshold model** | 네트워크 과학 | M11, M18 | 네트워크 임계점 통과 시 비선형 확산 |
| **SOC / Percolation / Power-law / Phase transition** | 통계물리 | M8, M10 | 시장 임계성 – 작은 사건이 대형 붕괴로 증폭 |
| **Omori law / ETAS / Gutenberg-Richter / Foreshock** | 지진학 | M2, M10 | 뉴스 후 여진 감쇠, 전조 신호 감지 |
| **Transfer entropy / Mutual info / Φ** | 정보이론 | M12, V2.x #78 | 정보 전이량·방향성 (상관 아닌 인과) |
| **Stackelberg / Costly signaling / ESS / Common knowledge** | 게임이론 | V2.x #80, #84 | 세력-개인 비대칭 정보 게임 |
| **Critical branching ratio** | 신경 사태 | M8 | 시장 임계 분기 감지 |
| **Bass diffusion / Hype cycle / Meme mutation** | 밈학·확산이론 | M2 | 서사 S-curve 소진, 변이 서사 출현 |
| **Trophic cascade / Niche overlap / Keystone / Carrying capacity** | 생태학 | M11, M14 | 키스톤 종목 제거 시 생태 붕괴 |

**Khuk0 귀납 추론 경로 (6개월 후 수식 의심 시 되돌아올 근거):**
- Case 1 (설거지 덫) → "진짜 신호처럼 보이는 거짓말 1건이 평균에 흡수되면 안 된다" → 곱셈형 Veto Gate
- Case 2 (임상 3상) → "본인이 스스로를 override하지 못하게 해야 한다" → Anti-Ego Firewall 병렬 파이프라인
- 두 사례가 동일 시간축(장초·장마감 유동성)에 걸림 → M9 Time-of-Day가 외부·내부 방어선의 교차점

---

## 3. 기술 스택 상세 근거 (2026-04 기준)

**Tier 1 MVP (W1-W8 블로킹 경로)**
- **Python 3.11+** — 3.13은 성능 개선 있으나 python-kis 호환성 미확인
- **asyncio + uvloop 2.6x** — 표준 이벤트 루프 대비 2.6배 (libuv C 기반)
- **Polars 10x pandas** — 컬럼 연산, lazy evaluation, zero-copy Arrow
- **python-kis** — KIS Developers의 타입 안전 래퍼. 자동 재연결, IDE 자동완성 100%
- **pykrx** — KRX 공식 비공개 데이터(VI 발동 이력 등)의 사실상 표준 파서
- **KB-BERT** — KB금융 공개 한국어 금융 BERT. 로컬 추론 < 100ms. MVP NLP 기본축.
- **finance_sentiment_corpus** — 한국어 금융 뉴스 라벨 공개. fine-tune 원료.
- **NetworkX** — 밸류체인 그래프 (MVP는 정적, V1.1+는 동적)
- **DuckDB** — 호가창 L2 저장. 컬럼 지향, SQL, 단일 파일, Parquet 출력
- **dotenv** → **OS Keychain으로 업그레이드 필수** (API key 보안)

**Tier 2 (W9-W12)**
- **LOBFrame** — 호가창 ML 9종 모델 통합 프레임워크 (DeepLOB, TLOB, LiT). Quantitative Finance 2025 게재.
- **Numba** — Python 핫패스 JIT (C 수준 속도, Cython 대안)
- **HyperCLOVA X / Solar Pro 2 API** — 비동기 2단계 LLM. M13 2단계 전용.
- **Prometheus + Grafana + Alertmanager** — 관측성 + 알람 (카카오워크/Telegram bot 연동)

**Tier 3 (V1.1+ ~ V2.x)**
- **PyTorch Geometric** — GNN 기반 밸류체인 동적 그래프
- **PyCausal / CausalML** — Transfer Entropy + Granger 인과
- **TLOB/LiT fine-tune** — 자체 L2 데이터 2년 축적 후
- **Rust + PyO3** — 핫패스 전면 재작성 (V2.x)

**KIS Rate Limit 실전 수치 (python-kis GitHub 이슈 기반)**
- REST: 약 20 req/s (계정별 상이, EGW00201 에러로 초과 감지)
- WebSocket: 실시간 시세 구독 41건/세션
- 모의계좌는 실계좌보다 제한 낮음
- WebSocket 장애 패턴: HTS ID 설정 오류 시 "No close frame received" 에러

**한국어 금융 NLP 6파전 (2025-2026)**
- **KB-BERT** — KB금융, 금융 특화, 최우수. MVP 기본축.
- **KoFinBERT** — KOSPI 예측 연구 논문. 학술적.
- **KoELECTRA fine-tuned** — 범용. 금융 특화 약함.
- **finance_sentiment_corpus** — 라벨 데이터.
- **DART AI 감정 스코어** — 상용. API 접근 제한.
- **₩on** — 방법론 정립 논문 (ACL 2025). 참고용.

---

## 4. 핵심 수식 & 진입 조건

```
S_entry = 1[¬HardKill] · (αN + βV + γO) · Π G_i · M_regime · M_time

진입 조건: S_entry > θ_entry  AND  Anti-Ego Firewall = 1
```

**구성요소**
- `1[¬HardKill]`: hard kill flag 활성화 시 0 (M22 종목, Global/Account/Session 차단)
- `(αN + βV + γO)`: 뉴스·거래량·호가흐름 가중 덧셈 (α, β, γ 튜닝 대상)
- `Π G_i`: 52개 veto flag 곱셈. 한 개라도 0 → 전체 0
- `M_regime`: M7 시장 체제 multiplier (Trend 1.0 / Chop 0.5 / Crash 0.0)
- `M_time`: M9 시간대 multiplier (장초 1h 1.2 / 점심 0.3 / 마감 30분 1.5 등)
- `θ_entry`: 진입 임계값 (F5 하드락. Paper Trading으로 튜닝 후 고정)

**Case 1 (설거지) 재계산:** 7.60 × 0.52 × 0.159 × 0.31 × 0.50 × 0.30 × 0.49 ≈ 0.014 → θ=1.0 대비 99.8% 삭감

---

## 5. 8대 KPI 상세 측정 규약

| KPI | 공식 | 측정창 | 최소 표본 | 제외 규칙 |
|---|---|---|---|---|
| 월 수익률 (세후 기하평균 연간화) | `(∏(1+r_m))^(12/n) - 1 - 세금` | 캘린더 월 | n≥6 | 첫 주(시스템 안정화) 제외 |
| Deflated Sharpe | Bailey·López de Prado (2014) | 일별 수익률 | 50+ 트레이드 | — |
| Max Drawdown | `max(peak - trough)/peak` | 일별 NAV | — | — |
| 설거지 회피율 | `회피 건수 / 설거지 의심 신호 건수` | 월 | 월 5건+ | 의심 라벨링 기준 사전 정의 |
| 이벤트 손실 경감률 | `1 - (실손실 / MVP없을시 추정손실)` | 이벤트당 | 이벤트 3건+ | — |
| 시그널 레이턴시 p99 | Prometheus histogram_quantile | 일별 | 1000+ 신호 | — |
| override 로그 완전성 | `기록된 시도 / 실제 시도` | 월 | — | 실제 시도는 F1 자체+사후 회고로 교차검증 |
| F1 드리프트 (PSI) | population stability index | 월 | — | PSI > 0.2 → paper-only 전환 |

**자본 규모 별 재측정:**
- 10-30만 원 초기: KPI 계산은 동일하나 "통계적 유의성"은 자본 확대 시 재평가
- ≥ 1,000만 원 도달: 외부 승인권자·증권사 통지 자동 트리거

---

## 6. 12주 로드맵 주차별 마일스톤

**W1-2 데이터 인프라 (가장 중요한 주간)**
- ★ Day 1: 호가창 L2 WebSocket 로거 24/7 무중단 가동 + DuckDB 스키마 확정 (모든 의사결정 선행)
- DART 크롤러 (공시 실시간)
- 뉴스 피드 통합 (연합뉴스·매경·한경·다음/네이버 크롤)
- pykrx 백필 2년치 (OHLCV·VI 이력)
- KIS API 키 + OS Keychain 저장
- 감시 종목 유니버스 (KOSPI200 + KOSDAQ150)
- 모니터링 대시보드 minimal

**W3-4 NLP Features**
- M1 Linguistic Certainty Scorer (KB-BERT fine-tune)
- M2 Narrative Age Tracker (SBERT 클러스터링 + Omori decay)
- M3 Pre-News Drift Z-Detector
- **F1 라벨링 병행:** 최근 200건 + 과거 10년 일지 회고 50건 = 250건 수작업

**W5-6 Scoring Brain**
- M9 Time-of-Day Regime Multiplier
- M13 Two-Stage Hybrid Scorer (XGBoost 1단계)
- M14 Basket Coherence Gate
- F5 Parameter Hard-Lock (append-only 로그 + hash chain)
- Paper-Trade Ready MVP (실거래 미연결)

**W7-8 Monitor + Exit + Full MVP**
- M19 Loss Acceleration Trigger
- M22 Hard-Locked Stop Loss (+ 서버측 OCO)
- F1 Bargaining Language Detector (250건 라벨 완료 → fine-tune)
- Secondary 증권사 Adapter 추상화 계층 설계
- **Full MVP 10 live**

**W9-10 Backtest + Walk-forward**
- 공매도 재개(2025-03-31) 전후 레짐 분리 검증 필수
- Bayesian parameter tuning (θ_entry, α/β/γ 확정)
- Out-of-sample 미경험 사건 5-10건 재계산 (88% 가설 검증)
- Deflated Sharpe 측정

**W11-12 Paper Trading + V1.0 Launch**
- Paper Trading 2주 실행
- Kill Switch 4층 실발동·회복 훈련 (각 1회 이상)
- DR 시나리오 시뮬레이션 (heartbeat fail → auto flatten)
- KPI 전부 Paper Trading에서 통과 시 V1.0 Launch 승인
- 초기 자본 10-30만 원 단위로 실거래 시작

---

## 7. Cross-Module Feature Reuse (공유 Feature Store)

PRD 설계 시 반드시 고려할 재사용 경로:

- **KB-BERT 임베딩** → M1, M2, M6, F1 공통. 한 번 계산, 다수 모듈 소비.
- **L2 호가창 Tick** → M3, M4, M5 (외부) + F3 생리적 타이밍 분석 (내부) 양방향 소비
- **감정 점수 (M1 출력)** → M13 score, F1 흥정 감지 보조 feature
- **밸류체인 그래프 (M11)** → M14 bas coherence, M18 lead-follow timing
- **M9 시간대 multiplier** → S_entry 직접 + F2 FOMO 시간대 가중
- **본인 트레이딩 일지** → F1 학습 + V1.1+ M20 Anchor Decay 튜닝 + 분기 Red Team 세션 원료

**함의:** PRD에서 모듈별 Feature Store 스키마를 통일된 테이블로 선언해야 V1.1+ 확장 시 중복 계산 회피.

---

## 8. 명시적 Non-Goals & Rejected Ideas (재제안 차단)

**영구 배제 (상용화 Non-Goal 연관)**
- No-code UI — 개인용 고정
- 타 사용자 배포/SaaS — 투자일임업 §17/§18 위반
- 코드·파라미터 공개 (GitHub public, 블로그 시그널 공개) — 투자권유 해석 소지
- 가족·지인 계좌 위임 — 무인가 투자일임업

**V1.0 배제 (V1.1+ 이후 재검토)**
- NXT 다시장 연동 — V1.1+ 유보 (Scope 단순화)
- 파생상품·해외주식 — KRX 주시장 only
- 스캘핑/HFT (<1초) — 5초 예산 초과

**기술 선택에서 기각된 대안**
- Kiwoom OpenAPI+ — COM/OCX 레거시, Mac/Linux 미지원 → KIS 승
- LS증권 — 후발주자, 커뮤니티 작음 → V1.1+ secondary로 보류
- Cython 핫패스 — Numba로 충분 (Cython 복잡도 회피)
- 실시간 LLM blocking 호출 — 5초 예산 불가능
- pandas 유지 — Polars 10x 성능 이득 포기 불가
- .env 장기 사용 — OS Keychain 필수 (보안)

**아키텍처 결정에서 기각된 것**
- 덧셈형 스코어 모델 (업계 표준) — 비대칭 실패 방어 불가
- 단일 파이프라인 (외부 방어만) — Case 2 임상 3상은 내부 덫이므로 커버 불가
- 트레이더 완전 수동 override 허용 — F5 존재 이유가 없어짐

---

## 9. 경쟁·시장 인텔리전스 (Time-Sensitive)

**직접 경쟁자 없음 — 대신 세그먼트 비교**

| 세그먼트 | 대표 | 특징 | Athena와의 관계 |
|---|---|---|---|
| No-code 퀀트 플랫폼 | Time Percent (2026-02 펀딩) | 리테일, 기술지표 조합 | 상이 세그먼트, 경쟁 아님 |
| 증권사 알고 주문 | KIS, 키움 | 집행 전용 | 보완 (실행 레이어) |
| 해외 SaaS | QuantConnect, Alpaca | 미국 중심, 한국어 NLP 부재 | 한국 시장 특화로 구별 |
| 헤지펀드 퀀트 | 국내·외 기관 | 자본·인력 우위 | 기관은 L2 접근 우위, 본인은 심리 방어로 차별 |

**시장 규모 (2025-2026)**
- 글로벌 알고 시장: $21.89B (2025) → $25.04B (2026), CAGR 14.4%
- 리테일 세그먼트 CAGR: 8.32% (~2031)
- APAC CAGR: 8.73% (최고)
- NXT 시간외 거래액: 약 12조 원 (2025-04 기준, 전년 대비 ~10배)
- NXT 이용자 85% 개인투자자

**4대 정렬 타이밍 (부분 충돌 인정)**
- 공매도 재개 2025-03-31 — 변동성 ↑ (단, 숏 압력은 롱 전략과 부분 충돌)
- 금투세 폐지 2025-01-01 — 세후 수익 ↑ (단, 개인 유입 증가 → 세력 설거지 표적 확대 역효과)
- 밸류업 프로그램 2024-09~ — 저평가 재평가, 테마 순환 가속
- NXT 출범 2025-03 — 유동성 폭증, 설거지 관찰 최적

---

## 10. Open Questions (리서치 미완결)

PRD 작성 시 해결 필요 또는 실전 운영 중 관찰해야 할 항목:

- **KIS Rate Limit 정확한 TPS** — 공식 비공개. 실측 필요 (W1에서 벤치마크).
- **한국 리테일 알고 트레이딩 시장 규모** — 직접 데이터 없음. APAC 간접 추정.
- **Time Percent 시장 점유율·사용자 수** — VC 펀딩 정보만 공개, 실 규모 비공개.
- **2026년 KOSPI 일평균 거래대금** — Q1-Q2 데이터 확보 필요.
- **공매도 재개 이후 세력 행태 변화 패턴** — 본인 관찰 + Walk-forward 백테스트에서 추출.
- **F1 라벨 적정 수 (포화점)** — 250건이 충분한지 500건 필요한지 실험적 결정.
- **Deflated Sharpe의 실전 하한선** — 개인 1인 운용에서 1.5가 현실적인지 1.0이 현실적인지.
- **VI·동시호가·장전/장후 특이 시간대의 알파 지속성** — 본인 관찰로 검증.

---

## 11. Requirements Hints (PRD에서 기능 요구사항으로 전개할 것)

브리프·리서치에서 언급된 "~해야 한다" 류 암시:

- 모든 주문은 Pre-Trade Authorization Ledger에 S_entry·gate 목록·param_hash·git_sha 포함 기록 (append-only)
- F5 하드락은 장중 git pull/checkout 차단 (읽기전용 마운트)
- 파라미터 변경 시 24h cooling period + Paper Trading 재검증
- Kill Switch 4층 각각 독립적으로 off 가능 + 로그 남김
- heartbeat 5분 지연 시 모바일 푸시, 4시간 무응답 시 자동 flatten
- Secondary 증권사 Adapter는 KIS와 동일 interface (주문 DTO 추상화)
- M13 2단계 LLM 호출은 반드시 비동기 + 타임아웃 2초 + fallback to 1단계
- 월간 F1 재학습 시 PSI/KS 계산 후 데이터 drift 감사 리포트 자동 생성
- 모든 외부 API key는 OS Keychain 또는 HSM. 코드·git·.env 금지
- 감시 종목 유니버스는 설정 파일 아닌 DB 테이블로 (런타임 수정 가능)
- 세후 수익률 계산 모듈(M_tax) — 거래세 0.18% + 배당세 15.4% + 대주주 요건 추적

---

## 12. Detailed User Scenarios (PRD 시나리오·acceptance criteria 원료)

**Scenario A — 설거지 덫 재발 방지 (Primary)**
- 09:05 유리기판 테마주 뉴스 "대기업 투자 확대" 공시 → M1 Linguistic Certainty 높음 (`0.82`)
- M2 Narrative Age: 동일 서사 3일차 → `0.52` (피크 근접)
- M3 Pre-News Drift: 공시 전 1시간 비정상 거래량 → Z=`3.1` → `0.159` (내부자 의심)
- M4 Order Book Wall: 매수벽 수명 < 3초 → `0.31` (스푸핑)
- M14 Basket Coherence: 대장주 vs 후발주 Transfer Entropy 음수 → `0.50`
- S_entry = 0.014 < θ=1.0 → **진입 거부**, 이유 리포트 자동 생성 (M25)
- 기대: 12% 손실 → 0%

**Scenario B — 임상 3상 override 차단 (Primary)**
- D-3 임상 발표 예정 → M16 Event Proximity Sizer가 현 포지션 50% 자동 축소
- D-day 15:40 "임상 실패" 뉴스 → M1 부정 확실성 높음 + M6 실패 키워드 감지
- M22 Hard-Locked Stop 즉시 시장가 강제 청산
- 본인이 "조금만 기다려보자" 입력 시도 → F1 Bargaining Detector 감지 → F5 파라미터 변경 차단 + 로그 기록
- 기대: 15% 손실 → 3.5% 손실

**Scenario C — 정상 진입 (False Positive 억제)**
- 09:30 실적 호재 발표, M1 `0.9` + M3 정상 드리프트 + M4 매수벽 지속 + M14 바스켓 일관 양호
- S_entry > θ, Anti-Ego Firewall=1 → 진입, Sizing은 M15 Kelly with Veto Discount
- F5는 진입 시점 파라미터 snapshot 기록

**Scenario D — Kill Switch Global 발동**
- 당일 -2% 누적, 추가 1건 손절 → 일일 -3% 임계 → Global Circuit Breaker
- 모든 신규 진입 차단, 오픈 포지션은 M22 정상 exit만 허용
- 당일 거래 중지, 모바일 푸시, 익일 09:00 자동 재개

**Scenario E — heartbeat 상실 DR**
- 운영자 PC 네트워크 단절 → 서버측 heartbeat 4h 미수신
- 서버 자동 전량 시장가 청산 + 신규 진입 영구 차단 (수동 해제 필요)
- KIS 장애 시 Secondary Adapter(eBEST) fallback

---

## 13. Compliance Appendix (법률 근거 상세)

**자본시장법 주요 조항**
- §176 시세조종행위 금지 — 허수성 호가, 연속매매, 가장매매, 통정매매
- §178 부정거래행위 금지 — 일반 포괄 조항
- §178-2 시장질서 교란행위 — **과실도 처벌** (자동매매 사고 시 적용 가능)
- §17 인가, §18 등록 — 투자자문업·투자일임업
- §444 벌칙 — 5년 이하 징역 또는 2억 이하 벌금

**소득세법 / 증권거래세법**
- 금투세 폐지 2025-01-01 (상장주식 양도세는 대주주 외 비과세)
- 증권거래세 0.18% (코스피 0.03% + 농특세 0.15%)
- 배당소득세 15.4%
- 대주주 판정: 종목당 지분 1% 또는 시가 10억 원

**전자금융거래법**
- §9 금융회사 책임 (이용자 고의·중과실 시 면제)
- §21 안전성 확보의무

**한국거래소 시장감시규정**
- §4 이상거래 심리기준

**소규모 자본(10-30만 원) 기준 실질 리스크**
- 시세조종 심리 진입 가능성: 낮음 (시장 영향력 미미)
- KIS 계좌 제한 가능성: 낮음 (주문 규모 자체가 작음)
- 단, **패턴 자체**(고빈도 + 고취소율)는 자본 규모와 무관하게 경보 가능 → 가드레일 필수

---

## 14. Next Steps 체크리스트 (Week 1 Day 1)

즉시 실행 가능한 순서:

1. ☐ KIS 계좌 + API Key 발급 (실계좌 + 모의계좌 각 1개)
2. ☐ `python-kis`, `pykrx`, `uvloop`, `polars`, `duckdb`, `networkx` 설치
3. ☐ OS Keychain에 API Key 저장 (.env 금지 원칙 즉시 시행)
4. ☐ **★ 호가창 L2 WebSocket 로거 구현 및 24/7 무중단 가동** (DuckDB 스키마: ts, symbol, bid/ask 각 10호가, 체결가·수량)
5. ☐ 감시 종목 리스트 DB 테이블 (KOSPI200 + KOSDAQ150, 초기)
6. ☐ 로거 uptime 모니터링 대시보드 (Grafana 최소 구성)
7. ☐ DART 크롤러 + 뉴스 피드 통합
8. ☐ pykrx로 2년 OHLCV + VI 이력 백필
9. ☐ F1 라벨링 워크플로우 셋업 (과거 10년 일지 디지털화 병행 시작)
10. ☐ git repo 초기화 + branch protection (Anti-Ego Firewall 전제)

**12주 동안 단 하나의 원칙으로 수렴:** *"시스템은 조용히 아무것도 하지 않을 줄 알아야 한다."*
