---
title: "Product Brief: Athena"
status: "complete"
created: "2026-04-20"
updated: "2026-04-20"
inputs:
  - _bmad-output/brainstorming/brainstorming-session-2026-04-19-2122.md
  - _bmad-output/planning-artifacts/research/domain-korean-short-term-trading-infra-research-2026-04-20.md
project_codename: "Athena"
brief_type: "personal / research"
owner: "Khuk0"
---

# Product Brief: Athena

> **전문가 인지 복제형 단기 매매 자동화 시스템**
> 10년차 트레이더의 암묵지를, 두 번의 참사를 공개 해부한 끝에, 곱셈형 Veto Gate와 Anti-Ego Firewall 이중 아키텍처로 복제한다.

---

## Executive Summary

Athena는 한국 주식시장의 단기 매매에서 **"외부 기만(설거지 덫)"** 과 **"내부 편향(확증·앵커·FOMO)"** 이라는 두 종류의 실패를 동시에 차단하도록 설계된 개인용 자동화 시스템이다. **시스템의 1차 가치는 "조용히 아무것도 하지 않는 능력"** 이다 — 기회 포착이 아니라 **진입 거부**가 북극성이다. 기존 리테일 알고리즘이 "덧셈형 스코어 모델"로 평균을 쫓는 반면, Athena는 **`S_entry = 1[¬HardKill] · (αN + βV + γO) · Π G_i · M_regime · M_time`** 수식의 **곱셈형 Veto Gate** 구조와 **5개 Anti-Ego Firewall 모듈(F1–F5)** 을 병렬 운영하여, 한 개의 거짓말 신호 또는 한 번의 심리적 override 시도만으로도 전체 진입을 차단한다.

브레인스토밍 101개 아이디어를 30개 모듈로 수렴시키고, 그중 MVP 10개 모듈로 본인의 과거 실패 2건(2025-11 유리기판 A사, 2023-12 바이오 C사)을 재계산한 결과 **평균 88%+ 손실 경감이 관찰**되었다 — 단, 이는 **설계 근거이자 가설**이며, 동일 사례가 학습·선정에 쓰인 이상 in-sample 성격을 가진다. V1.0 Launch 전 **out-of-sample 검증 게이트**(Paper Trading 2주 + 본인 미경험 유사 사건 5-10건 재계산)를 반드시 통과해야 한다. 2026년 한국 시장은 공매도 재개(2025-03-31) · 금투세 폐지(2025-01-01) · 기업 밸류업 · NXT 출범이라는 4대 제도가 동시에 본궤도에 오른 구간이며 (단, 이 4요인은 상관·부분 충돌 가능성을 인정), 12주 안에 Paper Trading → V1.0 Launch까지의 실행 청사진이 주차별로 확정되어 있다. Athena는 팔 제품이 아니라, 본인이 **최소 6개월 동안 실거래 자본으로 통계적으로 유의한 KPI를 달성**하기 위한 도구이자 규율이다.

---

## The Problem

**문제는 "시장이 어렵다"가 아니라, "본인이 두 종류의 덫에 반복해서 걸린다"는 것이다.**

- **2025-11 유리기판 A사 (설거지 덫, -12%)** — 외부의 기만에 속았다. 뉴스 서사와 호가창 표면 신호가 진짜처럼 보였지만 실제로는 세력의 출구 유동성이었다. 10년차 본인의 감각으로도 실시간으로 구분 불가능했다.
- **2023-12 바이오 C사 (임상 3상 실패, -15%)** — 외부가 아닌 내부의 덫이었다. "이 회사는 다르다"는 확증편향 + 매입 단가 앵커링 + 손절 직전의 흥정 언어("조금만 더 기다려보자")가 복합 작동하며 hard stop을 override 했다.

이 두 사례는 단순 운이 아니라 **구조적 실패 양식**이다. 기존 기술지표 기반 알고리즘은 외부 덫은 그럭저럭 걸러도 내부 덫은 전혀 손대지 못하며, 반대로 심리 일지 중심 접근은 외부 기만에 속수무책이다. **두 덫을 동시에 방어하는 시스템은 현재 시장에 존재하지 않는다** — No-code 플랫폼(Time Percent 등)은 기술지표 조합 수준에 머물고, 증권사 제공 알고리즘 주문은 집행 전용이다.

