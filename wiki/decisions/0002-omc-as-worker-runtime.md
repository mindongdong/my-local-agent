---
status: Accepted
date: 2026-05-25
deciders: [dongmin]
supersedes: ""
superseded-by: ""
---

# 0002: Worker 실행을 OMC + cmux 조합으로 통일

## Context

원본 spec section 9 로드맵은 [[Worker]] 실행 runtime을 두 단계로 점진 도입하는 방안을 제안했다.

- **Phase 1**: `claude -p` headless 모드로 단순 subprocess 실행
- **Phase 2**: [[cmux]] pane 기반 오케스트레이션으로 전환

이 점진적 접근은 단기 안정성을 확보하는 대신, 통합 위험을 뒤로 미루는 구조다. W1에서 headless로 시작해 W6 시점에 cmux로 전환하면 당시 대규모 refactor가 불가피하다. 실행 모델, 통신 프로토콜, pane 격리 로직이 모두 바뀌어야 하기 때문이다.

반면 [[OMC]] (oh-my-claudecode)는 이미 다음을 내장한 통합 솔루션을 제공한다.

- [[cmux]] 기반 pane 오케스트레이션 (`send-keys` / `capture-pane`)
- 30개 이상의 전문 에이전트 생태계
- [[magic keyword]] (`autopilot:`, `ralph:`, `ulw`, `team`) 를 통한 작업 모드 선택
- Hook 시스템 및 worktree 격리

개발자가 일상적으로 사용하는 도구와 [[Worker]] 실행 도구가 다르면, 두 도구 스택을 동시에 이해하고 유지해야 하는 부담이 생긴다. ([[Hybrid 책임 분담]] 참고)

## Decision

**Worker 실행 runtime을 OMC + cmux 조합으로 처음부터 통일한다.**

원본 spec의 `claude -p` headless 단계 (Phase 1)를 스킵하고, W1부터 OMC + cmux를 Worker runtime으로 사용한다. 개발자가 작업할 때도, [[Worker]]가 실행될 때도 동일한 도구 스택([[OMC]], [[cmux]])을 사용한다.

[[Manager]]는 [[cmux]] `send-keys`로 Worker pane에 명령을 전달하고, `capture-pane`으로 출력을 수집한다. [[magic keyword]]를 통해 작업 복잡도에 따라 OMC 모드를 선택할 수 있다. 이 결정은 [[Hybrid 책임 분담]]의 OMC 측 책임 범위를 명시적으로 확정한다.

## Consequences

**긍정적 영향**

- 도구 스택 통일로 학습 비용과 유지보수 부담 절감
- [[OMC]] [[magic keyword]] 및 에이전트 생태계를 W1부터 즉시 활용
- [[cmux]] pane 격리로 Worker별 추적성 확보 (`capture-pane` 기반 로그)
- Phase 1 → Phase 2 전환 시점의 대규모 refactor 제거

**부정적 영향 / 리스크**

- [[cmux]] 통신 안정성을 W0.5 검증 게이트에서 조기 결판해야 함 (round-trip 성공률 ≥ 99% 기준). 통과 실패 시 이 결정을 재검토한다.
- 다중 OMC 세션 동시 실행 시 메모리 부담. [[qwen3.5:9b]] + OMC 세션 복수 병렬 실행은 16GB Mac Mini에서 빡빡할 수 있다. W0.5에서 실측 필요.
- OMC의 `autopilot`/`ralph` 루프가 [[L2 자율성]] 원칙과 충돌 가능. [[worktree]] 환경에서 `gh` CLI 차단 등 가드레일을 별도 설계해야 한다.

**되돌리기 난이도**: 중간. W0.5 게이트 실패 시 Phase 1 headless로 회귀 가능하나, W1 이후 전환은 비용이 크다.

## Alternatives considered

**(B) 원본 spec 그대로 Phase 1 headless 유지**

`claude -p` subprocess로 시작해 W6에서 cmux로 전환. 초기 단순성과 안정성은 확보되지만, 전환 시점의 refactor 규모가 크다. [[magic keyword]] 활용도 W6까지 불가하다. 채택하지 않는 이유: 통합 위험을 뒤로 미루는 것이 이득보다 손실이 크다고 판단.

**(C) cmux 없이 단순 multi-process Worker**

OS 수준의 subprocess로 Worker를 실행하고 stdin/stdout으로 통신. 구현 단순성은 최대지만, [[magic keyword]] 활용 불가, pane 단위 추적성 약함, OMC 에이전트 생태계 미활용. 채택하지 않는 이유: 장기 확장성 부재.
