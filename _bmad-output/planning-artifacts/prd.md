---
stepsCompleted:
  - step-01-init
  - step-02-discovery
  - step-02b-vision
  - step-02c-executive-summary
  - step-03-success
  - step-04-journeys
  - step-05-domain
  - step-06-innovation
  - step-07-project-type
  - step-08-scoping
  - step-09-functional
  - step-10-nonfunctional
  - step-11-polishclaud
  - step-12-complete
completed: 2026-04-20
status: complete
vision:
  northStar: "조용히 아무것도 하지 않을 줄 아는 시스템 — 진입 거부가 1차 가치. 고순도 기회만 통과시키는 거름망."
  northStarKpiRelation: "충돌 아닌 필연적 인과관계. 북극성(엄격한 Veto)이 KPI(월 수익률 > 30%)를 견인. 나쁜 진입을 0으로 수렴시킬수록 남은 진입의 기대 수익률 폭발."
  designPriority: "Veto Gate 엄격함 > 기회 포착 완화. 매매 횟수 부족은 시스템 실패가 아니라 '그 기간 시장에 고순도 기회 없었음'을 증명하는 객관적 데이터."
  differentiators:
    - "곱셈형 Veto Gate 아키텍처 — 덧셈 스코어 업계 표준 대비 단일 거짓 신호 전체 차단"
    - "Anti-Ego Firewall (F1-F5) — 리테일 시장에서 트레이더 본인을 1급 위협으로 모델링한 유일 사례, F1 250건 수작업 라벨은 복제 불가"
    - "자체 L2 호가창 2년 Time-Travel Rights — KIS Tick 히스토리 미제공 환경에서 시간만이 만드는 비대칭 자산"
    - "런칭 타이밍 (조건부) — 공매도 재개/금투세 폐지/밸류업/NXT 출범 4대 정렬, 단 부분 충돌 인정"
  coreInsight: "단기 매매 실패는 두 종류 — 외부 기만(설거지 덫) vs 내부 편향(확증·앵커·FOMO). 두 덫을 단일 곱셈형 로직으로 동시 방어한 리테일 알고리즘 제품은 Athena가 유일 (기관 Risk Desk는 '타인 통제', Athena는 '자기-통합')."
  uniquenessScope: "개인 투자자가 접근 가능한 리테일 알고리즘 시장 기준 (기관 헤지펀드 Risk Desk는 별도 범주로 인정)."
  futureState: "Cognitive Prosthesis — 모니터의 번쩍이는 뉴스/급등 호가창 앞에서 과거엔 마우스에 손을 올리고 흥분했을 상황에서, Athena가 'M3+F1 감지'를 이유로 진입 버튼 비활성화. 답답함이 아닌 '기묘한 안도감' — '내 뇌가 또 속으려 했구나'의 객관적 확인. 매매의 고통에서 해방되어 차분히 커피를 마시며 다음 데이터 분석. 뇌는 오직 '연구'와 '전략'에만 집중. 인지 부하 제로 상태가 Cognitive Prosthesis의 실체."
inputDocuments:
  - _bmad-output/planning-artifacts/product-brief-athena.md
  - _bmad-output/planning-artifacts/product-brief-athena-distillate.md
  - _bmad-output/planning-artifacts/research/domain-korean-short-term-trading-infra-research-2026-04-20.md
  - _bmad-output/brainstorming/brainstorming-session-2026-04-19-2122.md
documentCounts:
  briefs: 2
  research: 1
  brainstorming: 1
  projectDocs: 0
classification:
  projectType: api_backend
  projectTypeNote: "Personal bespoke backend service — internal module boundaries only, no external API/auth/SDK"
  domain: fintech
  complexity: high
  projectContext: greenfield
  scopeLock: personal-use-only
  scopeLockRationale: "Commercialization rejected 2026-04-20 due to 자본시장법 §17 투자자문업 / §18 투자일임업 licensing constraints"
workflowType: prd
projectName: Athena
author: Khuk0
created: 2026-04-20
---

# Product Requirements Document — Athena

**Author:** Khuk0
**Date:** 2026-04-20
**Project:** Athena — 전문가 인지 복제형 단기 매매 자동화 시스템

---

## Table of Contents

