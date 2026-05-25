---
status: Accepted
date: 2026-05-25
deciders: [dongmin]
supersedes: ""
superseded-by: ""
---

# 0003: Manager / OMC Worker 간 Hybrid 책임 분담

## Context

[[Manager]] 역할을 맡은 [[qwen3.5:9b]] (9B 파라미터, Q4_K_M) 는 경량 로컬 모델이다. 초기 설계에서는 이 단일 LLM이 다음 모든 책임을 혼자 처리하는 방안도 검토됐다.

- 한국어 이슈 fetch 및 의도 파악
- Worker용 영문 prompt 빌드
- 코드 작성 및 테스트 실행
- 가드레일([[일일 토큰 cap]], [[작업당 turn cap]]) 집행
- PR 생성 (`gh` CLI)

그러나 실제 운영 관점에서 두 가지 문제가 드러났다.

**Manager 단독으로는 부족하다**: 9B 모델은 한국어 의도 파싱과 짧은 JSON 응답 생성에는 충분하지만, 복잡한 멀티 파일 코드 작성 및 테스트 실행을 안정적으로 수행하기에는 capability가 부족하다. JSON 일관성도 흔들릴 수 있다.

**[[OMC]] 단독으로는 통제가 어렵다**: [[OMC]]는 영문 코드 작업에 특화되어 있지만, 한국어 의도 파싱이 약하고, 외부 가드레일([[일일 토큰 cap]], [[작업당 turn cap]])을 강제할 메커니즘이 없다. OMC가 PR 생성 권한까지 보유하면 [[L2 자율성]] 원칙을 침범할 위험이 있다.

두 LLM의 강점을 어떻게 분할해야 시스템이 안전하게 동작하는가가 이 결정의 핵심 질문이다.

## Decision

**Hybrid C** 구조를 채택한다. [[Manager]]와 [[OMC]]의 책임을 한국어/승인/가드레일 측과 영문/코드 작성 측으로 명확히 분리한다.

### Manager 담당 영역

| 책임 | 세부 내용 |
|------|-----------|
| 이슈 fetch | GitHub issue를 가져와 한국어 의도 파악 |
| 정보 충분성 판단 | 작업 착수 가능 여부를 한국어로 1차 판단 |
| 영문 prompt 빌드 | [[OMC]]에 전달할 영문 작업 명세 구성 |
| 2단계 승인 게이트 | [[interrupt #2]] (코드 승인) + [[interrupt #3]] (PR 승인) |
| 가드레일 집행 | [[일일 토큰 cap]], [[작업당 turn cap]] 외부 강제 |
| diff 한국어 요약 | OMC 결과물을 한국어로 사용자에게 설명 |
| PR 생성 | 승인 후 `gh` CLI로 PR 생성 (OMC에는 이 권한 없음) |
| wiki distill | 작업 완료 후 [[dev-wiki]] 갱신 |

### OMC 담당 영역

| 책임 | 세부 내용 |
|------|-----------|
| 영문 계획 분해 | `autopilot:` magic keyword 또는 `/deepinit` 으로 계획 생성 |
| 코드 작성 / 실행 / 테스트 | Worker 역할 전체 — 멀티 파일 변경, 빌드, 테스트 포함 |
| 모호함 발생 시 추가 질문 | `/deep-interview` 를 통해 [[interrupt #1]] 트리거 |
| 재시도 | verifier 루프 (`ralph:` / `ultraqa:`) 로 자율 수정 |

### 핵심 원칙

> [[OMC]]는 코드 작성/테스트까지만 책임진다. PR 생성 권한은 없고, 가드레일은 외부([[Manager]])에서 강제한다.

한국어 → 영문 round-trip 흐름은 다음과 같다.

```
사용자(한국어) → Manager(의도 파악 + prompt 빌드) → OMC(코드 작성)
                                                      ↓ interrupt #1 (모호함)
OMC(결과 반환) → Manager(diff 한국어 요약 + interrupt #2) → 사용자 승인
                Manager(interrupt #3) → 사용자 PR 승인 → gh CLI PR 생성
```

## Consequences

**긍정적 영향**:

- 각 LLM이 강점에만 집중한다. 9B Manager는 짧은 한국어 판단과 프롬프트 빌드에만 집중하므로 capability 부담이 줄어든다.
- 가드레일([[일일 토큰 cap]], [[작업당 turn cap]])을 [[Manager]]가 외부에서 강제하므로 [[L2 자율성]]이 구조적으로 유지된다.
- [[OMC]]의 강력한 코드 작성 능력(haiku/sonnet/opus 모델 라우팅, 전문 에이전트 30개+)을 그대로 활용한다.
- 한국어/영문 round-trip이 [[interrupt #1]]/[[interrupt #2]]/[[interrupt #3]] 세 지점에서 명확히 구분된다.

**부정적 영향**:

- 두 LLM 간 통신 메커니즘이 추가된다. 한국어 → 영문 prompt 빌드 품질, 영문 응답 → 한국어 요약 품질 모두 검증이 필요하다.
- [[OMC]]의 `/deep-interview` ([[interrupt #1]]) 가 [[Manager]]의 interrupt round-trip과 매끄럽게 동작하는지 [[W3]] 검증 단계에서 확인해야 한다.
- [[OMC]] 내부 모델 라우팅(haiku/sonnet/opus)으로 인해 실제 토큰 비용 추정이 복잡하다. [[일일 토큰 cap]] 집행 시 OMC 내부 소비량을 어떻게 측정할지 별도 설계가 필요하다.

**되돌리기 난이도**: 중간. Manager/OMC 경계를 다시 그으려면 prompt 빌드 로직과 interrupt 처리 흐름을 재작성해야 한다.

## Alternatives considered

**(A) Manager가 모든 것 처리**

[[qwen3.5:9b]] 단일 모델이 의도 파싱부터 코드 작성, PR 생성까지 전담하는 방안. 아키텍처가 단순하지만, 9B 모델의 코드 작성 capability가 부족하고 JSON 응답 일관성이 흔들린다. 멀티 파일 코드 변경을 안정적으로 처리하려면 훨씬 큰 모델이 필요하다. 기각.

**(B) OMC가 모든 것 처리**

[[OMC]]가 이슈 fetch부터 PR 생성까지 전담하는 방안. 코드 품질은 높지만, 한국어 의도 파싱이 약하고, 가드레일을 외부에서 강제할 메커니즘이 없다. OMC가 PR 생성 권한까지 가지면 사용자 개입 없이 자율적으로 PR이 merge될 수 있어 [[L2 자율성]] 원칙을 위반한다. 기각.