그리고 단기 매매의 손실은 월 수익률 30% 구간에서 **단 1건의 override가 3개월치 알파를 날린다.** 문제는 빈도가 아니라 비대칭 파괴력이다.

---

## The Solution

**Athena는 "감각"을 52개의 veto flag로 원자화하고, 이를 곱셈 구조로 결합하여 한 개라도 위반 시 전체 진입을 차단하는 알고리즘이다.** 시스템은 두 개의 파이프라인을 병렬로 운영한다.

**파이프라인 1 — 독사과 필터 (외부 기만 방어).** 뉴스 확실성(M1), 서사 나이(M2), 뉴스 전 표류(M3), 호가창 벽 수명(M4), 체결 크기 분포(M5), 시간대 체제(M9), 바스켓 일관성(M14) 등 25개 core 모듈이 `S_entry` 수식의 각 항을 구성한다. 평균을 끌어올리는 신호가 하나라도 거짓이면 곱셈 구조가 전체 점수를 0에 가깝게 수렴시킨다.

**파이프라인 2 — Anti-Ego Firewall (내부 편향 방어).** F1 흥정 언어 감지 · F2 자기 FOMO 센서 · F3 생리적 override · F4 3인칭 재결정 프롬프트 · F5 파라미터 하드락 — 5개 모듈이 **트레이더 본인**을 감시한다. F5는 장중 파라미터 수정을 물리적으로 차단하며, F1은 본인 과거 트레이딩 일지 200건 수작업 라벨로 학습한다.

**진입 조건:** `S_entry > θ_entry` **AND** `Anti-Ego Firewall = 1`. 두 조건 모두 충족하지 못하면 시스템은 **조용히 아무것도 하지 않는다** — 이 한 줄이 Athena의 북극성이며, 12주 동안 모듈을 추가하려는 모든 유혹을 기각하는 기준이다.

**살아있는 라벨 자산 (Living Label Asset) 루프.** F1은 **최근 200건 + 과거 10년 일지 회고 50건 = 총 250건** 수작업 라벨로 출발하지만, 실거래 이후 발생하는 모든 override 시도·흥정 언어·미체결 근접 사건이 다시 F1 학습셋으로 흡수된다. **운영 시간 = 모델 강건성 복리** — 외부자가 자본·인력으로 단축 불가능한 유일한 비대칭이다.

**MVP 10 모듈** — {M1, M2, M3, M9, M13, M14, M19, M22, F1, F5} — 만으로 과거 2건을 재계산한 **설계 가설**:
- **Case 1 (설거지 덫):** S_final ≈ 0.014 → 진입 임계 대비 99.8% 삭감 → **예상 100% 회피** (실제는 in-sample, out-of-sample 검증 필수)
- **Case 2 (임상 3상):** M16 포지션 50% 축소 + M22 강제 청산 + F1 override 차단 → **예상 77% 경감** (동일 조건)

---

## What Makes This Different

**진정한 해자는 도구가 아니다. 설계 사고와, 시간만이 만들 수 있는 자산이다.**

1. **곱셈형 Veto Gate 아키텍처** — 업계 표준인 덧셈형 스코어 모델은 신호 하나의 거짓이 평균에 흡수되어 오검을 유발한다. Athena의 `Π G_i` 곱셈 구조는 한 개의 veto만으로도 전체 진입을 차단하여, 비대칭 파괴력을 가진 단일 실패를 방어한다. 이 수식은 본인의 두 실패 사례를 귀납적으로 분해하여 도출되었고, 타 도메인(전염병학 SIR, Watts cascade, Omori law, Transfer entropy)의 수학을 직접 이식한 결과물이다.

2. **Anti-Ego Firewall — 본인을 감시하는 모듈군** — 경쟁 제품 누구도 "트레이더 본인의 심리적 override"를 시스템의 1급 위협으로 모델링하지 않는다. F1–F5는 본인의 라벨 데이터(최소 200건) 없이는 작동하지 않으므로, 외주·복제가 구조적으로 불가능한 해자이다.