1. [Executive Summary](#executive-summary) — Vision, 수식, 설계 원칙, 2-Track Defense, Scope Lock
2. [Project Classification](#project-classification) — Type · Domain · Complexity · Scope Lock · Operating Model
3. [Success Criteria](#success-criteria) — User · Capital Performance · Technical · 8대 KPI
4. [Product Scope](#product-scope) — MVP 10 모듈 · Growth V1.1+ · Vision V2.x · Non-Goals
5. [User Journeys](#user-journeys) — J1 Happy · J2 Edge · J3 Operator · J4 Incident · J5 Capital Gate
6. [Domain-Specific Requirements](#domain-specific-requirements) — 자본시장법 · KIS · 호가창 L2 · Blind Spots
7. [Innovation & Novel Patterns](#innovation--novel-patterns) — I-1~I-4 혁신 · 4-Gate Validation · Fallback
8. [Backend Service — Internal Architecture Requirements](#backend-service--internal-architecture-requirements) — 5 Bounded Contexts · DTO · Error Codes · Stack · Observability
9. [Project Scoping & Phased Development](#project-scoping--phased-development) — Validated-Learning MVP · Resources · Scoping Risks
10. [Functional Requirements](#functional-requirements) — 58 FRs / 8 Capability Areas (Capability Contract)
11. [Non-Functional Requirements](#non-functional-requirements) — Performance · Reliability · Security · Integration · Observability · Audit · Maintainability
12. [Appendix A — Brainstorming Traceability](#appendix-a--brainstorming-traceability) — Identified Gaps · Morphological Axes · Case 1 상세

---

## Executive Summary

Athena는 한국 주식시장 단기 매매에서 **외부 기만(설거지 덫)** 과 **내부 편향(확증·앵커·FOMO)** 이라는 두 종류의 실패를 동시에 차단하도록 설계된, 본인 전용 단기 매매 자동화 시스템이다. 시스템의 1차 가치는 **"조용히 아무것도 하지 않을 줄 아는 능력"** 이며, 기회 포착이 아니라 **진입 거부**가 북극성이다.

단기 매매 실패는 구조적으로 두 양식으로 분해된다:
- **외부 덫** (2025-11 유리기판 A사, -12%): 세력의 출구 유동성을 진짜 신호로 오인
- **내부 덫** (2023-12 바이오 C사, -15%): 확증편향 + 앵커링 + 흥정 언어가 hard stop을 override

리테일 알고리즘 시장에서 두 덫을 **단일 곱셈형 로직으로 동시 방어한 사례는 존재하지 않는다.** 기술지표 기반 알고리즘(Time Percent 등)은 외부 덫만 다루고 내부 덫에 무력하며, 심리 일지 접근은 외부 기만에 속수무책이다. 기관 헤지펀드의 Risk Desk는 구조적으로 존재하나 이는 "타인에 의한 통제"이며, 리테일 환경에서 **트레이더 내부 언어(F1) + 생리(F3)를 시장 데이터(M1-M25)와 동일 파이프라인에서 통합 처리하는 자기-통합 아키텍처**는 Athena가 유일하다.

Athena의 핵심 수식:

```
S_entry = 1[¬HardKill] · (αN + βV + γO) · Π G_i · M_regime · M_time
진입 조건: S_entry > θ_entry  AND  Anti-Ego Firewall = 1
```

52개 veto flag를 곱셈 결합하며, 한 개의 거짓 신호 또는 한 번의 심리적 override 시도만으로도 전체 진입을 차단한다. 5개 Anti-Ego Firewall 모듈(F1-F5)이 트레이더 본인을 감시하는 병렬 파이프라인을 운영하며, F1은 본인 과거 일지 250건 수작업 라벨(최근 200건 + 10년 회고 50건)로 학습한다.

**6개월 1차 목표:** 월 수익률 > 30%(세후 기하평균), Deflated Sharpe > 1.5, Max DD < 10%, 설거지 회피율 > 90%, 이벤트 손실 경감률 > 75%, override 로그 완전성 100%. 단, n≥6개월 · 50+ 트레이드 · bootstrap CI 하한 > 0 조건 하에서만 KPI 달성을 선언한다.

**설계 원칙 (북극성 vs KPI 관계):** 북극성과 KPI는 충돌이 아닌 필연적 인과관계다. 나쁜 진입을 0으로 수렴시킬수록 남은 진입의 기대 수익률이 폭발한다 — *"거름망의 눈이 촘촘할수록 남는 것은 금뿐이다."* Tradeoff 발생 시 **Veto Gate 엄격함 > 기회 포착 완화**. 매매 횟수 부족은 시스템 실패가 아니라 "그 기간 시장에 고순도 기회가 없었음"을 증명하는 객관적 데이터로 취급한다.

**방어 트랙 분리 (2-Track Defense):** 위의 "두 종류 실패(외부 기만 vs 내부 편향)" 프레임은 **알파 방어 트랙**에 한정된다. 단기 매매에는 이 외에도 Execution Slippage · Portfolio Correlation · Data Integrity · API 장애 · Tail Risk · Alpha Decay 등 다수 실패 양식이 존재하며, 이들은 **운영 방어 트랙** (DR · Compliance · Execution · Portfolio Risk · Data Quality · Kill Switch)이 **독립적으로 병렬 방어**한다. 즉 Veto Gate + Anti-Ego Firewall의 곱셈형 로직은 *알파 방어*의 핵심 장치이며, *운영 방어*는 별도 NFR·감사·DR 섹션에서 규율된다. 두 트랙은 서로 대체하지 않고 상호 보완한다.

**Scope Lock:** V1.0은 본인 전용 고정. 상용화·SaaS·타인 시그널 구독·계좌 위임은 자본시장법 §17(투자자문업)/§18(투자일임업) 라이선스 제약으로 V1.0 범위 영구 배제 (2026-04-20 확정). 아키텍처 수준에서만 재사용 가능한 경계(user_id 필드 여지, 모듈 경계 추상화)를 유지한다.

### What Makes This Special

**Core Insight** — 단기 매매 실패는 두 종류로 분해된다: *외부 기만* vs *내부 편향*. 두 덫을 동시에 동일 파이프라인에서 단일 곱셈형 로직으로 방어하는 리테일 알고리즘 제품은 Athena가 유일하다. 곱셈 구조는 한 개의 거짓 신호도 평균에 흡수되지 않고 전체를 0으로 수렴시켜, 비대칭 파괴력을 가진 단일 실패 양식을 구조적으로 방어한다.

**4개 해자 (Moats):**

1. **곱셈형 Veto Gate** — 업계 표준 덧셈 스코어 모델과 근본적 구조 차이. `Π G_i` 수식은 2건의 자기 실패 사례를 귀납적으로 분해해 도출되었고, 전염병학 SIR · Watts cascade · Omori law · Transfer entropy 등 9개 타 도메인 수학을 직접 이식한 결과물이다.

2. **Anti-Ego Firewall (F1-F5)** — 경쟁 제품 누구도 트레이더 본인을 1급 위협으로 모델링하지 않는다. F1은 본인 일지 250건 수작업 라벨 기반으로, 외주·복제가 구조적으로 불가능하다. F5는 장중 파라미터 변경·git revert를 물리 차단하는 append-only 해시체인 로그 구조.

3. **자체 L2 호가창 Time-Travel Rights** — KIS는 Tick 히스토리를 제공하지 않는다. Week 1 Day 1부터 자체 WebSocket 로거를 24/7 무중단 가동해 2년간 축적하는 데이터셋은 공매도 재개 · 밸류업 · NXT 전환기를 한 관찰자 시점에서 기록한 유일 자산으로, 자본·인력으로 단축 불가능한 시간 기반 비대칭이다.

4. **런칭 타이밍 (조건부 순풍)** — 공매도 재개(2025-03-31) + 금투세 폐지(2025-01-01) + 기업 밸류업 + NXT 출범(2025-03)의 4대 제도가 동시 본궤도. 단, 4요인은 부분 충돌 가능성이 있다(공매도 재개는 롱 전략과 부분 충돌, 금투세 폐지는 세력 설거지 표적 확대 역효과). "역사적 적기"가 아닌 **"강한 순풍"** 으로 정확히 기술한다.

**Future State — Cognitive Prosthesis:** 과거라면 마우스에 손을 올리고 흥분했을 상황 — 뉴스 헤드라인이 번쩍이고 호가창이 요동치는 순간 — 에서 Athena가 *"M3 선행 표류 + F1 흥정 언어 감지"* 를 이유로 진입 버튼을 비활성화한다. 답답함이 아닌 **기묘한 안도감**이 찾아온다: *"아, 내 뇌가 또 속으려 했구나"* 의 객관적 확인. 매매의 고통에서 해방되어 차분히 커피를 마시며 다음 데이터 분석으로 돌아간다. 시스템이 규율을 담당하므로 뇌는 오직 **연구와 전략**에만 집중하는 상태 — 인지 부하 제로가 이 제품이 궁극적으로 돌려주는 것이다.

## Project Classification

| 축 | 값 |
|---|---|
| **Project Type** | `api_backend` — 외부 API/인증/SDK 없이 내부 모듈 경계 (Feature Store ↔ Scoring ↔ Execution) 전용의 헤드리스 백엔드 서비스 |
| **Domain** | `fintech` — 한국 자본시장 자동 매매, 자본시장법 §176/§178/§178-2 가드레일 내장 |
| **Complexity** | **High** — 실시간 레이턴시(p99 < 5초) × 멀티소스 데이터 융합 × ML/NLP(KB-BERT) × 실자본 리스크 × 신규 아키텍처(곱셈형 Veto + Anti-Ego Firewall) |
| **Project Context** | `greenfield` — 기존 코드베이스 없음, 12주 MVP → V1.0 Launch 청사진 확정 |
| **Scope Lock** | `personal-use-only` — Primary User Khuk0 1명. 상용화·SaaS·타 사용자 확장 영구 배제 |
| **Operating Model** | Python 3.11+ asyncio+uvloop / Polars / DuckDB / KB-BERT / python-kis 스택의 24/7 상시 가동 서비스. 물리 이중화(UPS + LTE + 로거 PC ≠ 트레이딩 PC), 서버측 heartbeat 4시간 무응답 시 자동 전량 청산 |

---

## Success Criteria

### User Success

Athena의 유일한 사용자는 Khuk0 본인이다. 사용자 성공은 두 축으로 측정된다.

**축 A — 심리·행동 성공 (Cognitive Prosthesis Realized)**

| 성공 지표 | 목표 | 측정 방법 |
|---|---|---|
| 장중 override 시도 발생 시 **100% 차단** | F5 하드락 물리적 override 불가 | F5 tamper-evident 로그 테스트 |
| override 시도 **로그 완전성** | 100% | 시도 0회가 아닌 시도 발생 시 전수 기록. F1 자체 감지 + 사후 회고 교차검증 |
| 2건 과거 실패 시나리오 재발 시 회피 | A: 100% 회피 / B: ≥77% 경감 | Paper OOS 재계산 |
| 매매 외 시간 **해방도** | 장 개시 후 밀착 관찰 시간 ≥80% 단축 | 주간 회고 체크리스트 |
| "기묘한 안도감" 확인 (정성) | 월 1회 회고에서 override 유혹 차단 ≥3건 | 본인 서술형 로그 |

**축 B — 과거 실패 재현 시 방어 시나리오**

- **A (설거지 덫, 외부 기만)** — 2025-11 A사 패턴 재현 시 S_entry ≤ 0.02 자동 수렴, 진입 거부 + M25 설명 리포트 자동 생성
- **B (임상 3상 override, 내부 편향)** — M16 이벤트 근접 축소 + M22 강제 청산 + F1 흥정 언어 감지 + F5 하드락 4중 방어 동작
- **C (정상 진입, False Positive 억제)** — 진짜 호재 패턴에서 S_entry > θ 최소 빈도 유지 (n ≥ 50 / 6개월)
- **D (Kill Switch 발동)** — 4층 각 1회 이상 실발동·회복 훈련 Paper 기간 내 완료
- **E (heartbeat 상실 DR)** — 4h 무응답 시 서버측 자동 전량 시장가 청산 검증

### Business Success (Capital Performance)

Athena는 상용 제품이 아니므로 "Business Success"를 **자본 운용 성과**로 재정의한다.

**6개월 1차 목표** (실거래, 세후, 기하평균, 레버리지 0)

| 지표 | 목표 | 표본·측정창 | 선언 조건 |
|---|---|---|---|
| 월 수익률 연간화 | > 30% | n ≥ 6개월 · 50+ 트레이드 | bootstrap CI 하한 > 0 |
| Deflated Sharpe | > 1.5 | 일별, Bailey·López de Prado | — |
| Max Drawdown | < 10% | 일별 NAV | — |
| 설거지 회피율 | > 90% | 월, 의심 라벨링 기준 사전 정의 | 월 5건+ 의심 |
| 이벤트 손실 경감률 | > 75% | 이벤트당 vs MVP-없을시 추정손실 | 이벤트 3건+ |

**자본 확장 게이트 (조건부)**
- **초기:** 10-30만 원 단위. KPI 규율·Kill Switch 훈련·Living Label 기동 목적
- **≥ 1,000만 원:** 외부 승인권자 위임 + KIS 준법감시인 서면 통지 + 가족 1인 비상정지 권한 공증 위임 **자동 트리거**
- **Flag Down:** MDD ≥ -10% 또는 override 로그 단절 시 시스템 off → 3일 냉각기 + Paper Trading 1주 재통과

**12-24개월 2차 목표 (V1.1+ 진입 조건)**
- V1.0 KPI 지속성 공고화 (n ≥ 12개월, 100+ 트레이드, Deflated Sharpe > 1.5)
- V2.x 해금 Meta-gate: 위 조건 통과 후에만 연구 테마 착수. *연구 테마는 규율의 도피구가 되지 않는다.*

### Technical Success

**MVP (12주) 기술 완성 기준**

| 범주 | 지표 | 목표 | 측정 |
|---|---|---|---|
| 레이턴시 | 시그널 p99 | < 5초 | Prometheus histogram_quantile |
| 가용성 | L2 로거 uptime | ≥ 99% | 24/7, 미달 시 paper-only 전환 |
| DR | heartbeat 무응답 4h | 자동 전량 flatten | Paper 기간 실발동 훈련 |
| DR | 서버측 OCO stop (M22) | 트레이더 override 불가 증명 | tamper 테스트 |
| DR | Secondary 증권사 Adapter | KIS 장애 fallback 동작 | DR 드릴 |
| 감사 | Pre-Trade Ledger | append-only SHA-256 체인, 100% 완전성 | 월간 해시 검증 |
| 감사 | F5 tamper-evident | 장중 파라미터 변경 0건 + git revert 방어 | 보안 감사 |
| 드리프트 | F1 월간 재학습 | PSI < 0.2 | 초과 시 paper-only 자동 전환 |
| 모듈 | 52 veto flag missing 허용 | 월 missing > 3 → neutral(1) degrade + 경보 | 감사 리포트 |
| 보안 | API Key | OS Keychain (.env 금지) | 코드 스캔 |

### Measurable Outcomes — 8대 KPI Dashboard

전부 세후 · 기하평균 · 레버리지 0 기준. **엄격함 > 기회 포착** 원칙에 따라 "n 미달로 인한 미선언"은 실패가 아닌 시스템 정상 작동으로 간주한다.

| # | 지표 | 목표 | 제외 규칙 |
|---|---|---|---|
| 1 | 월 수익률 (세후 기하평균 연간화) | > 30% | 첫 주 안정화 구간 제외 |
| 2 | Deflated Sharpe | > 1.5 | — |
| 3 | Max Drawdown | < 10% | — |
| 4 | 설거지 회피율 | > 90% | 의심 라벨링 기준 사전 정의 |
| 5 | 이벤트 손실 경감률 | > 75% | 이벤트 3건+ |
| 6 | 시그널 레이턴시 p99 | < 5초 | 1000+ 신호 |
| 7 | Override 로그 완전성 | **100%** | 시도 발생 시 전수 기록 |
| 8 | F1 드리프트 PSI | < 0.2 | 초과 시 paper-only 자동 전환 |

## Product Scope

### MVP — Minimum Viable Product (12주, V1.0 Launch)

**MVP 10 모듈** — {M1, M2, M3, M9, M13, M14, M19, M22, F1, F5}

**외부 기만 방어 (8개)**
- M1 Linguistic Certainty Scorer (KB-BERT + finance_sentiment_corpus)
- M2 Narrative Age Tracker (SBERT + Omori decay)
- M3 Pre-News Drift Z-Detector (microstructure)
- M9 Time-of-Day Regime Multiplier
- M13 Two-Stage Hybrid Scorer (XGBoost → 비동기 LLM)
- M14 Basket Coherence Gate (Transfer Entropy)
- M19 Loss Acceleration Trigger
- M22 Hard-Locked Stop Loss (서버측 OCO 이중화)

**내부 편향 방어 (2개)**
- F1 Bargaining Language Detector (본인 일지 250건 수작업 라벨)
- F5 Parameter Hard-Lock (append-only 해시체인 + git revert 방어)

**MVP 필수 인프라 (비-모듈)**
- ★ L2 호가창 WebSocket 로거 24/7 무중단 (Week 1 Day 1 최우선)
- DuckDB 기반 Feature Store + 통일 스키마 (V1.1+ 확장 대비 모듈 경계)
- Pre-Trade Authorization Ledger (append-only SHA-256 체인)
- 4층 Circuit Breaker (Global · Account · Session · Symbol)
- Secondary 증권사 Adapter 추상화 계층 (MVP는 설계까지, 구현은 V1.1+)
- Prometheus + Grafana + Alertmanager (카카오워크/Telegram bot)
- **Compliance Guardrails (MVP 필수):** 허수성 호가 상한, 분당 주문 수 상한, 취소율 < 30%, OS Keychain API key, 세후 수익률 계산(M_tax), 대주주 요건 추적, §176/§178/§178-2 가드레일 수식 내장

**MVP 검증 Gate (V1.0 Launch 전 통과 필수)**

1. Paper Trading 2주 완주
2. Kill Switch 4층 각 1회 이상 실발동·회복
3. DR 시나리오 (heartbeat fail → auto flatten) 실훈련
4. Out-of-sample 미경험 사건 5-10건 재계산 (88% 손실 경감 가설 검증)
5. 공매도 재개(2025-03-31) 전후 레짐 분리 walk-forward 백테스트 통과
6. 자본시장법 체크리스트 (KIS 준법감시인 서면 통지 조건부 트리거 확정)

### Growth Features (Post-MVP, V1.1+)

**Priority ⭐⭐⭐ (M4-6개월 편입 목표)**
- M7 Regime Classifier (Trend/Chop/Crash 3상태)
- M11 Valuechain Directed Graph (NetworkX 산업 밸류체인 DAG)
- M12 Transfer Entropy + R0 Estimator
- M16 Implied-Vol & Event Proximity Sizer
- M23 Multi-Trigger Exit Orchestrator
- M25 Explainable Veto Report Generator

**Priority ⭐⭐ (M6-12개월)**
- M8 Market Criticality Thermometer
- M15 Kelly with Veto Discount
- M18 Lead-Follow Timing
- M20 Anchor Point Decay
- M24 Bayesian Flag Trust + Shadow Attribution

**Supporting (자체 L2 2년 데이터 축적 후 활성화)**
- M4 Order Book Wall Life Analyzer
- M5 Trade Size Distribution Monitor
- M6 Deception Keyword Density
- M10 b-value & Stress Accumulation (Gutenberg-Richter)
- M17 Cooldown & Randomization Gate
- M21 Momentum Decay Detector
- F2 Self-FOMO Behavioral Sensor
- F3 Physiological Override (심박·수면부채)
- F4 Third-Person Re-decision Prompt

**V1.1+ 진입 Meta-gate**
- V1.0 KPI n ≥ 6개월 관측치로 선언 조건 통과
- L2 호가창 2년치 축적 진행률 > 50%

### Vision (V2.x 연구 테마, M12+)

**V2.x 해금 Meta-gate** — V1.0이 n ≥ 6개월, 100+ 트레이드, Deflated Sharpe > 1.5 유지 통과 후에만 착수.

- #82 Red Team GAN Auto-Adversary — 자기 강건화
- #80 Stackelberg Reverse Engineering — 세력-본인 게임이론
- #84 Common Knowledge Cascade — Morris 1990
- #85 Beauty Contest Tracker — Keynes 2차/3차 추론
- #78 Integrated Information Φ — 의식 이론 이식
- Hypergraph NN — 3자·4자 고차 상호작용
- #30 Joint Copula Interaction — 다변량 꼬리 의존성

### Explicit Non-Goals (영구 배제 — Change Control 차단)

- ❌ 스캘핑/HFT (< 1초 레이턴시) — 5초 예산 초과
- ❌ 파생상품·해외주식 — KRX 주시장 only
- ❌ NXT 다시장 연동 — V1.1+ 유보
- ❌ No-code UI · 상용화 · 타 사용자 확장 — §17/§18 영구 배제
- ❌ 실시간 LLM blocking 호출 — 비동기 2단계만 허용
- ❌ 가족·지인 계좌 위임 — 무인가 투자일임업
- ❌ 코드·파라미터·시그널 대외 공개 — 투자권유 해석 소지

**Change Control:** MVP 12주 중 모듈 추가·삭제는 문서화된 변경요청(CR) 거쳐 **최대 1건만** 허용. 초과 시 12주 일정 자동 리셋. 주말 파라미터 튜닝은 git commit + 72h cooling + Paper Trading 재검증 없이 prod 반영 금지.

---

## User Journeys

Athena는 단일 사용자 Khuk0의 **다섯 가지 역할 모드**를 서비스한다. 각 모드는 동일 인물이지만 시간·상태·심리 조건이 다르며, 별도의 기능 요구사항을 생성한다.

### Persona: Khuk0 — Single User, Multi-Role

- **배경:** 한국 주식시장 단기 매매 10년차. 수학적 추상과 구체적 시장 현실 사이 빠른 왕복. 자신의 두 실패(2025-11 유리기판 A사, 2023-12 바이오 C사)를 객관화해 시스템 아키텍처로 환원한 도메인 전문가
- **현재 상황:** 월 수익률 변동성 크고, 치명적 단일 손실이 3개월치 알파를 날림. 본인 감각만으로는 외부 기만과 내부 편향을 모두 방어할 수 없음을 인정
- **원하는 상태 (Cognitive Prosthesis):** 장중 override 유혹이 들어와도 시스템에 막혀 "기묘한 안도감"을 느끼는 상태. 뇌는 연구·전략에만 집중
- **장애물:** 12주 구축 기간의 역량·시간 제약, 실패 사례가 in-sample에 머무르는 위험, KIS API 장애, 자신의 파라미터 override 충동

---

### Journey 1 — Trading Mode: 설거지 덫 재발 회피 (Happy Path / Scenario A)

**Opening.** 09:05. 방금 속보: "유리기판 관련주 대기업 투자 확대." 과거라면 심박이 급등하고 마우스가 이미 매수 호가를 치고 있었을 장면.

**Rising Action.** Athena 파이프라인이 동시 가동:
- M1 확실성 0.82 (높음, 위험 신호)
- M2 서사 나이 3일차 (피크 근접) 0.52
- M3 공시 전 1h Z=3.1 비정상 거래량 → 0.159 (내부자 의심)
- M14 밸류체인 일관성 Transfer Entropy 음수 → 0.50
- M9 시간대 multiplier 0.49 (장초 위험 프리미엄)

**Climax.** 대시보드: **"S_entry = 0.014 (θ=1.0). 진입 거부. 이유: M3 선행 표류 + M14 바스켓 역전 + M2 서사 소진."** 매수 버튼 비활성화. M25 설명 리포트 자동 생성 + Pre-Trade Ledger append-only 저장.

**Resolution.** 답답함이 아닌 **기묘한 안도감**. *"아, 내 뇌가 또 속으려 했구나."* 커피를 마시고 다음 감시 종목으로 넘어간다. 12시 해당 종목 -12% 마감. Athena는 100% 회피했다.

**요구 Capability:** 뉴스 실시간 파싱+KB-BERT(M1,M2) · L2 Z-score 엔진(M3) · Transfer Entropy(M14) · 시간대 multiplier(M9) · S_entry 집계+θ 비교+거부 이유 리포트(M25) · 매수 버튼 UI 비활성화(F5 연동) · Pre-Trade Ledger 감사 기록

---

### Journey 2 — Trading Mode: 임상 3상 override 시도 차단 (Edge Case / Scenario B)

**Opening.** 15:37. 바이오 종목 포지션 보유 중. D-day 임상 발표 예정. 15:40 "임상 3상 실패" 속보. 과거라면 내부 목소리: *"조금만 기다려보자, 이번엔 다르다."*

**Rising Action.**
- M16이 이미 D-3부터 포지션 50% 자동 축소 상태
- M22 Hard-Locked Stop이 뉴스 수신 0초 후 서버측 시장가 강제 청산
- 파라미터 변경 창 열기 시도 → F5 장중 읽기전용 마운트 확인 차단
- 채팅창 타이핑: *"조금만 더 기다려..."* → F1 Bargaining Detector 실시간 감지, Anti-Ego Firewall 플래그 1→0

**Climax.** 대시보드 빨간 경고: **"F1 감지: Bargaining Language 0.87 · F5 하드락: 장중 파라미터 수정 불가 · M22 청산 완료: -3.5%."** 마우스를 밀어낸다. 호흡은 가빠지지만 물리적 override가 차단되어 있음을 안다.

**Resolution.** 저녁, 감사 로그 확인. F1 감지 흥정 언어 3건 · F5 차단 수정 시도 1건 · M22 강제 청산 1건 모두 해시체인 기록. 과거 C사 -15% 대비 오늘 -3.5% (**77% 경감**). 월간 회고: *"시스템이 내 대신 규율을 지켰다. 이 감각이 Cognitive Prosthesis다."*

**요구 Capability:** M16 Event Proximity 자동 축소 · M22 서버측 OCO+tamper-evident · F1 실시간 언어 감지(채팅·메모·장중 입력 소스 hook) · F5 장중 읽기전용 마운트+append-only 해시체인 · Anti-Ego Firewall 상태 UI · 월간 override 감사 리포트

---

### Journey 3 — Operator Mode: 주간 F1 라벨 재학습 (Off-hours Routine)

**Opening.** 토요일 오전. 이번 주 트레이딩 로그 확인: F1 감지 흥정 언어 12건, Kill Switch 발동 0건, 새 override 시도 2건.

**Rising Action.**
- Prometheus 대시보드: L2 로거 uptime 99.7% (목표 99% 통과)
- F1 라벨링 워크플로우: 새 2건 override 시도 데이터셋 추가 (누적 252건)
- PSI 자동 계산: 0.14 (임계 0.2 미만 → 정상, paper-only 전환 불필요)
- Walk-forward 백테스트 재실행 (지난 주 포함) → θ_entry 후보값 확인

**Climax.** Sunday 밤 F1 재학습 완료. PSI 재검증 0.11로 하락. KPI 대시보드: 월 수익률 누적 연간화 +32% (목표 통과), Deflated Sharpe 계산값 1.7 (n=38 trades, 50+ 미달이라 **선언 보류**). 원칙에 따라 *선언 보류를 정상으로 수용* — "엄격함 > 기회 포착".

**Resolution.** 월요일 아침 Athena는 재학습된 F1 가중치로 자동 가동. 파라미터 변경은 git commit + 72h cooling + Paper 재검증 pending 상태.

**요구 Capability:** Prometheus/Grafana 대시보드 · F1 라벨링 도구(GUI/CLI) · PSI/KS 드리프트 자동 계산 + paper-only 자동 전환 트리거 · Walk-forward 백테스트 러너(레짐 분리 포함) · 파라미터 변경 72h cooling + Paper 재검증 enforce · KPI 누적 대시보드 + 선언 조건 충족 여부 실시간 표시

---

### Journey 4 — Incident Responder: heartbeat 상실 + KIS API 장애 (DR Scenario E)

**Opening.** 화요일 11:23. 회의 중. 스마트폰 Telegram bot: **"heartbeat 지연 5분 — 로거 PC에서 응답 없음."**

**Rising Action.** 5분 전 아파트 인터넷 단절. 로거 PC는 LTE 라우터 fallback 중이나 KIS WebSocket reconnect 루프 진입. 트레이딩 PC는 독립 인터넷으로 정상이나 heartbeat 신호는 로거 PC에서 끊김.

MTS 앱 오픈 → 오픈 포지션 2종목 확인. 서버측 카운트다운: **heartbeat 무응답 4h 중 3h 54분 남음** (자동 flatten 전 수동 복구 시도).

**Climax.** LTE 테더링으로 노트북 접속 → 로거 PC 원격 접속, WebSocket 재연결 수동 트리거. 2분 후 heartbeat 복구. Telegram bot: **"heartbeat OK. 신규 진입 차단 해제."** 동시에 KIS API `EGW00201` rate limit 에러 반환 중. Secondary Adapter가 V1.1+라 수동 모니터링으로 대응.

**Resolution.** 사건 로그 작성: 원인(아파트 인터넷) · 대응(LTE → 원격 로거 재시작) · 소요(11분) · 훈련 추가(LTE fallback 자동 감지 스크립트). 이 사건이 V1.1+의 Secondary Adapter 우선순위를 ⭐⭐⭐로 승격.

**요구 Capability:** heartbeat 4h watchdog + 서버측 자동 전량 flatten · heartbeat 5분 지연 모바일 푸시(Telegram/카카오워크 bot) · 로거 PC ↔ 트레이딩 PC 물리 이중화(MVP 필수) · LTE 라우터 fallback + UPS(MVP 필수) · Secondary 증권사 Adapter 추상화 계층(MVP 설계, V1.1+ 구현) · KIS rate limit 에러 자동 throttle + 로깅 · Incident log 템플릿 + 월간 DR 훈련 체크리스트

---

### Journey 5 — Capital Gate Crosser: 자본 ≥ 1,000만 원 도달 (Compliance Trigger)

**Opening.** V1.0 런칭 4개월 후. 누적 자본 1,000만 원 돌파. 시스템 자동 compliance 트리거 발동.

**Rising Action.** 대시보드 경고: **"자본 ≥ 1,000만 원 도달. 다음 작업 필수:"**
1. KIS 준법감시인 서면 통지 (이메일 템플릿 자동 생성)
2. 가족 1인 MTS OTP 비상정지 권한 공증 위임
3. 외부 승인권자 위임 서약서 작성

**Climax.** 템플릿 이메일 검토·서명 후 발송, 회신 수령 + Pre-Trade Ledger append. 가족과 공증 사무소 방문 → OTP 권한 위임 공증. 서약서 git signed commit.

**Resolution.** 자본 확장 모드 unlock. Account-level Kill Switch가 가족 비상정지 권한과 연동되어 헤어 트리거 상태. 규제 준수는 "귀찮은 작업"이 아닌 **자본이 커질수록 자동으로 상승하는 보호막**이 된다.

**요구 Capability:** 자본 실시간 모니터링 + threshold 트리거 · KIS 준법감시인 통지 템플릿(이메일·회신 보관) · 가족 OTP 위임 공증 체크리스트 + git 기록 · 외부 승인권자 서약서 템플릿 · Account-level Kill Switch의 가족 비상정지 권한 연동

---

### Journey Requirements Summary

5개 Journey가 드러내는 **FR 클러스터 → MVP 포함 여부** 매핑:

| FR 클러스터 | Journey 출처 | MVP 포함 |
|---|---|---|
| Entry Scoring Pipeline (M1-M14, S_entry 집계) | J1, J2 | ✅ MVP |
| Anti-Ego Firewall (F1, F5, 읽기전용 마운트) | J2 | ✅ MVP |
| Exit & Stop System (M19, M22; M16 partial) | J2 | ✅ MVP (M16은 V1.1+) |
| Kill Switch 4층 (Global/Account/Session/Symbol) | J2, J4 | ✅ MVP |
| DR Infrastructure (heartbeat, 물리 이중화, LTE) | J4 | ✅ MVP |
| Secondary Adapter (KIS fallback) | J4 | 🟡 MVP 설계 / V1.1+ 구현 |
| Monitoring & Alerting (Prometheus, Telegram bot) | J3, J4 | ✅ MVP |
| F1 Labeling Workflow | J3 | ✅ MVP |
| Drift Detection (PSI, KS, paper-only 자동 전환) | J3 | ✅ MVP |
| Walk-forward Backtest | J3 | ✅ MVP |
| Compliance Automation (준법감시인 통지, 공증) | J5 | 🟡 MVP 템플릿 / 트리거는 자본 확장 시 |
| Capital Threshold Monitor | J5 | ✅ MVP |
| Pre-Trade Ledger (append-only SHA-256) | J1, J2, J4 | ✅ MVP |
| Explainable Report (M25) | J1 | 🟡 MVP는 간단 버전 / 풍부한 V1.1+ |

---

## Domain-Specific Requirements

### Compliance & Regulatory (한국 자본시장법 & 관련법)

**D-C1. 자본시장법 §176 시세조종행위 금지 (MVP 가드레일 수식 내장)**
- 허수성 호가: 동일 호가 반복 상한
- 취소율 < 30% 하드 제한
- 분당 최대 주문 수 상한 (계정별 튜닝)
- 가장·통정매매: 본인 계좌 단일 사용, 타 계좌 위임 영구 금지

**D-C2. 자본시장법 §178 부정거래·§178-2 시장질서 교란 (과실도 처벌)**
- Pre-Trade Authorization Ledger (append-only, SHA-256 체인) 필수
- 모든 주문에 `S_entry 값`, `통과 Gate 목록`, `param_hash`, `policy_version_git_sha`, `시각 hash` 기록
- 월간 외장 백업 (외장 디스크 또는 S3 write-only)

**D-C3. 자본시장법 §17 투자자문업 / §18 투자일임업 금지 (Scope Lock 준수)**
- 코드·파라미터·시그널 대외 공개 영구 금지
- 타인 계좌 위임 영구 금지
- 가족·지인 계좌 위임 영구 금지
- 2026-04-20 Scope Lock 확정, PRD 전체 관통 원칙

**D-C4. 공매도 재개 (2025-03-31) 레짐 적응**
- NSDS(Naked Short-selling Detecting System) 가동 이후 기관 행태 변화 대응
- Walk-forward 백테스트에서 **2025-03-31 전후 레짐 분리 검증 필수** (V1.0 Launch 조건)
- 본 시스템은 롱 전용이므로 공매도 직접 구현 불필요

**D-C5. 소득세법·증권거래세법 (M_tax 모듈 필수)**
- 세후 수익률 계산: 증권거래세 0.18% (코스피 0.03% + 농특세 0.15%), 배당세 15.4%
- 금투세 폐지 (2025-01-01) 반영, 양도소득세 체계만 적용
- 대주주 요건 추적: 종목당 지분 1% 또는 시가 10억 원 근접 시 M_tax 경보

**D-C6. 전자금융거래법 §9, §21**
- §9 이용자 고의·중과실 시 책임 면제 조항 인지
- §21 안전성 확보의무 → OS Keychain API key 저장, .env 영구 금지

**D-C7. 한국거래소 시장감시규정 §4 (이상거래 심리기준)**
- 허수성 호가·연속매매 패턴 자체 경고 로그 + 월간 자기 감사

**D-C8. KIS 준법감시인 통지 (조건부 자동 트리거)**
- 초기 10-30만 원 규모: 시장 영향 미미, **불필요**
- **자본 ≥ 1,000만 원 또는 일일 주문 > 50건** 도달 시 자동 트리거
- 운용계획·예상 주문빈도·취소율·본인 자본 전용 이메일 고지 + 회신 보관 (Ledger append)

### Technical Constraints

**D-T1. 실시간 레이턴시 예산**
- 시그널 생성 p99 < 5초 (Prometheus histogram_quantile 측정)
- 서브-초 스캘핑은 명시적 범위 밖
- LLM 호출은 비동기 2단계만 허용 (블로킹 경로 금지) → M13 Two-Stage Scorer
- LLM 타임아웃 2초 + fallback to 1단계

**D-T2. 호가창 L2 데이터 (Time-Travel Rights)**
- KIS Tick 히스토리 미제공 → 자체 WebSocket 로거 24/7 무중단 (Week 1 Day 1 최우선)
- DuckDB 컬럼 지향 저장: `ts, symbol, bid/ask 10호가, 체결가·수량`
- 목표 2년 축적 → V1.1+ M4/M5/LOBFrame 기반 확장 원료

**D-T3. KIS API 제약**
- REST 약 20 req/s (초과 시 `EGW00201` rate limit 에러)
- WebSocket 실시간 시세 구독 41건/세션 (HTS ID 오류 시 "No close frame received")
- OS레벨 token-bucket throttle 구현 (MVP)
- 모의계좌는 실계좌 대비 제한 낮음 (파라미터 최적화·연속 호출은 실계좌 권장)

**D-T4. 고가용성 & DR**
- L2 로거 uptime ≥ 99% (미달 시 paper-only 자동 전환)
- heartbeat 4h 무응답 → 서버측 자동 전량 flatten + 신규 진입 영구 차단 (수동 해제 필요)
- 물리 이중화: UPS + LTE 라우터 + 로거 PC ≠ 트레이딩 PC (인터넷 차단·화이트리스트)
- Secondary 증권사 Adapter: MVP는 추상화 계층, V1.1+ 구현

**D-T5. 감사 & Tamper-Evident (운영 방어 트랙)**
- Pre-Trade Authorization Ledger (append-only, SHA-256 월간 체인 해시)
- F5 장중 파라미터 수정 물리 차단 (읽기전용 마운트 + git revert 방어)
- 모든 정책 변경은 git signed commit + 72h cooling + Paper 재검증
- append-only 로그 외장 백업 (외장 디스크 또는 S3 write-only)

**D-T6. 실행 품질 — Execution Slippage (Blind Spot A, 운영 방어)** ★
- 슬리피지 실측: 시그널가 vs 체결가, tick 단위 기록
- 슬리피지 > **0.3%** 시 해당 신호 후속 진입 S_entry × 0.5 discount
- 취소·재주문 패턴 자동 throttle (자본시장법 §176 연계)
- 장초 1h 유동성 얇은 구간 특별 감시 flag

**D-T7. 데이터 무결성 — Data Quality (Blind Spot C, 운영 방어)** ★
- 뉴스 피드 타임스탬프 검증: > 30초 지연 시 해당 신호 drop
- KB-BERT·LLM confidence < 임계값 시 neutral(1) 처리 (곱셈 파이프라인 오염 방지)
- 월간 feature 분포 drift 모니터링 (F1 PSI 외 M1·M9 등 주요 feature 확장)
- 52 flag *missing* 허용(neutral=1) + **틀린 값 감지** 이중 장치

**D-T8. Portfolio 리스크 — Correlation / Concentration (Blind Spot B, 운영 방어)** ★
- 동시 오픈 포지션 수 상한: **MVP 3종목**
- 동일 테마·섹터 2종목 이상 동시 보유 금지 (최소 버전)
- V1.1+: M15 Kelly with Veto Discount + M11 밸류체인 그래프 기반 correlation matrix 확장
- Max DD < 10% KPI를 깨는 주 경로로 인식하고 매일 감시

**D-T9. 보안**
- API key: OS Keychain / HSM 수준 저장 (.env 영구 금지)
- 주문 키 ↔ 조회 키 분리
- KIS MTS에서 일일·종목별 최대 주문금액 하드 제한
- 코드·git 리포지토리·.env 파일에 secret 직접 저장 금지

### Integration Requirements

**D-I1. 증권사 API — Primary: KIS Developers**
- REST + WebSocket, python-kis 라이브러리 (타입 안전, 자동 재연결, 조회 자동 재등록)
- 실계좌 + 모의계좌 각 1개 (개발·검증용)

**D-I2. 증권사 API — Secondary Adapter (MVP 설계 / V1.1+ 구현)**
- 주문 DTO 추상화 계층 (KIS와 동일 interface)
- V1.1+ 후보: eBEST 또는 대신 CREON

**D-I3. DART OpenAPI (공시)** — 실시간 공시 크롤러, 무료, Feature Store 정규화 저장

**D-I4. 뉴스 피드** — 네이버/다음 금융 · 연합뉴스 · 매경 · 한경 RSS/크롤링. 타임스탬프 필수 (D-T7 연계). 금융 빅데이터 플랫폼 DART 감정 점수는 선택 보조 feature.

**D-I5. 과거 데이터 백필** — pykrx (OHLCV + VI 이력 2년). 자체 L2 로거는 Tick 수준 Week 1 Day 1부터 실시간 축적.

**D-I6. 알림 & 모바일** — Telegram bot 또는 카카오워크 (heartbeat 5분 지연 push). Prometheus + Grafana + Alertmanager.

**D-I7. NLP 모델** — KB-BERT 로컬 추론 (<100ms, MVP 기본축) + finance_sentiment_corpus fine-tune 원료. HyperCLOVA X / Solar Pro 2는 비동기 2단계 전용 (M13).

### Risk Mitigations (Top 6 핵심 + 3 Blind Spot)

**핵심 6 리스크**

| # | 리스크 | 심각도 | MVP 완화 | 조기경보 |
|---|---|---|---|---|
| 1 | 호가창 Tick 히스토리 부재 | Critical | Week 1 Day 1 자체 L2 로거 + DuckDB 스키마 | 로거 uptime < 99% → paper-only |
| 2 | 오픈 포지션 중 서버/네트워크 다운 | Critical | 서버측 OCO + heartbeat 4h auto-flatten | heartbeat 지연 > 5분 |
| 3 | 자본시장법 §176/§178/§178-2 위반 | High | 분당 주문 상한 + 취소율 < 30% + Pre-Trade Ledger + (조건부) 준법감시인 통지 | 취소율 > 20% → auto throttle |
| 4 | KIS API 장애·rate limit | High | Secondary Adapter 설계 + OS token-bucket + 수동 MTS 청산 플레이북 | EGW00201 에러 급증 |
| 5 | 곱셈형 Veto False Negative 폭발 | Medium | 센서 결측 → neutral(1) degrade + missing rate 월간 감사 | 52 flag missing > 3개 |
| 6 | F1 라벨 드리프트 | Medium | 월 20건 추가 라벨 + PSI/KS + 분기 재학습 gate | PSI > 0.2 → paper-only |

**3 Blind Spot (운영 방어 트랙)**

| 리스크 | 심각도 | MVP 완화 | 조기경보 |
|---|---|---|---|
| Execution Slippage (D-T6) | High | 슬리피지 실측 + 임계 초과 시 S_entry × 0.5 discount | 일별 평균 슬리피지 > 0.2% |
| Portfolio Correlation Bust (D-T8) | High | 동시 포지션 3종목 상한 + 테마 중복 금지 | 오픈 포지션 테마 cosine > 0.8 |
| Data Integrity GIGO (D-T7) | Medium | 타임스탬프 검증 + confidence neutral(1) 처리 | 뉴스 지연 > 30s 빈도 증가 |

---

## Innovation & Novel Patterns

### Detected Innovation Areas

Athena는 다음 **4가지 근본 혁신**을 포함한다. 모두 **리테일 알고리즘 트레이딩 시장** 기준 혁신이며, 기관 운영 환경은 별도 범주로 구분한다.

**I-1. 곱셈형 Veto Gate 아키텍처 (Multiplicative Veto Architecture)**

업계 표준: `Score = αN + βV + γO` 형태의 **덧셈 스코어 모델**. 개별 신호의 평균을 최대화하므로 한 개의 거짓 신호가 다른 신호의 양수 기여에 흡수되어 오검 유발.

Athena: `S_entry = 1[¬HardKill] · (αN+βV+γO) · Π G_i · M_regime · M_time`의 **`Π G_i` (52개 veto flag 곱셈)** 구조. 한 개 flag가 0에 근접하면 전체 S_entry가 0으로 수렴 → **단일 거짓 신호로 전체 진입 차단**. 비대칭 파괴력을 가진 단일 실패(설거지 덫, 임상 3상 override)에 대한 구조적 방어.

*도전하는 가정:* "더 많은 신호를 결합하면 더 정확하다"는 가산적 합리주의. Athena는 "하나의 거짓말이 전체를 오염시킨다"는 곱셈적 비관주의로 뒤집는다.

**I-2. Anti-Ego Firewall — 트레이더 본인을 1급 위협으로 모델링**

기존 리테일 제품(Time Percent 등)은 시장 데이터만 모델링. 기관 Risk Desk는 트레이더를 통제하나 이는 **"타인에 의한 제3자 통제"** 로 리테일 복제 불가.

Athena의 F1-F5는 트레이더 본인의 **내부 언어(F1), FOMO(F2), 생리(F3), 재결정 프롬프트(F4), 파라미터 잠금(F5)** 을 시장 데이터(M1-M25)와 동일 파이프라인에서 **단일 인물 자기-통합(self-integrated) 형태로** 처리.

*핵심 혁신:* F1은 본인 일지 **250건 수작업 라벨**로 학습. 외주·복제 구조적 불가능한 **인격적 데이터 자산**이며, 타인 사용 시 즉시 효력 상실 (이는 §17/§18 규제 충돌과 별개로 본질적 1인용 이유).

*도전하는 가정:* "알고리즘은 시장만 보면 된다." Athena는 "10년차 트레이더의 실패는 시장보다 자기 자신에게서 온다"는 인정으로 시작한다.

**I-3. 9개 타 도메인 수학의 실패 양식별 1:1 이식 (Cross-Domain Transplant)**

비유가 아닌 **실제 수학 모델의 직접 이식**:

| 이식 수학 | 원 도메인 | Athena 모듈 | 포착 실패 양식 |
|---|---|---|---|
| SIR / R0 / Super-spreader | 전염병학 | M11, M12, M14 | 밸류체인 전이 한계 |
| Watts cascade / PageRank | 네트워크 과학 | M11, M18 | 임계점 통과 비선형 확산 |
| SOC / Power-law / Phase transition | 통계물리 | M8, M10 | 소사건 → 대붕괴 임계성 |
| Omori law / Gutenberg-Richter | 지진학 | M2, M10 | 뉴스 여진 감쇠, 전조 |
| Transfer entropy / Φ | 정보이론 | M12, V2.x #78 | 인과 정보 전이 |
| Stackelberg / ESS / Common knowledge | 게임이론 | V2.x #80, #84 | 세력-개인 비대칭 게임 |
| Critical branching ratio | 신경 사태 | M8 | 시장 임계 분기 |
| Bass diffusion / Hype cycle | 밈 확산 | M2 | 서사 S-curve 소진 |
| Trophic cascade / Keystone | 생태학 | M11, M14 | 키스톤 종목 제거 붕괴 |

*도전하는 가정:* "금융은 금융 안에서 풀어야 한다"는 학문적 고립. Athena는 **실패 양식 간 동형성(isomorphism)** 을 믿고 도메인 횡단을 선택한다.

**I-4. Living Label Asset — 운영 시간의 복리 비대칭**

Athena의 학습 자산은 **운영 시간 자체가 모델 강건성의 복리 함수**가 되는 구조:
- F1 라벨: 250건 + 실거래 이후 모든 override 시도·흥정 언어·근접 사건 자동 흡수
- L2 호가창 2년 자체 백필: Week 1 Day 1부터 축적, 공매도 재개·밸류업·NXT 전환기를 한 관찰자 시점에서 기록한 **유일 데이터셋**

자본·인력으로 단축 불가능한 시간 기반 비대칭이며, 어떤 후속 연구(레짐 전이, 세력 행동 변화, NXT 유동성 이주)에도 과거로 돌아가 답할 수 있는 **옵션 가치**.

*도전하는 가정:* "모델 성능은 데이터 양으로 결정된다"는 static view. Athena는 "**특정 시점을 놓치면 영구히 복구 불가능한 데이터가 존재한다**"는 시간 기반 asymmetry로 확장한다.

### Market Context & Competitive Landscape

| 세그먼트 | 대표 | Athena와의 관계 |
|---|---|---|
| No-code 퀀트 (리테일) | Time Percent Trading Bank | 상이 세그먼트, **경쟁 아님** |
| 증권사 알고 주문 | KIS, 키움 | 집행 전용, **보완 관계** |
| 해외 SaaS | QuantConnect, Alpaca | 미국 중심, 한국어 NLP·호가창 부재 |
| 헤지펀드 퀀트 | 국내외 기관 | 자본·인력·L2 접근 우위. **본인은 심리 방어로 차별** |
| 호가창 ML 연구 | LOBFrame (QF 2025), TLOB, LiT | **참조 아키텍처**, 한국 시장 재현은 Athena 독자 |
| 한국어 금융 NLP | KB-BERT, KoFinBERT, finance_sentiment_corpus | **공통 기반**, Athena 학습 활용 |

**경쟁 격차 원천:** 도구·API·라이브러리·공개 NLP 모델은 **평준화 상태**. 실제 격차는 2가지에만 존재:

1. **설계 사고** (veto gate × Anti-Ego 이원 파이프라인)
2. **시간 기반 자산** (L2 2년 + F1 250+ 지속 축적)

Time Percent 같은 리테일 No-code 플랫폼은 **설계 사고의 다른 차원**에 있다. 그들의 목표는 "진입 장벽 최소화", Athena의 목표는 "전문가 규율 외부화". 경쟁이 아닌 **평행 세계**.

### Validation Approach — 4-Gate 검증

혁신의 과신 방지를 위한 단계별 게이트:

**Gate 1 — In-sample Sanity (이미 확인됨)**
- MVP 10 모듈로 2건 과거 실패 재계산: Case 1 S_entry=0.014 (99.8% 삭감), Case 2 77% 경감
- 단, 이는 **설계 근거이자 in-sample 가설**이며 검증이 아님

**Gate 2 — Out-of-sample (V1.0 Launch 전 필수)**
- 본인 미경험 유사 사건 **5-10건 재계산** (유리기판·임상 외 다른 종목·시기)
- 공매도 재개(2025-03-31) 전후 **레짐 분리 walk-forward 백테스트**
- 각 모듈의 False Positive rate 측정

**Gate 3 — Paper Trading (2주)**
- 실시간 데이터 파이프라인 실주행
- Kill Switch 4층 각 1회 실발동·회복 훈련
- heartbeat 상실 DR 시나리오 실훈련
- 드러난 edge case는 **V1.0 Launch 연기 사유**

**Gate 4 — 6개월 실거래 KPI**
- Deflated Sharpe > 1.5 (n≥6개월, 50+ trades, bootstrap CI 하한 > 0)
- 선언 조건 미달은 실패가 아닌 **정상 작동** (엄격함 > 기회 포착 원칙)

**Anti-Overfit 규율:**
- θ_entry, α/β/γ 튜닝은 Bayesian + walk-forward 조합만 허용
- 주말 파라미터 튜닝은 git commit + 72h cooling + Paper 재검증 없이 prod 반영 금지
- V2.x 연구 테마는 V1.0 KPI 6개월 통과 후에만 해금 (Meta-gate)

### Risk Mitigation — 혁신 실패 시 Fallback

| 혁신 요소 | 실패 시나리오 | Fallback |
|---|---|---|
| **I-1 곱셈형 Veto Gate** | 다수 false negative 폭발, 의미 있는 진입 < n=50/6개월 | M24 Bayesian Flag Trust로 flag 실효성 사후 평가 (V1.1+). 최악 시 일부 flag를 가산 모드로 degrade — 단 북극성 원칙 위반이므로 신중 |
| **I-2 Anti-Ego Firewall** | F1 250건 라벨이 본인 언어 변화 속도 못 따라감 (PSI > 0.2) | 자동 paper-only 전환 + 월 20건 추가 라벨 + 분기 재학습. 근본 실패 시 F1 비활성화, F5 하드락만 유지 |
| **I-3 타 도메인 수학 이식** | Transfer Entropy·SIR 등 한국 단기 시장에 물리적 미스매치 | M24 Bayesian Flag Trust로 모듈별 적중률 추정 → 신뢰도 낮은 모듈 자동 격하. 최악 시 해당 모듈 V1.1+ 스코프에서 제거 |
| **I-4 Living Label Asset** | 2년 L2 데이터 축적 중 로거 uptime 극도 저하 (< 50%) | paper-only 자동 트리거 + DR 인프라 재점검. 데이터 구멍 Interpolation 금지(완전성 보호), 기간 재측정으로 대응 |
| **Overfitting 전반** | OOS gate에서 in-sample 대비 성능 급락 | V1.0 Launch 연기 + θ_entry 재튜닝 + 추가 사건 5-10건 재계산. 최악 시 MVP 모듈 10→7로 축소 |

---

## Backend Service — Internal Architecture Requirements

Athena는 외부 공개 API를 갖지 않는 헤드리스 백엔드 서비스이므로, 표준 `api_backend` 템플릿의 외부 노출 섹션(SDK·외부 인증·공개 endpoint 카탈로그)은 적용 대상 외다. 대신 **내부 모듈 경계**와 **외부 의존성 계약**을 중심으로 요구사항을 정의한다.

### Project-Type Overview — 5개 상위 도메인 (Bounded Contexts)

| 도메인 | 책임 | 주요 모듈 |
|---|---|---|
| **Feature Store** | 원시 데이터 정규화·저장·조회. DuckDB 단일 source of truth | — |
| **Alpha Defense Track** | 시장 알파 판단 (외부 기만·내부 편향 방어) | M1-M25, F1-F5 |
| **Operational Defense Track** | 실행·데이터·포지션·규제 안전장치 | Slippage, Portfolio, Data Quality, Kill Switch |
| **Decision Orchestrator** | S_entry 집계 + Firewall 검증 + 진입/거부 결정 | — |
| **Execution Gateway** | 증권사 Adapter 추상화 + 주문·체결·Pre-Trade Ledger | python-kis Primary, Secondary V1.1+ |

```
Feature Store (DuckDB)
   │
   ├─> Alpha Defense ──┐
   │   (M1-M14, F1-F5) │
   │                   ▼
   │              Decision Orchestrator
   │                   │   (S_entry > θ AND Firewall = 1)
   ├─> Operational ────┤
   │   Defense Track   ▼
   │                Execution Gateway ◄──► KIS (Primary)
   │                   │                   Secondary (V1.1+)
   │                   ▼
   └──────────> Pre-Trade Ledger (append-only SHA-256)
```

### Technical Architecture Considerations

**PT-1. 모듈 간 통신 규약 (Internal "API" 계약)**
- 모든 inter-module 통신은 **Pydantic 2 DTO** 로만 (Any/dict 직접 전달 금지)
- DTO 필수 필드: `timestamp`, `module_version`, `policy_version_git_sha`
- 동기 경로: asyncio 직접 호출 (< 1ms 오버헤드 목표)
- 비동기 경로: LLM 호출·외부 API 등 블로킹 작업은 `asyncio.Queue` 기반 비동기 파이프
- 블로킹 LLM 직접 호출 영구 금지 (D-T1 연계)

**PT-2. Feature Store 데이터 스키마**
- DuckDB 단일 source of truth, Polars DataFrame으로 in-memory 연산
- 주요 테이블:

| 테이블 | 내용 | 빈도 |
|---|---|---|
| `ticks` | L2 호가창 10호가 + 체결 | 초고빈도 |
| `quotes` | 분봉·일봉 OHLCV + VI 이력 | 분·일 단위 |
| `news` | 뉴스·공시 원문 + 파싱 feature | 이벤트 기반 |
| `modules_output` | 각 M/F 모듈 출력 (timestamp, module_version) | 신호 단위 |
| `decisions` | S_entry·통과 gate·진입/거부·policy_version | 의사결정 단위 |
| `orders` | 주문 의도·체결·슬리피지 | 주문 단위 |
| `anti_ego_events` | F1-F5 발동 이력 (append-only) | 이벤트 기반 |
| `labels_f1` | F1 본인 일지 수작업 라벨 (250건+ 축적) | 수동 입력 |

- **Commercialization-ready seam:** 모든 테이블에 `user_id` 컬럼 유지 (V1.0은 단일 값 고정, 미래 재사용 대비)

**PT-3. Error Codes & Degradation Policy**

| 에러 코드 | 원인 | Degradation 경로 |
|---|---|---|
| `EGW00201` (KIS rate limit) | REST > 20 req/s 초과 | token-bucket throttle + 재시도 최대 3회 → 실패 시 Secondary(V1.1+) |
| `FEATURE_MISSING` | 52 flag 중 일부 결측 | neutral(1) degrade + 월간 missing_rate 감사. missing > 3개 → 해당 종목 paper-only |
| `LLM_TIMEOUT` | M13 2단계 LLM > 2초 | 1단계 XGBoost 결과로 fallback |
| `CONFIDENCE_BELOW_THRESHOLD` | KB-BERT confidence < τ | 해당 feature neutral(1) 처리 (D-T7) |
| `DATA_STALE` | 뉴스 피드 > 30초 지연 | 해당 신호 drop (D-T7) |
| `HEARTBEAT_LOST` | 로거 heartbeat 5분 지연 | 모바일 푸시 → 4h 무응답 시 전량 flatten |
| `SLIPPAGE_EXCEEDED` | 슬리피지 > 0.3% | 후속 S_entry × 0.5 discount (D-T6) |
| `POLICY_NOT_COOLED` | 정책 변경 < 72h cooling | prod 반영 거부, paper-only enforcement |

**PT-4. Rate Limits (외부 의존성 계약)**
- KIS REST: token-bucket 20 req/s 하한 가정, 실측으로 튜닝 (W1 벤치마크)
- KIS WebSocket: 41건/세션 상한, 감시 유니버스 확장 시 세션 분할
- 뉴스 크롤러: 소스별 `robots.txt` 준수, 자체 rate limit 15 req/min default
- DART OpenAPI: 공식 rate limit 준수

**PT-5. Versioning & Policy Management**
- 정책 = `(수식, 파라미터, 모듈 set, 가중치)` 4-튜플의 git commit hash
- `policy_version_git_sha` 모든 decision·order에 embed (Pre-Trade Ledger)
- 정책 변경은 **git signed commit + 72h cooling + Paper 재검증** 없이 prod 반영 금지 (F5 연계)
- 모듈 개별 버전: semver (예: `M1.v1.2.0`), DTO에 embed

**PT-6. Secret Management (Internal only)**
- 외부 공개 API 없음 → 외부 인증 모델 N/A
- KIS API key, Telegram bot token 등은 **OS Keychain / HSM** 저장 (.env 영구 금지)
- KIS 주문 key ↔ 조회 key 분리 (두 개 발급)
- 로거 PC ↔ 트레이딩 PC 간 내부 통신은 로컬 네트워크 + SSH key

**PT-7. 런타임 스택**

| Tier | 구성 | 도입 시점 |
|---|---|---|
| **MVP** | Python 3.11+ · asyncio+uvloop(2.6x) · Polars(10x pandas) · DuckDB · python-kis · pykrx · KB-BERT · NetworkX · Prometheus+Grafana | W1-W8 |
| **V1.0 보강** | LOBFrame 참조 · Numba 핫패스 · HyperCLOVA X/Solar Pro 2 (비동기 2단계만) | W9-W12 |
| **V1.1+ ~ V2.x** | PyTorch Geometric GNN · TLOB/LiT fine-tune (자체 L2 후) · Rust+PyO3 핫패스 | M4+ |

**PT-8. 배포 & 실행 모델**
- 단일 호스트 상시 실행. Linux 권장 (현재 Windows 11 환경 → WSL2 또는 Linux 전환 검토)
- 로거 PC ≠ 트레이딩 PC 물리 이중화 (D-T4 연계)
- 모델 재학습은 주간 배치 (F1 + PSI 자동화)

**PT-9. 관측성 (Observability)**
- **Logs:** 구조화 JSON, 로컬 파일 + 주간 외장 백업
- **Metrics:** Prometheus (시그널 레이턴시 histogram, 모듈별 throughput, error rate)
- **Traces:** asyncio 작업 단위 trace ID (M13 2단계 병렬 경로 디버깅)
- **Alerts:** Alertmanager → Telegram bot / 카카오워크 (우선순위별 라우팅)

### Implementation Considerations

**PT-I1. 리포지토리 구조 (제안)**
- Monorepo, 모듈별 패키지:
  - `athena/feature_store`, `athena/alpha_defense`, `athena/ops_defense`, `athena/orchestrator`, `athena/execution`, `athena/core` (공통 DTO·config·logging)
- 의존성 관리: Poetry 또는 uv

**PT-I2. 테스트 전략**
- **단위:** 모듈별 결정론적 (seed 고정)
- **통합:** Feature Store → Orchestrator → Execution (mock KIS) e2e 시나리오 A/B/C/D/E
- **회귀:** 과거 2건 실패 재계산 CI 자동 실행 (in-sample S_entry snapshot 비교)
- Paper Trading은 "실환경 통합 테스트"로 간주, V1.0 Launch gate

**PT-I3. CI/CD & Branch Protection**
- `main` branch: direct push 금지, PR + 본인 self-review + CI 통과 필수
- pre-commit: black, ruff, mypy/pyright
- CI: 단위 + 통합 + 회귀 + 과거 2건 snapshot 비교
- prod deploy: manual + (정책 변경 시) 72h cooling + Paper 재검증

**PT-I4. 12주 Critical Path (선·후행 관계)**
- **W1 Day 1:** L2 로거 (다른 모든 작업의 선행)
- **W3-4:** F1 라벨 250건과 M1-M3 개발 병렬 (F1 지연 = 전체 12주 지연)
- **W9-10:** Walk-forward는 W7-8 Full MVP 완료가 prerequisite
- **W11-12:** Paper Trading + Kill Switch 실훈련 + DR 훈련 병렬
- **Change Control:** MVP 12주 중 모듈 추가·삭제 최대 1건 (Scope Lock)

---

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**Chosen MVP Type: Validated-Learning MVP** (not Revenue / Platform / Experience)

Athena의 MVP는 다음 중 어느 것도 아니다:
- ❌ **Revenue MVP** — 상용 제품 아님, 수익은 실거래 P&L로 직접
- ❌ **Platform MVP** — 단일 사용자, 확장 계획 없음 (§17/§18 Scope Lock)
- ❌ **Experience MVP** — UI 최소, 심미성 목표 아님

**Athena MVP = Validated-Learning MVP**
- **핵심 가설:** MVP 10 모듈로 과거 2건 실패 88%+ 경감 (in-sample 확인)
- **검증 대상:** 이 가설이 **out-of-sample + 실거래 6개월**에서 재현되는가
- **학습의 대가:** 실자본 노출 (10-30만 원 단계). KPI 미달 시 Flag Down + paper-only 전환으로 자산 보전
- **"학습 속도 > 제품 완성도"** 가 아닌, **"규율의 외부화 > 기회 포착"** 이 실제 MVP 가치 기준

**Resource Requirements**

| 자원 | 수량 / 제약 | 리스크 |
|---|---|---|
| 개발자 | Khuk0 1인 | Bus factor = 1 (중대) |
| 시간 | 12주 집중, 주 평균 30-40시간 추정 | 주 가용 시간 변동성 |
| 자본 | 초기 10-30만 원 | 자본 확장은 KPI 6개월 통과 후 |
| 하드웨어 | 로거 PC + 트레이딩 PC + UPS + LTE 라우터 | 물리 이중화 MVP 필수 |
| 외주 불가 항목 | F1 250건 수작업 라벨 (본인 일지 기반) | I-2 혁신의 전제 — 외주 시 효력 상실 |

### MVP Feature Set (Phase 1) — 기존 섹션 참조 요약

상세는 `Product Scope § MVP`, `Domain Requirements`, `Backend Service`를 참조한다. 여기서는 **교차 인덱스**만 유지.

| 카테고리 | 구성 | 상세 섹션 |
|---|---|---|
| **알파 방어 모듈** (8) | M1, M2, M3, M9, M13, M14, M19, M22 | Product Scope / Innovation I-1 |
| **내부 편향 방어 모듈** (2) | F1, F5 | Product Scope / Innovation I-2 |
| **필수 인프라** | L2 로거, DuckDB Feature Store, Pre-Trade Ledger, 4층 Kill Switch, Compliance Guardrails | Product Scope / Backend Service PT-2 |
| **운영 방어 트랙** (신규) | D-T6 Slippage, D-T7 Data Quality, D-T8 Portfolio (최소 버전) | Domain Requirements |
| **검증 Gate** (4단계) | OOS 5-10건 + Paper 2주 + Kill Switch 실훈련 + 공매도 전후 레짐 분리 | Innovation § Validation Approach |

**Core Journeys Supported in MVP:** J1 (설거지 덫 회피), J2 (임상 3상 override 차단), J3 (주간 F1 재학습), J4 (DR 시나리오)

**MVP 제외 (Journey는 있지만 완전 자동화 X):** J5 (Capital Gate ≥1,000만 원) — 트리거 + 템플릿까지만 MVP, 실제 발동은 자본 도달 시점

### Post-MVP Features (Phase 2 V1.1+ / Phase 3 V2.x)

상세는 `Product Scope § Growth Features` · `Product Scope § Vision` 참조.

**Phase 2 (V1.1+, M4-12개월):** 우선순위 순서
- ⭐⭐⭐: M7, M11, M12, M16, M23, M25
- ⭐⭐: M8, M15, M18, M20, M24
- Supporting: M4, M5, M6, M10, M17, M21, F2, F3, F4
- 인프라: Secondary Adapter 실구현

**Phase 3 (V2.x, M12+):** #78, #80, #82, #84, #85, Hypergraph NN, #30 연구 테마. **Meta-gate:** V1.0이 n≥6개월 + 100+ 트레이드 + Deflated Sharpe > 1.5 통과 후에만 해금.

### Risk Mitigation Strategy (Scoping-Level)

기존 Risk 섹션(Domain · Innovation)은 *모듈·혁신* 수준이었다. 여기서는 **scoping·일정·자원** 수준 상위 리스크를 다룬다.

**Technical Risks (Scoping)**

| 리스크 | 시나리오 | Contingency |
|---|---|---|
| L2 로거 uptime < 99% | WebSocket reconnect 문제, 스토리지 구조 미비 | Week 1 최우선. 미달 시 Week 2 완전 투입, M1-M3 Week 4로 지연. 최악 시 MVP 연기 |
| F1 라벨 수집이 시간 잡아먹음 | 과거 10년 일지 디지털화 예상 초과 | 최근 200건만으로 MVP 착수, 회고 50건은 V1.1+ 지속 라벨링으로 이관 |
| KIS API 실측 rate limit < 가정 | `EGW00201` 빈발 | 분당 주문 수 하드 제한 즉시 강화. Secondary Adapter MVP 승격 검토 (Change Control 1건 사용) |

**Market Risks (시장 환경)**

| 리스크 | 시나리오 | Contingency |
|---|---|---|
| 공매도 재개 이후 세력 행태 전면 변화 | 설거지 패턴 진화, 과거 데이터 기반 Veto Gate 오작동 | Walk-forward 2025-03-31 전후 레짐 분리 실패 시 MVP 연기 + in-sample 사례 추가 수집 |
| NXT 유동성 이주 → 주시장 신호 품질 저하 | Tick 구조 자체 변화 | MVP는 주시장 only 고수 (scope 유지). NXT는 V1.1+ 격리. 최악 시 감시 유니버스 재정의 |
| Tail Risk (전쟁·금융위기 외생 충격) | S_entry가 못 잡는 충격으로 MDD 급증 | Global Kill Switch 즉시 발동 + paper-only. Tail risk 감지 장치(M_volatility_macro)는 V1.1+ 개발 |

**Resource Risks (1인 개발, Bus Factor = 1)**

| 리스크 | 시나리오 | Contingency |
|---|---|---|
| Khuk0 건강·피로 | 주당 가용 시간 지속적 < 30h | 12주를 14-16주로 확장. Change Control 1건 원칙 유지, 일정만 연장, V1.0 Launch 조건 불변 |
| 개인 이벤트 (이사·가족·건강) | 1-4주 개발 중단 | Paper Trading 전환 + 일정 해당 기간만큼 일괄 연장. heartbeat 자동 flatten 의존 |
| 12주 내 MVP 불가 판명 | Week 8 체크포인트에서 주요 모듈 < 50% 완성 | scope 축소 검토: MVP 10 → 7 모듈 (M13·M14 후순위화). J5 Capital Gate는 V1.1+로 이관 |
| 외부 승인권자 부재 | override 유혹 차단 장치 약화 | F5 tamper-evident 최대 강화 + 월간 자기 감사 체크리스트 + 가족·지인 월간 구두 공유(정보 disclosure 수준) |

**Meta Risk: 완벽주의 → Scope Creep**
- **증상:** "이 모듈도 필요해" 유혹 반복, 모듈 추가 요청 대기열
- **Contingency:** Change Control **1건 원칙 엄수**. 추가 욕구는 문서화만 하고 V1.1+ 대기열로 직행. 12주 일정 자동 리셋 규정 존중. 이것이 MVP 규율의 마지막 안전장치다.

---

## Functional Requirements

> **Capability Contract:** 아래 FR 리스트는 Athena V1.0의 완전한 기능 인벤토리다. 이 리스트에 없는 기능은 V1.0에 존재하지 않는다. UX·Architecture·Epic 작성은 이 리스트만을 참조한다.

### 1. Entry Scoring & Veto Gate (Alpha Defense)

- **FR1:** 시스템은 KIS WebSocket을 통해 L2 호가창 데이터를 Week 1 Day 1부터 24/7 실시간 수집·저장할 수 있다
- **FR2:** 시스템은 DART 공시·뉴스 피드(네이버·다음·연합·매경·한경)를 실시간 수집·파싱하여 Feature Store에 정규화 저장할 수 있다
- **FR3:** 시스템은 뉴스 문장의 언어적 확실성을 0-1 스코어로 산출할 수 있다 (M1)
- **FR4:** 시스템은 동일 서사의 생애주기(신규→피크→소진)를 추적하여 서사 나이 스코어를 산출할 수 있다 (M2, Omori law decay)
- **FR5:** 시스템은 뉴스 공시 전 비정상 가격·거래량 표류를 Z-score로 감지할 수 있다 (M3)
- **FR6:** 시스템은 시간대(장전·동시호가·장초·점심·마감·장후)별 가중치 multiplier를 산출할 수 있다 (M9)
- **FR7:** 시스템은 XGBoost 1단계 + 비동기 LLM 2단계 하이브리드 스코어링을 수행할 수 있다 (M13, LLM 2초 타임아웃 + 1단계 fallback)
- **FR8:** 시스템은 밸류체인 바스켓 내 선행주-후발주 Transfer Entropy를 계산하여 일관성 gate를 판정할 수 있다 (M14)
- **FR9:** 시스템은 `S_entry = 1[¬HardKill] · (αN+βV+γO) · Π G_i · M_regime · M_time` 수식으로 52개 veto flag를 곱셈 집계하여 종목별·시점별 S_entry 스코어를 산출할 수 있다
- **FR10:** 시스템은 `S_entry > θ_entry` **AND** `Anti-Ego Firewall = 1` 조건을 모두 충족한 경우에만 진입을 허용할 수 있다
- **FR11:** 시스템은 진입 거부 시 거부 이유(어떤 gate·flag가 0이었는지)를 M25 설명 리포트로 자동 생성할 수 있다
- **FR12:** 시스템은 52 veto flag 중 일부 결측 시 해당 flag를 neutral(1)로 degrade 처리하고 월간 missing_rate를 감사할 수 있다

### 2. Anti-Ego Firewall (Internal Bias Defense)

- **FR13:** 시스템은 사용자의 채팅·메모·장중 입력에서 흥정 언어 패턴(예: "조금만 더", "이번엔 다르다")을 실시간 감지할 수 있다 (F1)
- **FR14:** 사용자는 본인 과거 일지에서 흥정 언어 사례를 수작업 라벨링할 수 있으며, 시스템은 이 라벨 250건+ 으로 F1 모델을 fine-tune할 수 있다
- **FR15:** 시스템은 F1·F5 등 Anti-Ego 모듈 판정을 집계하여 Anti-Ego Firewall 상태 플래그(0 또는 1)를 산출할 수 있다
- **FR16:** 시스템은 장중 파라미터 수정·정책 변경·git revert를 물리적으로 차단할 수 있다 (F5, 읽기전용 마운트 + append-only 해시체인 로그)
- **FR17:** 시스템은 Anti-Ego Firewall 발동·시도 이력을 `anti_ego_events` 테이블에 append-only로 기록할 수 있다
- **FR18:** 사용자는 Anti-Ego Firewall 발동 상태를 대시보드에서 실시간 확인할 수 있다

### 3. Exit & Stop Management

- **FR19:** 시스템은 오픈 포지션의 손실 가속도(2차 미분)를 모니터링하여 파열적 하락을 감지할 수 있다 (M19)
- **FR20:** 시스템은 종목 단위 Hard-Locked Stop Loss를 서버측 OCO 주문으로 이중화하여 실행할 수 있으며, 트레이더 override가 물리적으로 불가능해야 한다 (M22)
- **FR21:** 시스템은 이벤트 근접도 기반 포지션 자동 축소 능력을 가진다 (M16, V1.1+ 목표. MVP는 수동 설정 + 이벤트 캘린더 alert)
- **FR22:** 시스템은 모든 청산 이벤트(M22, Kill Switch, DR auto-flatten)를 `orders` 테이블 및 Pre-Trade Ledger에 기록할 수 있다

### 4. Operational Defense (Blind Spots A/B/C — 운영 방어 트랙)

- **FR23:** 시스템은 주문 의도가(시그널가) vs 실제 체결가의 슬리피지를 tick 단위로 실측·기록할 수 있다 (D-T6)
- **FR24:** 시스템은 슬리피지 > 0.3% 시 후속 동일 신호의 S_entry × 0.5 discount를 적용할 수 있다 (D-T6)
- **FR25:** 시스템은 동시 오픈 포지션 수 상한(MVP: 3종목)을 enforce할 수 있다 (D-T8)
- **FR26:** 시스템은 동일 테마·섹터 2종목 이상 동시 보유를 금지할 수 있다 (D-T8)
- **FR27:** 시스템은 뉴스 피드 타임스탬프가 30초 초과 지연 시 해당 신호를 drop할 수 있다 (D-T7)
- **FR28:** 시스템은 NLP 모델 confidence가 임계값 이하인 feature를 neutral(1)로 자동 처리할 수 있다 (D-T7)
- **FR29:** 시스템은 취소·재주문 패턴을 자동 throttle할 수 있다 (§176 준수)

### 5. Risk Control & Kill Switch

- **FR30:** 시스템은 4층 Circuit Breaker(Global·Account·Session·Symbol)를 독립적으로 발동·해제할 수 있다
- **FR31:** 시스템은 일일 손실 ≥ -3% 시 Global CB를 발동하여 당일 신규 진입 전면 차단할 수 있다 (익일 자동 재개)
- **FR32:** 시스템은 MDD ≥ -8% 시 Account CB를 발동하여 주간 중지 + 자본 50% 축소 + 3일 냉각기 + Paper Trading 1주 재통과를 enforce할 수 있다
- **FR33:** 시스템은 연속 3회 손절 시 Session CB로 2시간 쿨다운할 수 있다
- **FR34:** 시스템은 M22 발동 종목에 대해 Symbol CB를 당일 차단할 수 있다
- **FR35:** 시스템은 heartbeat 무응답 4시간 경과 시 서버측 자동 전량 시장가 청산 + 신규 진입 영구 차단을 실행할 수 있다 (수동 해제 필수)
- **FR36:** 시스템은 heartbeat 지연 5분 시점에 모바일 푸시(Telegram/카카오워크)를 발송할 수 있다
- **FR37:** 시스템은 KIS API 장애 시 Secondary 증권사 Adapter로 fallback할 수 있다 (MVP는 추상화 계층, V1.1+ 실구현)

### 6. Compliance & Audit

- **FR38:** 시스템은 모든 주문 의도에 `S_entry 값`, `통과 Gate 목록`, `param_hash`, `policy_version_git_sha`, `시각 hash`를 포함하여 Pre-Trade Authorization Ledger에 append-only로 기록할 수 있다 (§178-2 연계)
- **FR39:** 시스템은 월간 SHA-256 체인 해시를 산출하여 외장 백업(외장 디스크 또는 S3 write-only)에 저장할 수 있다
- **FR40:** 시스템은 분당 주문 수 상한 및 취소율 < 30% 하드 제한을 enforce할 수 있다 (§176)
- **FR41:** 시스템은 본인 계좌 단일 사용만 허용하고 타 계좌 위임을 영구 차단할 수 있다 (§17/§18)
- **FR42:** 시스템은 세후 수익률을 계산할 수 있다 (M_tax: 증권거래세 0.18%, 배당세 15.4%, 금투세 폐지 반영)
- **FR43:** 시스템은 대주주 요건(종목당 지분 1% 또는 시가 10억 원) 근접 시 M_tax 경보를 발송할 수 있다
- **FR44:** 시스템은 자본 ≥ 1,000만 원 또는 일일 주문 > 50건 도달 시 KIS 준법감시인 통지 워크플로우를 자동 트리거할 수 있다
- **FR45:** 시스템은 KIS 준법감시인 통지 이메일 템플릿을 생성하고 회신 수령 기록을 Ledger에 append할 수 있다
- **FR46:** 시스템은 자본 ≥ 1,000만 원 도달 시 가족 1인 OTP 비상정지 권한 공증 위임 체크리스트와 외부 승인권자 서약서 템플릿을 자동 제시할 수 있다

### 7. Monitoring & Alerting

- **FR47:** 사용자는 L2 로거 uptime, 시그널 레이턴시 p99, Kill Switch 상태, KPI 누적을 실시간 대시보드(Grafana)에서 확인할 수 있다
- **FR48:** 시스템은 시그널 레이턴시를 Prometheus histogram으로 측정·기록할 수 있다 (histogram_quantile p99 지원)
- **FR49:** 시스템은 8대 KPI(월 수익률, Deflated Sharpe, MDD, 설거지 회피율, 이벤트 손실 경감률, 레이턴시 p99, override 로그 완전성, F1 PSI)를 실시간 누적 계산하여 대시보드에 표시할 수 있다
- **FR50:** 시스템은 KPI 선언 조건(n≥6개월, 50+ trades, bootstrap CI 하한 > 0) 충족 여부를 실시간 표시할 수 있다
- **FR51:** 시스템은 일별 거래 요약·override 시도 로그·KPI 변화를 주간 리포트로 자동 생성할 수 있다
- **FR52:** 시스템은 52 veto flag missing rate를 월간 감사 리포트로 자동 생성할 수 있다

### 8. Model Lifecycle & Policy Management

- **FR53:** 사용자는 주간 F1 라벨링 워크플로우(GUI 또는 CLI)로 새 override 시도 사례를 데이터셋에 추가할 수 있다
- **FR54:** 시스템은 F1 라벨 PSI를 월간 자동 계산할 수 있으며, PSI > 0.2 시 paper-only 모드로 자동 전환할 수 있다
- **FR55:** 시스템은 walk-forward 백테스트 러너로 공매도 재개(2025-03-31) 전후 레짐 분리 검증을 실행할 수 있다
- **FR56:** 시스템은 θ_entry 및 α/β/γ 가중치 튜닝을 Bayesian + walk-forward 조합으로 실행할 수 있다
- **FR57:** 시스템은 파라미터·정책 변경이 git signed commit + 72h cooling + Paper 재검증을 통과해야만 prod 반영하는 정책을 enforce할 수 있다
- **FR58:** 시스템은 정책 변경 이력(누가·언제·무엇을·왜)을 감사 로그에 기록할 수 있다

---

## Non-Functional Requirements

> **범위:** 본 섹션은 Athena V1.0의 품질 속성을 측정 가능한 형태로 규정한다. **Scalability**와 **Accessibility**는 §17/§18 Scope Lock에 의한 단일 사용자 영구 고정 특성상 명시적으로 제외한다.

### Performance

- **NFR-P1:** 시그널 생성 end-to-end 레이턴시 p99 < **5초** (Prometheus histogram_quantile 측정, 1000+ 신호/월 표본)
- **NFR-P2:** KB-BERT 로컬 추론 < 100ms per inference (MVP 기본축 조건)
- **NFR-P3:** LLM 2단계 호출 타임아웃 2초, 초과 시 1단계 XGBoost 결과로 fallback
- **NFR-P4:** DuckDB Feature Store 쿼리 p95 < 500ms (MVP 유니버스 350종목 × 2년 L2 데이터 기준)
- **NFR-P5:** 장중 블로킹 경로(시그널 생성 → 주문 의도 → 주문 발행)에서 외부 LLM·외부 API 블로킹 호출 금지 (비동기 Queue 경로만 허용)

### Reliability & Availability

- **NFR-R1:** L2 호가창 WebSocket 로거 uptime **≥ 99%** (장중 기준, 월 허용 downtime 약 6시간 30분). 미달 시 paper-only 자동 전환.
- **NFR-R2:** heartbeat 정상 지연 < 60초. **5분** 초과 시 모바일 푸시, **4시간** 초과 시 서버측 자동 전량 시장가 청산 + 신규 진입 영구 차단 (수동 해제 필수)
- **NFR-R3:** MTTR (평균 복구 시간) < 30분 for Operator 수동 개입 가능 장애 (KIS reconnect, 로거 restart 등)
- **NFR-R4:** 물리 이중화: 로거 PC ≠ 트레이딩 PC, UPS + LTE 라우터 fallback 필수
- **NFR-R5:** 정책·파라미터 변경은 72h cooling + Paper 재검증 통과 전 prod 반영 금지 (F5 enforce)

### Security

- **NFR-S1:** 모든 API key·secret은 **OS Keychain 또는 HSM** 수준 저장. `.env`·환경변수 평문·git·코드 하드코딩 영구 금지
- **NFR-S2:** KIS 주문 key와 조회 key는 분리 발급 및 별도 저장
- **NFR-S3:** Pre-Trade Authorization Ledger는 append-only이며, 외부 공격 또는 자기 override로 수정 불가능한 **tamper-evident** 구조여야 한다 (SHA-256 월간 체인 해시 + 외장 write-only 백업)
- **NFR-S4:** 장중 파라미터·정책 저장소는 **읽기전용 마운트**로 물리적 수정 차단
- **NFR-S5:** 로거 PC ↔ 트레이딩 PC 간 내부 통신은 로컬 네트워크 + SSH key 기반
- **NFR-S6:** KIS MTS 계정에서 일일·종목별 최대 주문금액 하드 제한 설정 (이중 안전장치)

### Integration (외부 의존성 품질)

- **NFR-I1:** KIS REST API: token-bucket 20 req/s 기준 throttle. `EGW00201` 에러 수신 시 재시도 최대 3회 + 지수 백오프 → 실패 시 Secondary Adapter fallback (V1.1+ 실구현)
- **NFR-I2:** KIS WebSocket: 41건/세션 상한 준수, 재연결 자동 복구 + 조회 자동 재등록 (python-kis 활용)
- **NFR-I3:** 뉴스 피드: 소스별 `robots.txt` 준수, 자체 rate limit 15 req/min default
- **NFR-I4:** 증권사 Adapter 경계는 KIS/Secondary 간 DTO 동일 interface 보장 (교체 비용 최소화)
- **NFR-I5:** 외부 API 장애 시 해당 신호는 neutral(1) degrade 또는 drop, 시스템 전체 crash 금지 (**graceful degradation**)

### Observability

- **NFR-O1:** 모든 로그는 구조화 JSON 형식. 로컬 파일 저장 + 주간 외장 백업
- **NFR-O2:** Prometheus 필수 메트릭: 시그널 레이턴시 histogram, 모듈별 throughput (signals/min), error rate by code, Kill Switch 상태, 오픈 포지션 수
- **NFR-O3:** Alertmanager 우선순위별 라우팅:
  - **Critical** (Global CB, heartbeat 4h, Ledger 체인 해시 불일치) → 즉시 모바일 푸시 + 이메일
  - **High** (heartbeat 5분 지연, PSI > 0.2, 취소율 > 20%, 로거 uptime < 99%) → 모바일 푸시
  - **Medium** (slippage spike, missing rate 증가, API rate limit 근접) → 대시보드 경고
- **NFR-O4:** asyncio 작업 단위 trace ID 부여 (M13 2단계 병렬 경로 및 비동기 파이프라인 디버깅 지원)

### Auditability & Compliance

- **NFR-A1:** Pre-Trade Ledger는 모든 주문 의도·체결·거부 이벤트를 월간 SHA-256 체인 해시로 보호하며 외장 write-only 백업 (외장 디스크 또는 S3)
- **NFR-A2:** Ledger 보존 기간: **영구** (자본시장법 요구 및 감사 재현용)
- **NFR-A3:** override 시도 로그 완전성 **100%** (F1 자체 감지 + 사후 회고 교차검증으로 증명)
- **NFR-A4:** 월간 compliance 자기 감사 리포트 자동 생성 (취소율, 분당 주문 수, 대주주 근접, missing rate, PSI 포함)
- **NFR-A5:** 모든 정책 변경은 git signed commit에 기록 (누가·언제·무엇을·왜), 감사 로그에 복제 저장

### Maintainability & Evolvability

- **NFR-M1:** 모든 inter-module 통신은 Pydantic 2 DTO 타입화. `timestamp`, `module_version`, `policy_version_git_sha` 필수 필드
- **NFR-M2:** 모듈 개별 semver (예: `M1.v1.2.0`), DTO 및 로그에 embed
- **NFR-M3:** Change Control: MVP 12주 중 모듈 추가·삭제 **최대 1건**. 초과 시 12주 일정 자동 리셋
- **NFR-M4:** 데이터 스키마 모든 테이블에 `user_id` 컬럼 유지 (V1.0 단일 값 고정, commercialization-ready seam)
- **NFR-M5:** 증권사 Adapter는 추상화 계층으로 분리 (KIS/Secondary 교체 시 코어 로직 영향 없음)

### Excluded Categories (명시적 제외)

| 범주 | 제외 이유 |
|---|---|
| **Scalability** | §17/§18 Scope Lock — 단일 사용자 영구 고정. 수평 확장·다중 테넌시 목표 없음. 단 `user_id` 컬럼 seam(NFR-M4)은 유지 |
| **Accessibility** | 단일 사용자 전용, 공공 UI 없음. WCAG/Section 508 적용 대상 아님 |

---

## Appendix A — Brainstorming Traceability

본 Appendix는 2026-04-19 브레인스토밍 세션(101 아이디어 → 30 모듈 → MVP 10)에서 도출되었으나 본문 섹션에 명시되지 않은 요소를 보존한다. 형태학적 완결성과 설계 근거 추적성 확보가 목적이다.

### A.1 Identified Gaps (Future Research Directions)

30개 모듈 형태학 분석 결과 다음 4개 교차 영역이 **gap**으로 식별되었다. V1.1+ 모듈 선정 시 이 gap 해소 여부를 우선 기준으로 삼는다.

| Gap | 설명 | 관련 V1.1+ 모듈 |
|---|---|---|
| **Multi-day × Adversarial** | 며칠 전 세력 포지셔닝 감지 | M4 (L2 Wall Life), M6 (Deception Keyword) |
| **Online Learning × Anti-Ego** | 개인 편향의 시간 변화 학습 | M24 (Bayesian Flag Trust), F1 지속 라벨 |
| **Hard Kill × Macro** | 시장 전체 레벨 hard kill 규칙 | V1.1+ M_volatility_macro (신규 제안) |
| **Tick × Network** | 초단기 cross-stock leadership | M18 (Lead-Follow Timing) |

### A.2 Morphological Axes (Module Classification)

모듈 추가·삭제 시 다음 5축 중 어느 영역에 해당하는지를 Change Request에 명시한다. 동일 축 내 중복 개발 방지 + 형태학적 coverage 감사 가능.

- **A. 결정 단계 (6):** Pre-Entry Filter · Entry Trigger · Sizing · Monitor · Exit · Learning
- **B. 정보 레이어 (7):** Microstructure · NLP · Network · Macro · Distribution · Adversarial · Trader Internal
- **C. 신호 기능 (4):** Go · Gate · Hard Kill · Sizer
- **D. 시간 스케일 (5):** Tick · Minute · Intraday · Multi-day · Regime
- **E. 적응성 (3):** Static · Rolling · Online Learning

**적용 예시:** M1 Linguistic Certainty Scorer = (A: Pre-Entry Filter, B: NLP, C: Gate, D: Intraday, E: Rolling). 동일 A+B+C 조합의 새 모듈 제안 시 M1과의 기능 중복 여부를 Change Review에서 검증.

### A.3 Case 1 재계산 상세 — Innovation Validation Gate 1 보강

설거지 덫 (2025-11 유리기판 A사, -12%) MVP 10 모듈 재계산 상세:

```
S_final = 7.60   × 0.52 × 0.159 × 0.31  × 0.50  × 0.30 × 0.49  ≈ 0.014
          [αN+βV+γO] [M2]  [M3]   [M14]  [M9]   [G_i] [M13]
          덧셈 항목   서사   공시전  바스켓  시간대  기타   2단계
                     소진   드리프트 역전           veto   스코어
```

- θ_entry = 1.0 대비 **99.8% 삭감** (0.014 ≪ 1.0)
- 진입 거부 → 예상 손실 0% (vs 실제 -12%)
- **경고:** 이 수치는 *in-sample* 재계산이다. MVP 설계 근거로는 충분하나 최종 검증이 아니다. **V1.0 Launch 조건은 Innovation § Validation Approach의 Gate 2-4 통과**.

### A.4 Case 2 재계산 개요 — 임상 3상 override (2023-12 바이오 C사, -15%)

MVP 10 모듈 기반 다층 방어:
- **M16 Event Proximity Sizer:** D-3부터 포지션 50% 자동 축소 (V1.1+ 대상, MVP는 수동 캘린더 alert)
- **M22 Hard-Locked Stop:** 뉴스 수신 0초 후 서버측 시장가 강제 청산
- **F1 Bargaining Detector:** "조금만 기다려..." 내부 발화 실시간 감지
- **F5 Parameter Hard-Lock:** 장중 파라미터 수정 물리 차단

예상 결과: -15% → **-3.5% (77% 경감)**. Case 1과 마찬가지로 in-sample.

---

## Document End

**문서 버전 관리:** 본 PRD의 변경은 git signed commit 기준. 주요 변경(FR/NFR 추가·삭제, Scope Lock 변경)은 별도 Change Log 섹션 append.

**다음 단계 (PRD 이후):** UX Design → Architecture → Epics & Stories → Development. 각 후속 문서는 본 PRD의 FR·NFR·Journey에 traceability를 유지해야 한다.
