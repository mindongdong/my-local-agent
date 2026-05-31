---
status: Accepted
date: 2026-05-30
deciders: [dongmin]
supersedes: ""
superseded-by: ""
---

# 0007: W0.5 검증 게이트 결과 — Go (헤드리스 전제)

## Context

[[W0.5]] 검증 게이트의 목적은 코드 작성([[W1]]~)에 들어가기 전에 **qwen3.5:9b([[Manager]]) + [[OMC]] + [[cmux]] 조합이 Mac Mini M4 16GB에서 실제로 돌아가는지** 결판내는 것이다 ([[ADR 0005]]). [work-plan.md](../../work-plan.md) §8은 Go 기준 3개를 정의했다:

1. 메모리 peak < 14GB
2. cmux 통신(round-trip) ≥ 99% 성공
3. `ulw` 2 동시 통과

2026-05-30 환경 셋업 후 위 3개 + 보너스(JSON 신뢰성)를 실측했다. 측정 데이터·방법·함정은 [[w0.5-validation]]에 누적되어 있다.

## Decision

**Go — [[W1]] E2E 스파이크로 진입한다. qwen3.5:9b + OMC + cmux 스택을 유지한다.**

단 다음을 **운영 전제 조건**으로 둔다:

1. **헤드리스 운영** — Mac Mini에서 Chrome/VSCode 등 데스크톱 GUI 앱을 띄우지 않는다. 메모리 Go(①)는 이 전제에서만 충족된다.
2. **Manager 컨텍스트 캡** — 256K는 명목 스펙. full로 채우면 KV 캐시가 16GB를 초과하므로 운영 컨텍스트를 보수적으로 제한한다.
3. **JSON 강제 = 프롬프트 구조 명시 + 코드측 검증** — ollama `format` 스키마는 이 setup에서 강제되지 않음. format에 의존하지 않는다.
4. **모델 라우팅(`eco:`→haiku) 검증은 [[W1]]로 연기** — Go 기준이 아니며 OMC 내부 동작이라, W1 실사용 중 OMC `/trace`/로그로 확인한다.

No-go fallback(Gemma 3n E4B 다운그레이드, headless `claude -p` 회귀, 동시성 1 축소)은 **발동하지 않는다**.

## Consequences

**측정 요약** (상세: [[w0.5-validation]])

| Go 기준 | 결과 | 판정 |
|---|---|---|
| ① 메모리 peak < 14GB | 모델 로드 RAM 8.5GB@4k. 헤드리스 타겟 ~14GB, 현 데스크톱(Chrome/VSCode)은 ~14-15GB | ⚠️ 헤드리스 전제 Go |
| ② cmux round-trip ≥ 99% | 300/300 (100%), 평균 0.277s/최대 0.329s | ✅ |
| ③ `ulw` 2 동시 | 워커 ~213MB/개, 서버측 실행, +2 시 free% 평탄 | ✅ |
| (보너스) JSON 신뢰성 | 구조 14/14(100%), 의미 13/14(93%), temp=0 결정성 | ✅ |
| 모델 라우팅 | 미측정 → W1 연기 | ⏸ |

**핵심 운영 제약** (W1 이후 설계에 반영)

- 헤드리스 필수. 데스크톱 앱 가동 시 스왑 → latency 급등.
- `ulw`/동시 워커는 메모리 제약이 아님(서버측). 동시 task 1~2는 가드레일/추적성 관점에서 유지.
- Manager JSON 파이프라인은 프롬프트 구조 명시 + 검증 + 파싱 실패 시 재시도로 구현.

**잔여 리스크**

- 메모리 헤드룸이 얇다(헤드리스에서도 ~14GB). FastAPI/Discord/SQLite 추가 시 재측정 필요.
- 모델 라우팅 미검증 — W1에서 결판. `eco:` 라우팅이 의도대로 동작하지 않으면 비용 추정/가드레일에 영향.

**되돌리기 난이도**: 낮음. fallback 경로(Gemma, headless)가 [[ADR 0004]]·[[ADR 0002]]에 준비되어 있다.

## Alternatives considered

**(A) No-go — Gemma 3n E4B 다운그레이드** ([work-plan.md](../../work-plan.md) §8 fallback). 메모리 문제가 임계였다면 선택했을 경로. 측정 결과 메모리는 헤드리스 전제로 충족되고 qwen3.5:9b의 한국어/JSON 품질(93%)이 양호하여 불필요. 미채택.

**(B) No-go — headless `claude -p` 회귀** ([[ADR 0002]] 대안 B). cmux 통신이 불안정했다면 선택. round-trip 300/300으로 안정 확인되어 불필요. 미채택.

**(C) 동시성 1로 축소 + Gemma + headless** (plan §8 "둘 다 문제"). 메모리·통신 모두 실패 시의 최후 경로. 해당 없음. 미채택.

**(D) 모델 라우팅까지 측정 후 Go 판정**. 완전성은 높으나 라우팅은 Go 기준이 아니고 OMC 내부라 W1 실사용에서 더 자연스럽게 검증된다. 게이트를 불필요하게 지연시키지 않기 위해 연기. ([[w0.5-validation]] 미측정 항목)

## Addendum — Mac Mini 재검증 (2026-05-30)