3. **자체 L2 호가창 백필 데이터 — "Time-Travel Rights"** — KIS Developers는 Tick 히스토리를 제공하지 않는다. Week 1 Day 1부터 자체 WebSocket 로거를 24/7 무중단 가동하여 2년간 축적하는 것은 단순 fine-tune 원료가 아니라, **공매도 재개·밸류업·NXT 전환기 전체를 한 관찰자 시점에서 기록한 유일 데이터셋**이다. 향후 어떤 후속 질문(레짐 전이, 세력 행동 변화, NXT 유동성 이주)에도 과거로 돌아가 답할 수 있는 권리 — 이 옵션가치는 MVP KPI와 동급의 전략 자산이며, 시간만이 만들 수 있다.

4. **런칭 타이밍 (조건부)** — 공매도 재개(2025-03-31) + 금투세 폐지(2025-01-01) + 밸류업 + NXT 출범(2025-03)이 본궤도에 오른 구간이다. 변동성 ↑ · 세후 수익 ↑ · 테마 순환 가속 · 개인 알고 유동성 폭증의 4대 조건이 호의적으로 작동. **단, 이 4요인은 독립적 호재가 아닐 수 있다** — 공매도 재개는 Athena의 롱 전략과 부분 충돌, 금투세 폐지는 세력 설거지 표적 확대라는 역효과 잠재. 타이밍은 강한 순풍이지만 "역사적 적기"는 아니다.

**경쟁 비교**

| 축 | Time Percent 등 No-code | 증권사 알고 주문 | Athena |
|---|---|---|---|
| 대상 | 리테일 일반 | 기관·집행 전용 | 본인 전용 |
| 전략 깊이 | 기술지표 조합 | 집행 로직만 | Veto Gate × Anti-Ego |
| 호가창 활용 | N/A | 집행 최적화 | M4/M5/자체 백필 |
| 심리 방어 | 없음 | 없음 | F1–F5 |

---

## Who This Serves

**Primary User — Khuk0 본인.** 10년 한국 주식 단기 매매 경력, 수학적 추상과 구체적 시장 현실 사이를 빠르게 왕복하는 역량, 자신의 실패를 객관화하는 메타인지력을 보유. 본인이 도메인 전문가이자 유일한 운영자이자 유일한 라벨 제공자이다.

**Success for the User:** 장중 override 시도 0회를 유지하면서, 3개월 연속으로 월 수익률 KPI를 실거래 자본으로 달성한다. 그 과정에서 본인의 심리적 규율이 시스템의 외부화를 통해 체화된다.

**Non-User:** 이 제품은 다른 사람을 위해 만들지 않는다. No-code UI도 없고, 상용화 검토도 하지 않는다. 브리프가 개인용으로 작성된 이유이기도 하다.

---

## Success Criteria

**6개월 1차 목표 — 8대 KPI** (전부 세후·기하평균 기준, 레버리지 0)

| 범주 | 지표 | 목표 | 측정창·표본 |
|---|---|---|---|
| **수익성** | 월 수익률 (세후, 기하평균 연간화) | > 30% | n≥6개월, 50+ 트레이드 |
| **수익성** | Deflated Sharpe Ratio | > 1.5 | Bailey·Lopez de Prado 공식 |
| **수익성** | Max Drawdown | < 10% | 일별 NAV 기준 |
| **방어력** | 설거지 패턴 회피율 | > 90% | 월 단위 |
| **방어력** | 이벤트 손실 경감률 | > 75% | 이벤트당 |
| **시스템** | 시그널 레이턴시 p99 | < 5초 | Prometheus 측정 |
| **감사** | override 시도 로그 완전성 | **100%** | 시도 0회가 아닌, 시도 발생 시 전수 기록 |
| **드리프트** | 월간 F1 라벨 재학습 주기 | 1회/월 + PSI<0.2 | drift 초과 시 paper-only 전환 |

