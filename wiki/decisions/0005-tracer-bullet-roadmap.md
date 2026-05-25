---
status: Accepted
date: 2026-05-25
deciders: [dongmin]
supersedes: ""
superseded-by: ""
---

# 0005: Layer-by-layer 대신 Tracer-bullet 로드맵 + W0.5 검증 게이트 채택

## Context

원본 spec(`wiki/raw/local-agent-server-spec.md`) section 9는 **Layer-by-layer 로드맵**을 제안한다. Manager 완성 → Worker 완성 → PR 완성 → wiki distill → 운영 안정화 순서로 레이어를 쌓아 올리는 방식이다.

이 구조에는 두 가지 리스크가 내재되어 있다.

첫째, **통합 위험 후행 문제**. 각 레이어를 독립 완성한 뒤 마지막에 통합하면, 컴포넌트 간 인터페이스 불일치와 런타임 충돌이 후반부에서야 드러난다. 재작업 비용이 매몰 비용이 큰 시점에 발생한다.

둘째, **환경 검증 미확인 문제**. [[OMC]] + [[cmux]] 조합이 Mac Mini 환경 (16GB RAM, Apple Silicon) 에서 실제로 안정적으로 동작하는지 아직 측정된 바 없다. [[W1]] 진입 전에 이 사실이 파악되지 않으면, 환경 가정이 틀렸을 때의 fallback 결정이 많은 작업이 완료된 후에야 내려지게 된다.

이 두 리스크를 부트스트랩 직후에 처리하기 위해 로드맵 패러다임 전환이 필요하다.

## Decision

**[[tracer-bullet 로드맵]]을 채택**한다. Layer 별 완성 대신, 시스템을 관통하는 가는 E2E 라인 하나를 먼저 구현하고, 이후 라인 위에 두께를 더해 나간다.

**[[W1]] 스파이크**: Discord 메시지 수신 → 하드코딩 영문 프롬프트 → [[cmux]] 내 [[OMC]] 호출 → diff 한국어 출력 → Discord 포스팅. 이 6컴포넌트 라인이 끝에서 끝까지 흐르면 W1 목표 달성. W2~W7에서 하드코딩을 실제 로직으로 점진 대체한다.

**[[W0.5]] 검증 게이트를 추가**한다. [[W0]] 부트스트랩 직후, [[W1]] 진입 전 1~2일 동안 아래 항목을 실측한다.

| 측정 항목 | 목표 |
|---|---|
| 메모리 peak (Manager LLM + OMC 동시 실행) | < 14 GB |
| `autopilot:` 단발 호출 완료 여부 | 성공 |
| [[cmux]] 통신 round-trip 레이턴시 | < 5초 |
| `ulw` 동시성 안정성 (2 worker 병렬) | 크래시 없음 |
| 모델 라우팅 (haiku/sonnet/opus 전환) | 정상 분기 |

측정 결과에 따라 **Go / No-go**를 결정한다. No-go 시 fallback:

- 메모리만 문제 → [[Gemma 3n E4B]]로 다운그레이드 (ADR 0004의 qwen3.5:9b 선택 일부 reverse)
- cmux 통신 문제 → `claude -p` headless 회귀 ([[ADR 0002]] 결정 일부 reverse)

**Phase 구조**:

| Phase | 내용 |
|---|---|
| [[W0]] | 부트스트랩 — dev-wiki + ADR + system-design + 환경 셋업 |
| [[W0.5]] | 검증 게이트 — Go/No-go |
| [[W1]] | E2E 스파이크 — 가는 line 1개 |
| [[W2]] | Manager 두뇌화 — 이슈 fetch + 한국어 의도 파싱 |
| [[W3]] | [[interrupt #1]] + checkpointer |
| [[W4]] | 승인 게이트 [[interrupt #2]], [[interrupt #3]] |
| [[W5]] | PR + [[가드레일]] |
| [[W6]] | wiki distill + 대시보드 |
| [[W7]] | 운영 안정화 |

## Consequences

**긍정적 영향**:

- 통합 위험이 [[W1]]에서 조기 발견된다. 컴포넌트 인터페이스 오류를 후반부가 아닌 초기에 수정할 수 있다.
- 매 phase 끝에 "작동하는 무언가"가 존재한다. 중간에 작업이 중단되더라도 실행 가능한 결과물이 남는다.
- [[W0.5]] 게이트로 환경 가정 검증을 부트스트랩 직후에 진행한다. fallback 결정이 매몰 비용 없는 시점에 내려진다.

**부정적 영향**:

- **W1 범위 팽창 risk**. 현재 정의된 W1의 "가는 line" 자체가 이미 6개 컴포넌트(Discord bot + cmux 헬퍼 + send/capture 래퍼 + diff 캡처 + [[qwen3.5:9b]] 한국어 요약 + Discord 포스팅)를 포함한다. tracer-bullet 정신 — 가능한 한 가늘게 — 을 위반할 수 있다. **W1 진입 시 재절제(scope reduction)가 반드시 필요하다.**
- **refactor 비용 누적**. W1의 하드코딩이 W2~W5에서 점진 대체되므로, 초기 코드의 일부는 버려진다. Layer-by-layer 대비 중복 작업이 발생한다.
- **W0.5 측정 항목 재정의 필요**. 위 측정 항목들은 현재 cmux `send-keys` / `capture-pane` 메커니즘 가정 위에 정의되어 있다. W0.5 착수 전에 실제 cmux API와 맞추어 항목을 재검토해야 한다.

**되돌리기 난이도**: 중간. W1 구현 전까지는 롤백 비용이 낮다. W2 이후에는 tracer-bullet 구조에 의존하는 코드가 쌓여 Layer-by-layer로 전환하는 비용이 커진다.

## Alternatives considered

**(A) 원본 spec Layer-by-layer 유지**

각 레이어를 완성한 뒤 통합하는 방식. 단계별 완성도가 명확하고, 레이어 간 독립성이 높다. 그러나 통합 위험이 후행하고, 작동하는 결과물이 나오기까지 오랜 시간이 걸린다. 환경 가정 실패 시 후반 fallback 결정의 비용이 크다고 판단하여 기각.

**(B) MVP feature-by-feature (각 phase 독립 feature)**

각 phase를 독립적인 feature 단위로 구성하는 방식. 통합은 빠르지만, phase 간 데이터 흐름과 인터페이스 일관성이 흔들릴 위험이 있다. tracer-bullet은 전체 E2E 흐름을 하나의 선으로 유지하기 때문에 일관성 보장이 더 강하다고 판단하여 기각.
