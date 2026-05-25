---
status: Accepted
date: 2026-05-25
deciders: [dongmin]
supersedes: ""
superseded-by: ""
---

# 0006: 시스템 범위 — 단일 GitHub repo (1.0), 검증 후 multi-repo 확장 도모

## Context

지금까지의 spec, ADR 0001~0005, [[system-design]] 어디에도 "이 시스템이 몇 개의 repo를 대상으로 하는가"가 명시적으로 확정된 적 없다. 원본 spec section 10의 "Repo: 1개 집중 (whitelist 단순화)" 문구가 유일한 언급이지만, 배경 이유와 경계 조건이 없는 한 줄에 불과하다.

이 공백이 낳는 질문들은 다음과 같다.

- [[Manager]]가 watching/fetch하는 target repo가 1개인가, N개인가?
- [[wiki distill]] (`distill_to_wiki` 노드)의 대상이 단수인가 복수인가?
- [[worktree]]가 어떤 repo를 분리하는 것인가?
- Discord bot 단일 인스턴스에서 여러 repo의 알림을 어떻게 구분하는가?

이 질문들에 대한 표준 답이 없으면 W1~W7 설계 전반에서 "단수 가정"이 암묵적으로 사용되고, 추후 multi-repo 시나리오 접촉 시 충돌이 발생한다.

또한 [[ADR 0001]]에서 확정된 dev-wiki vs [[target-repo wiki]] 구분, [[ADR 0005]]에서 정의된 [[tracer-bullet 로드맵]]은 모두 "target repo가 단수"라는 전제 위에서 설계되었다. 이를 소급해서 명시할 필요가 있다.

사용자 확정 정의 (2026-05-25):

> "하나의 깃허브 레포지토리를 작업 공간으로 추적하는 로컬 에이전트 서버 기반의 에이전트 매니징 시스템"

## Decision

**1.0 시스템 범위는 단일 GitHub repo로 한정한다.**

구체적 경계:

- [[Manager]]가 watching/fetch하는 target repo: **1개**
- [[Worker]]가 작업하는 [[worktree]]: 그 target repo의 branch들
- [[target-repo wiki]] distill 대상: **1개**
- 로컬 에이전트 서버 인스턴스 1개 = target repo 1개

결과적으로 1.0의 시스템 정체성:

> 하나의 GitHub repo를 작업 공간으로 추적하는, 로컬에서 돌아가는 에이전트 매니징 서버

**단일 repo 검증 완료 후 multi-repo 확장을 도모한다.**

검증 범위는 W0~W7 모든 phase 완료, [[L2 자율성]] / [[가드레일]] / interrupt 사이클 운영 안정성 확인이다. multi-repo 확장은 별도 ADR (향후 ADR 00XX-multi-repo-expansion)으로 결정한다.

**[[ADR 0007]] 재지정**: 이전 spec/system-design에서 `wiki/decisions/0006-omc-validation-result.md`로 예약되어 있던 [[W0.5]] 검증 결과 ADR은 본 ADR 0006 채번으로 인해 **[[ADR 0007]]**로 재지정된다.

## Alternatives considered

**(A) Multi-repo from day 1**

여러 target repo를 처음부터 지원하는 방식. 이 경우 이슈 라우팅 (어떤 repo의 이슈인가), 우선순위 / 자원 분배 로직, Discord 알림 채널 구분이 즉시 필요하다. [[ADR 0005]]의 [[tracer-bullet 로드맵]]이 정의한 [[W1]] E2E 스파이크의 통합 위험이 repo 수만큼 곱셈으로 증가한다. 1.0 검증 비용이 폭증하므로 기각.

**(B) Single repo + multi-repo extension hooks (인터페이스만 추상화)**

1.0은 단일 repo로 운영하되, `RepoRouter` 같은 추상 인터페이스를 미리 도입하는 방식. YAGNI 원칙 위반 — 검증되지 않은 추상화는 미래 refactor의 부담이 된다. "쓰지 않을 인터페이스"를 유지보수해야 하는 비용이 실제 확장 시 얻는 이득보다 크다고 판단하여 기각.

**(C) Repo 종속 없이 task-only 시스템 (GitHub 통합 제거)**

GitHub 이슈 fetch, PR 생성, [[wiki distill]] 노드를 제거하고 task 단위만 처리하는 방식. 시스템의 핵심 가치인 이슈 연동 / PR 추적 / 노하우 distill이 의미를 잃는다. 사용자 확정 정의와 충돌하므로 기각.

## Consequences

**긍정적 영향**:

- 1.0 설계 단순화 — repo 라우팅, 우선순위, 자원 분배 로직 불필요. [[W1]]~[[W7]] 설계 surface가 작아진다.
- [[worktree]], [[target-repo wiki]] distill, [[가드레일]]이 모두 1개 repo 기준으로 명확히 정의된다.
- 검증 surface가 작음 → W0~W7 통과 비용 절감.
- [[interrupt #1]]~[[interrupt #3]] / [[L2 자율성]]의 의미가 1개 repo 컨텍스트에서 명확히 정의된다.
- 향후 multi-repo 확장 시, 검증된 단일 repo 동작을 reference behavior로 활용 가능.

**부정적 영향**:

- 사용자가 동시에 여러 repo를 다루려면 별도 인스턴스 (별도 Ollama + FastAPI + Discord bot 세트)를 띄워야 한다 — 1.0의 명시적 한계.
- multi-repo 확장 시 라우팅 / 인스턴스 매핑 / Discord 채널 분리 등 refactor 비용이 발생한다.
- Discord bot 단일 인스턴스에서 multi-repo 구분이 안 됨 — 확장 시 채널/스레드 기반 라우팅 신설 필요.
- 미래 확장 ADR 시점에 ADR 0001~0006 일부가 superseded 처리될 가능성이 있다.

**되돌리기 난이도**: 낮음 (1.0 내). W0~W7 완료 전까지 단일 repo 가정은 설계 전반에 스며 있으므로, 변경 시 영향 범위가 넓다. 그러나 이것은 확장을 막는 것이 아니라 확장을 별도 ADR 결정으로 명시적으로 분리하겠다는 의도다.