**개인 성공 정의:** **최소 6개월, 50+ 트레이드, bootstrap CI 하한 > 0** 조건 하에서 위 KPI를 실거래 자본으로 달성. n=3 월관측만으로는 '운과 실력 구별 불가'이므로 선언하지 않는다.

---

## Capital & Kill Switch (Launch Pre-Gate)

실거래 자본이 걸린 시스템에서 **"언제 플러그를 뽑을지"가 없으면 KPI는 사후 측정에 불과**하다. 다음 4층 Circuit Breaker를 V1.0 Launch 이전 Paper Trading 기간 내 최소 1회 실발동·회복 훈련을 거쳐야 한다.

| 레벨 | 트리거 | 대응 | 재개 조건 |
|---|---|---|---|
| **Global** | 일일 손실 ≥ -3% | 당일 거래 중지 | 익일 자동 재개 |
| **Account** | MDD ≥ -8% | 주간 중지 + 자본 50% 축소 | 3일 냉각기 + Paper Trading 1주 재통과 |
| **Session** | 연속 3회 손절 | 2시간 쿨다운 | 자동 |
| **Symbol** | M22 Hard-Locked Stop | 해당 종목 당일 차단 | 자동 |

**Flag down:** MDD ≥ -10% 또는 override 로그 단절 시 시스템 off. 재가동은 **3일 냉각기 + Paper Trading 1주 재통과**가 필수 (외부 승인권자 위임은 자본 확대 단계에서 재검토).
**자본 규모:** **초기 10-30만 원 단위로 시작** (KPI 규율·Kill Switch 훈련·Living Label Asset 루프 기동이 목적). 6개월 KPI 달성 시 단계적 확대. 자본 ≥ 1,000만 원 도달 시 외부 승인권자 위임·증권사 서면 통지 등 상위 안전장치 자동 트리거.

---

## Disaster Recovery & On-Call (Bus Factor = 1 완화)

1인 개발·운영 구조에서 본인 부재는 오픈 포지션 방치로 직결된다. 다음 안전장치는 V1.0 Launch 전 필수.

- **Heartbeat 4시간 무응답 → 서버측 전량 시장가 청산 + 신규 진입 영구 차단**
- **KIS API 장애 시 secondary 증권사 Adapter(eBEST 또는 대신 CREON) fallback** — 주문 인터페이스 추상화 계층을 Week 7-8에 설계
- **로거 중단 5분 내 모바일 푸시 알림** (카카오워크/Telegram bot) + on-call escalation 정책
- **물리 이중화:** UPS + LTE 라우터 + 로거 PC ≠ 트레이딩 PC (인터넷 차단·화이트리스트)
- **비상정지 권한 위임:** 초기 10-30만 원 규모에서는 자기 속박(3일 냉각기+Paper 재통과)으로 갈음. 자본 ≥ 1,000만 원 도달 시 가족 1인에게 MTS OTP 비상정지 권한 공증 위임 자동 트리거

---

## Compliance & Audit

**자본시장법 §176 / §178 / §178-2 가드레일** (§178-2는 과실도 처벌)

| 위반 유형 | 정량 가드레일 |
|---|---|
| 허수성 호가 | 동일호가 반복 상한, 취소율 < 30% |
| 연속매매 | 분당 최대 주문수 상한 |
| 가장·통정매매 | 본인 계좌 단일 사용, 타 계좌 위임 영구 금지 |

- **KIS 준법감시인 사전 서면 통지 (조건부):** 초기 10-30만 원 규모에서는 시장 영향력 미미로 불필요. **자본 ≥ 1,000만 원 도달 또는 일일 주문건수 > 50건 도달 시 자동 트리거** — 운용계획·예상 주문빈도·취소율·본인 자본 전용을 이메일 고지하고 회신 보관
- **Pre-Trade Authorization Ledger (append-only):** 모든 주문에 `S_entry 값`, `통과 Gate 목록`, `param_hash`, `policy_version_git_sha`, `시각 hash` 필수 기록. 월간 SHA-256 체인 해시로 외부 백업(외장 디스크 또는 S3 write-only)
- **API Key 보안:** OS Keychain/HSM 수준 저장. `.env` 금지. 주문 키와 조회 키 분리. 증권사 MTS에서 일일·종목별 최대 주문금액 하드 제한
- **세무 준수:** 수익률은 **세후** 재정의(거래세 0.18% · 배당세 15.4% 반영). 대주주 요건(종목당 1% 또는 10억 원) 근접 시 M_tax 경보
- **공개 금지:** Athena 코드·파라미터·시그널 대외 공개 영구 금지 (투자자문업 §17/§18 위반 소지)