원래 판정의 측정치는 **개발용 다른 Mac**에서 나왔고, 메모리는 머신 특정값이라 [[w1-handoff]] §1이 타겟 **Mac Mini(M4 16GB)** 재검증을 W1 전 필수로 요구했다. 헤드리스(VSCode·Discord·KakaoTalk·iTerm2·Preview 종료)에서 3 Go 기준을 재현한 결과:

| Go 기준 | Mac Mini 16GB 헤드리스 실측 | 판정 |
|---|---|---|
| ① 메모리 peak < 14GB | `top` used **15G** (모델+3워커 동일), 단 **swap 무증가(113.5M 고정)·pressure normal** | ⚠️ 조건부 PASS |
| ② cmux round-trip ≥ 99% | **300/300 (100%)**, first-try 300/300, ~0.25s/trial | ✅ |
| ③ `ulw` 2 동시 | 워커 2개(+0.75GB) 추가에도 swap 고정, compressor 흡수 | ✅ |

**메모리 메트릭 정정**: Apple Silicon **통합메모리**에서 GPU 상주 모델 가중치(~7.4GB)가 **wired**로 잡혀 `top "used"`가 모델 로드만으로 ~15G가 된다. 따라서 16GB 머신에서 `top used < 14GB`는 모델을 띄우는 한 충족 불가 — **올바른 게이지는 swap 증가량 + pressure level**이며 둘 다 건강(모델+3워커에서도 무-스왑). 기준 ①의 **의도(스왑 스래싱 없이 동작)는 충족** → 조건부 PASS. 원 Decision(Go, 헤드리스 전제) **유지**.

**운영 전제 보강**:
- (기존 1~4 유지) +
- **5. Manager 모델 keep_alive 단명(버스트 로드)** — 메모리 병목은 GUI가 아니라 **모델 7.4GB + macOS ~8GB**다(헤드리스로도 ~15G). GUI 종료만으론 14GB 밑으로 안 내려간다. **진짜 레버는 keep_alive**: Manager 추론(triage/요약)에만 짧게 로드하고 유휴 시 언로드해 **7.4GB를 회수**, 평시는 8.5G + 워커로 헤드룸 확보. (모델 자동 언로드 → 즉시 회수 실측 확인)

**cmux 0.64.10 API 정정** (Mac Mini에서 드러남): `send`/`read-screen`은 **`--surface`에 `--window` 컨텍스트 필수**, 기본 `new-workspace`는 비-터미널이라 **`--layout` 터미널 surface 명시** 필요. W1 cmux 래퍼에 반영. (상세: [[w0.5-validation]] Mac Mini 재측정 §②)

**잔여 리스크 갱신**: 헤드룸 얇음(unused ~170M). W1에서 Discord bot·FastAPI·SQLite·실제 요약 컨텍스트 추가 시 **운영 메모리 재측정** 필요. 초과 시 fallback = keep_alive 단축 / 동시성 1 / Gemma 다운그레이드([[ADR 0004]]).

## Addendum — 모델 라우팅(`eco:`→haiku) 검증 (2026-05-31, W1)

본 ADR 본문(Decision 4, Consequences 표)이 [[W1]]로 연기했던 마지막 항목. W1 E2E 완료 후 OMC 4.14.4 소스·문서 evidence로 확인했다 (라이브 `/trace`는 W2 OMC 본격 통합 시).

**결과: wiki의 "`eco:`→haiku 결정적 라우팅" 가정은 부정확 — 정정함.**

| 가정 | evidence | 판정 |
|---|---|---|
| `eco:`가 OMC 매직 키워드 | README/quickref/slides에 `eco` = "token-efficient/budget-friendly parallel" 실재 | ✅ 맞음 |
| `eco:` → **haiku** 결정적 매핑 | 코드·skill 어디에도 키워드→모델 테이블 없음 | ❌ 부정확 |

- **실제 메커니즘**: OMC 모델 라우팅은 **LLM(에이전트)이 작업 복잡도를 보고 `Task(subagent_type="executor", model="haiku\|sonnet\|opus")`로 명시 선택**한다 (`skills/ultrawork/SKILL.md` L68-70: simple→haiku, standard→sonnet, complex→opus; `sciomc`/`deep-dive`도 동일 패턴). 결정적 테이블이 아니라 **프롬프트 지시 기반 판단**.
- **`eco`의 정체**: 별도 skill이 아닌 **모드 수식 키워드**(token-efficient/budget-friendly parallel). 다른 모드와 조합("autopilot eco:", "ralph eco:"), 모델 선택을 저렴한 쪽으로 편향시키나 **haiku를 강제하지 않는다**.
- **W0.5 함정과 동형**: 가정한 메커니즘(자동 라우팅 테이블)이 실제로는 다르게(LLM 지시 기반) 동작 — ollama `format` 강제 함정과 같은 교훈. **메커니즘 가정을 코드로 먼저 검증할 것.**

**함의 (비용 추정/가드레일)**: 모델 선택이 비결정적(LLM 판단)이므로 정적 "eco=haiku" 가정으로 비용을 사전 추정하면 틀린다. **실제 spawn된 model을 사후 관측**(`/trace` 파싱 또는 PostToolUse hook)해야 한다 ([[ADR 0003]] Consequences, [[w1-handoff]] §8). 본 ADR Consequences 표의 "모델 라우팅 ⏸"은 이 Addendum으로 **확인 완료**로 갱신.

**정정 페이지**: [[w0.5-validation]]/[[system-design]] 모델 라우팅 섹션 + 라우팅 표, [[glossary]] `eco:` 정의.
