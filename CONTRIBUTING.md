# Contributing

이 repo의 git 작업 규약. 결정 배경은 [wiki/decisions/0008-git-workflow-tbd.md](wiki/decisions/0008-git-workflow-tbd.md), wiki 운영 규약은 [wiki/SCHEMA.md](wiki/SCHEMA.md) 참고.

## Git 워크플로우 — Trunk-Based Development

- `main`이 트렁크. 항상 releasable 상태를 유지한다.
- 모든 변경은 `main`에서 분기한 **짧은 수명 브랜치**(수 시간 ~ 최대 1일)에서 작업하고 **PR**로 트렁크에 통합한다. 장수 브랜치를 두지 않는다.
- PR 열기/머지 전 최신 `main`에 rebase. 브랜치를 작게 유지해 통합을 자주 한다.

### 브랜치 이름
`<type>/<short-desc>` — 예: `feat/discord-mention`, `fix/cmux-timeout`, `chore/git-conventions`.

## 커밋 — Conventional Commits

`<type>(<scope>): <subject>`

- 영어, 명령형, 간결. 제목 ≤ ~72자. 본문은 선택이며 짧게 — 제목으로 충분하면 생략.
- **type**: `feat` `fix` `refactor` `docs` `test` `chore` `perf` `ci`
- **scope** (이 repo): `wiki` `adr` `manager` `worker` `cmux` `discord` `infra` …
- 예: `docs(wiki): record W0.5 cmux round-trip`, `feat(manager): add issue intent parser`

## Pull Request

- `main` 대상으로 [PR 템플릿](.github/pull_request_template.md)을 채워 연다. 모든 섹션 작성.
- PR은 작고 집중되게. 관련 phase 노트와 ADR을 링크한다.
- 남길 가치가 있는 결정 → ADR(`wiki/decisions/NNNN-*.md`) 추가 + `wiki/index.md`·`wiki/log.md` 갱신 (SCHEMA 참고).

## 커밋하지 말 것
- 시크릿 / API 키, 빌드 산출물, `.omc/` 런타임 상태 (git-ignored).