---

## Scope (MVP Boundary)

**In — MVP 10 모듈 {M1, M2, M3, M9, M13, M14, M19, M22, F1, F5}**
- 외부 기만 방어 7개: M1 뉴스 확실성 · M2 서사 나이 · M3 뉴스 전 표류 · M9 시간대 체제 · M13 2단계 하이브리드 스코어러 · M14 바스켓 일관성 Gate · M19 손실 가속 트리거 · M22 Hard-Locked 손절
- 내부 편향 방어 2개: F1 흥정 언어 감지 · F5 파라미터 하드락

**Explicit Non-Goals (의도적 배제 — scope creep 차단)**
- ❌ 스캘핑/HFT (<1초 레이턴시 요구) — 본 시스템은 5초 예산
- ❌ 파생상품·해외주식 — KRX 주시장 only
- ❌ NXT 다시장 연동 — V1.1+ 유보
- ❌ No-code UI · 상용화 검토 · 타 사용자 확장 — 개인용 고정
- ❌ 실시간 LLM blocking 호출 — LLM은 비동기 2단계만 허용 (KB-BERT 로컬 추론이 기본축)

**Change Control:** MVP 12주 기간 중 모듈 추가·삭제는 **문서화된 변경요청(CR) 거쳐 최대 1건만 허용**. 초과 시 12주 일정 자동 리셋. 주말 파라미터 튜닝은 git commit + 72h cooling + Paper Trading 재검증 없이 prod 반영 금지.

---

## Technical Approach (개요)

**Tier 1 MVP 스택 (Week 1-8):** Python 3.11+ · asyncio + uvloop(2.6x) · Polars(10x pandas) · python-kis · pykrx · KB-BERT + finance_sentiment_corpus · NetworkX · scipy · scikit-learn · SQLite/DuckDB · Vault/.env

**Tier 2 (Week 9-12):** LOBFrame 참조 · Numba 핫패스 · HyperCLOVA X / Solar Pro 2 API (비동기만) · Prometheus+Grafana

**Tier 3 (V1.1+ ~ V2.x):** PyTorch Geometric GNN · Transfer Entropy 라이브러리 · TLOB/LiT fine-tune (자체 L2 데이터) · Rust+PyO3 핫패스 재작성

**12주 로드맵**
- **W1-2** 데이터 인프라 — DART 크롤러, 뉴스 피드, pykrx, **★호가창 L2 WebSocket 로거 24/7 무중단 즉시 가동 (Day 1 최우선)**
- **W3-4** NLP Feature — M1–M3 + F1 라벨 수작업 50건
- **W5-6** Scoring Brain — M9, M13, M14, F5 Paper-Trade Ready
- **W7-8** Monitor + Exit — M19, M22 + F1 라벨 200건 완료 + Full MVP 10
- **W9-10** Backtest + Walk-forward — **공매도 재개(2025-03-31) 전후 레짐 분리 검증 필수**
- **W11-12** Paper Trading 2주 → V1.0 Launch 승인

---

## Vision

**6–12개월:** V1.1+ — M7 Regime Classifier, M11+M12 밸류체인 Transfer Entropy, M16 Event Proximity Sizer, M23 Multi-Trigger Exit, M25 Explainable Report 순차 추가. V1.1+ 진입의 전제는 Week 1부터 축적한 **호가창 L2 2년 데이터**로 M4/M5 본격 가동.

