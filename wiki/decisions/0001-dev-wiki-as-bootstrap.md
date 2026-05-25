---
status: Accepted
date: 2026-05-25
deciders: [dongmin]
supersedes: ""
superseded-by: ""
---

# 0001: dev-wiki를 부트스트랩 단계에 통합

## Context

원본 spec(`wiki/raw/local-agent-server-spec.md`) section 6은 [[target-repo wiki]]만 다룬다. [[Manager]]가 작업을 완료한 후 외부 타겟 저장소에 노하우를 distill하는 역할로 wiki를 정의하고 있으며, 이 에이전트 서버 자체를 빌드하는 과정에서 얻은 결정과 노하우를 어디에 누적할지는 명시되어 있지 않았다.

미래 세션이 컨텍스트 없이 진입할 경우, 흩어진 결정들을 다시 발굴해야 하는 비용이 발생한다. [[W0]] 시점부터 의사결정이 누적되고 있으므로, 이 서버 자체의 빌드 노하우를 추적할 구조가 즉시 필요하다. `wiki/raw/llm-wiki.md`에 정의된 [[llm-wiki]] 철학 — LLM이 살아있는 지식 베이스로 직접 사용·갱신하여 지식이 복리로 축적된다 — 을 이 프로젝트에 즉시 적용할 수 있는 시점이기도 하다.

## Decision

[[W0]] (프로젝트 시작) 시점에 [[dev-wiki]](`wiki/`)를 함께 구축한다.

- 모든 그릴링 결과, ADR, system-design을 `wiki/` 안에 점진적으로 축적한다.
- 원본 spec과 llm-wiki 철학 등 원본 소스는 `wiki/raw/`에 immutable하게 보존하고, LLM은 읽기만 한다.
- [[SCHEMA.md]]에 정의된 ingest/query/lint 워크플로우와 형식 규약을 모든 LLM 세션이 따른다.
- [[llm-wiki]] 철학을 [[dev-wiki]]에 직접 적용한다. 지식은 질문마다 재발견되는 것이 아니라 wiki에 한 번 컴파일되어 재사용된다.

## Consequences

**긍정적 영향**:

- 미래 세션이 `wiki/index.md`에서 출발하여 빌드 노하우를 즉시 흡수할 수 있다.
- 결정의 근거가 ADR로 추적 가능하며, 결정이 뒤집힐 경우 `superseded-by` 필드로 연결된다.
- 그릴링 결과와 실험 산출물이 `wiki/raw/`에 immutable로 보존되어, 나중에 결정을 재평가할 수 있다.
- [[SCHEMA.md]]가 단일 규약 출처 역할을 하므로, 세션 간 wiki 형식 불일치가 방지된다.

**부정적 영향**:

- [[W0]]에 초기 부담이 집중된다 (wiki 뼈대 구축, SCHEMA 정의, ADR 초기 세트 작성 — 약 1일 소요).
- 각 phase 완료 시 `log.md`와 `index.md`를 갱신해야 하므로 빌드 속도가 약간 느려질 수 있다.

**되돌리기 난이도**: 낮음. wiki 디렉터리를 제거하면 이전 상태로 돌아가지만, 그 시점까지 축적된 ADR과 로그는 손실된다.

## Alternatives considered

**(B) wiki 없이 진행, 나중에 ad-hoc 정리**

작업 초기에는 빠르게 진행할 수 있다. 그러나 결정 추적성이 없어서 미래 세션이 맥락을 재발굴해야 하는 비용이 증가한다. "나중에 정리"는 실제로 실행되지 않는 경우가 많으며, 누락된 결정을 재구성하는 비용이 초기 wiki 구축 비용보다 크다고 판단하여 기각.

**(C) ADR만 표준화 (`docs/adr/`), glossary/log/phases는 lazy 생성**

ADR만으로는 용어 불일치와 상호 참조 부재 문제가 해결되지 않는다. glossary 없이 ADR을 작성하면 같은 개념을 다른 이름으로 부르는 혼선이 생기고, log 없이는 시계열 흐름을 파악할 수 없다. 또한 `docs/adr/`로 분산하면 `wiki/raw/`와의 연결이 끊겨 발견성이 떨어진다고 판단하여 기각.
