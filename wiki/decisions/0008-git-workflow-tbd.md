---
status: Accepted
date: 2026-05-30
deciders: [dongmin]
supersedes: ""
superseded-by: ""
---

# 0008: Git 워크플로우로 Trunk-Based Development 채택

## Context

[[W0.5]] 검증을 지나 코드 작성 phase([[W1]]~)로 들어가기 전에, 이 repo의 git 작업 방식·커밋 컨벤션·PR 형식을 명시적으로 고정할 필요가 있다. 지금까지는 `main`에 docs 커밋만 쌓였고 (`chore:` / `docs(wiki):` 식 Conventional Commits), 브랜치 전략과 PR 형식이 정의되지 않았다.

이 프로젝트는 소수 인원 + 잦고 작은 변경(wiki ingest, phase 기록, [[tracer-bullet 로드맵]]의 수직 슬라이스)이 특징이다. 무거운 브랜치 모델(Git Flow의 develop/release 장수 브랜치)은 오버헤드가 크고 통합을 미뤄 "자주 통합" 정신과 어긋난다.

> [[ADR 0007]]은 [[W0.5]] 검증 결과 ADR로 예약됨. 본 결정은 0008번을 사용한다 (0007은 W0.5 완료 시 작성).

## Decision

**Git 워크플로우로 Trunk-Based Development(TBD)를 채택한다.**

- `main`을 단일 트렁크로 두고 항상 releasable 상태를 유지한다.
- 모든 변경은 `main`에서 분기한 **짧은 수명 브랜치**(수 시간 ~ 최대 1일)에서 작업하고 **PR**로 트렁크에 통합한다. 장수 브랜치를 두지 않는다.
- 커밋은 **Conventional Commits** — `type(scope): subject`, 영어, 간결(제목 ≤ ~72자, 본문은 선택·짧게). type: feat/fix/refactor/docs/test/chore/perf/ci.
- PR은 `.github/pull_request_template.md` 형식을 따르고 관련 phase 노트·ADR을 링크한다.

운영 세부는 [CONTRIBUTING.md](../../CONTRIBUTING.md)에, wiki 기록 규약은 [[SCHEMA.md]]에 둔다.

## Consequences

**긍정적 영향**

- 잦은 트렁크 통합 → 머지 충돌·드리프트 최소화. [[tracer-bullet 로드맵]]과 정합.
- 단순한 히스토리, 명확한 커밋/PR 형식 → 미래 세션·외부 기여자 onboarding 비용 절감.
- PR 템플릿이 wiki bookkeeping(log/index, ADR)을 체크리스트로 강제.

**부정적 영향 / 리스크**

- 작은 단위로 자주 쪼개는 규율이 필요. 큰 변경을 한 브랜치에 몰면 TBD 이점이 사라진다.
- 솔로 작업 시 PR이 형식적일 수 있으나, 기록·리뷰 트리거로서 가치를 유지한다.

**되돌리기 난이도**: 낮음. 워크플로우 문서·템플릿 교체로 전환 가능.

## Alternatives considered

**(A) Git Flow** — develop/release/hotfix 장수 브랜치. 릴리스 주기가 뚜렷한 대형 팀에 적합하나, 소수 인원 + 잦은 작은 변경에는 오버헤드가 과하고 통합 지연을 유발. 기각.

**(B) main 직접 커밋만 (브랜치·PR 없음)** — 가장 가볍지만 리뷰 게이트·변경 단위 추적이 약하고, 사용자가 원한 PR 형식 요구와 맞지 않음. 기각.

**(C) GitHub Flow** — TBD와 거의 동일(feature 브랜치 + PR)하나 브랜치 수명 강조가 약함. 본 ADR은 "짧은 수명"을 명시한 TBD로 채택 — 사실상 포함 관계.