**12–24개월:** V2.x 연구 테마 — Red Team GAN Auto-Adversary(#82), Stackelberg Reverse Engineering(#80), Beauty Contest Tracker(#85), Integrated Information Φ. **Meta-gate:** V2.x는 V1.0이 n≥6 관측치로 Deflated Sharpe > 1.5 통과한 이후에만 해금. 연구 테마는 규율의 도피구가 되지 않는다.

**궁극 상태 — Cognitive Prosthesis.** 본인의 심리적 규율이 시스템을 통해 완전히 외부화되어, Athena가 본인보다 더 본인을 잘 아는 상태. Anti-Ego Firewall은 단순 기능이 아니라 **본인의 메타인지를 코드로 외부화하여 인지 부하를 줄이는 장치**이다. 북극성은 언제나 동일하다 — **"조용히 아무것도 하지 않을 줄 아는 시스템."**

---

## Critical Success Factors (7)

1. **Week 1 Day 1 호가창 로거 가동** — 지연은 V1.1+ 전체를 지연시킨다. 다른 모든 의사결정보다 선행.
2. **F1 라벨 250건 본인 수작업 완료** — 외주 불가. **최근 200건 + 과거 10년 일지 회고 라벨링 50건 = 총 250건**. 회고 라벨링은 W3-4에 병행, 시간 투자 없이 라벨 다양성 수 배 확보 (유일한 데이터 레버리지).
3. **F5 tamper-evident 설계** — 하드락 + git revert 방어(append-only 해시체인 로그) + 장중 리포지토리 읽기전용 마운트 + 파라미터 변경 24h cooldown. "override 시도 0회"가 아니라 **"override 시도 로그 완전성 100%"** 를 측정한다.
4. **Kill Switch 4층 실발동 훈련** — Paper Trading 기간(W11-12) 내 Global/Account/Session/Symbol 각 1회 이상 발동·회복 시뮬레이션 통과가 V1.0 Launch 승인 조건.
5. **공매도 재개 전후 레짐 분리 검증** — 2025-03-31 기점 overfit 회피의 유일한 장치. Walk-forward 백테스트에서 명시적 분리 구간 포함.
6. **법률 체크리스트 사전 통과** — KIS 준법감시인 서면 통지 회신 보관, §176/§178/§178-2 가드레일 수식 내장, Pre-Trade Ledger 스키마 확정.
7. **MVP scope 엄수 + out-of-sample 게이트** — 30개 모듈의 유혹을 Change Control로 차단. 88% 경감은 "가설"이며 V1.0 전 미경험 사건 5-10건 재계산으로 검증.

---

## Risks & Mitigation (Top 6)

| 리스크 | 심각도 | 완화 | 조기경보 지표 |
|---|---|---|---|
| 호가창 Tick 히스토리 부재 | **Critical** | Week 1 Day 1 자체 L2 로거 + DuckDB 스키마 확정 | 로거 uptime < 99% → paper-only |
| 오픈 포지션 중 서버/네트워크 다운 | **Critical** | 서버측 OCO stop + heartbeat 4h → 자동 flatten | heartbeat 지연 > 5분 |
| 자본시장법 §176/§178/§178-2 | High | 분당 주문 상한 + 취소율 < 30% + Pre-Trade Ledger + KIS 준법감시인 사전 통지 | 취소율 > 20% → 자동 throttle |
| KIS API 장애·rate limit | High | Secondary 증권사 Adapter + OS레벨 token-bucket + 수동 MTS 청산 플레이북 | EGW00201 에러 급증 |
| 곱셈형 Veto의 False Negative 폭발 | Medium | 센서 결측 → 해당 flag neutral(1)로 degrade + 월간 missing rate 감사 | 52개 flag 중 missing > 3개 |
| F1 라벨 드리프트 (공매도 재개 후 본인 언어 변화) | Medium | 월 20건 추가 라벨 + PSI/KS 지표 모니터 + 분기 재학습 게이트 | PSI > 0.2 → paper-only 전환 |

---

*이 브리프는 Athena의 PRD 작성을 위한 선행 문서이다. 상세 모듈 스펙·수식 파생·로드맵 세부는 brainstorming-session 및 domain-research 원문을 참조하며, 이후 PRD에서 모듈 단위 요구사항으로 전개한다.*
