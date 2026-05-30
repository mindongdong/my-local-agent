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
