# wiki/log.md — 시계열 활동 로그

> 항목 prefix 규약: `## [YYYY-MM-DD] {ingest|decision|query|lint|phase} | <title>`
>
> 자세한 규약은 [SCHEMA.md](SCHEMA.md) section 6 참고.

---

## [2026-05-25] phase | W0 bootstrap 완료 — dev-wiki 뼈대 + ADR 5개 + system-design

W0 부트스트랩 산출물:

- `wiki/` 디렉터리 골격 (raw/grilling, decisions, concepts, architecture, phases) 생성
- 원본 source 2개를 `wiki/raw/` 로 이동 (`local-agent-server-spec.md`, `llm-wiki.md`)
- [SCHEMA.md](SCHEMA.md) — wiki 운영 규약 작성 (258줄)
- [glossary.md](glossary.md) — 도메인 용어 시드 22개 / 8 그룹 (167줄)
- [raw/grilling/2026-05-22-initial-grilling.md](raw/grilling/2026-05-22-initial-grilling.md) — 초기 그릴링 8개 결정 압축본 (111줄)
- ADR 0001 ~ 0005 작성 (`wiki/decisions/`)
- [architecture/system-design.md](architecture/system-design.md) — 원본 spec section 1~12 개정판 (558줄, ADR 5개 인용)
- `CLAUDE.md` 최상단에 dev-wiki 포인터 2줄 추가
- `work-plan.md` (root) 의 tmux → cmux 전역 치환, qwen3.5:9b 모델명 정확 명시, "cmux 단계 제거" 모순 표현 정정 (2026-05-25 grilling 결과)

실행 방식: Phase 0 (직접 Bash) → Phase 1 (Agent 3-way 병렬 + 직접 Edit) → Phase 2 (Agent 5-way 병렬 ADR) → Phase 3 (Opus executor 단일, system-design) → Phase 4 (직접 Write, index/log).

다음: W0.5 검증 게이트 진입 전 [Phase 5 verifier 일관성 검증] 및 Phase 6 (사용자 손, Ollama + cmux + OMC 환경 셋업).

## [2026-05-25] lint | W0 verifier 패스 — 18 PASS / 5 WARN / 1 FAIL → 모두 정정 완료

Phase 5 verifier (Opus) 가 wiki 전체 일관성을 검증. 결과 요약:

- **PASS (18)**: ADR 형식 일관성, 파일명 규약, system-design ↔ ADR 0001~0005 모순 없음, 로드맵 ↔ ADR 0005 일치, Manager/Worker 책임 ↔ ADR 0003 일치, index.md ↔ 실제 파일 매핑, log.md prefix 규약, SCHEMA.md 디렉터리 구조, grilling Q1~Q8 추적성 등
- **FAIL (1, 정정 완료)**:
  - `work-plan.md:112` 파일명 오기 `0004-qwen3-9b-as-manager.md` → `0004-qwen3.5-9b-as-manager.md`
  - `work-plan.md:184` 모델명 오기 `Qwen3 9B` → `qwen3.5:9b`
- **WARN (5, 일부 정정)**:
  - W0.5 메모리 임계값 통일 — work-plan.md 13GB → 14GB (wiki 정본 매칭)
  - glossary 누락 entry 추가 — `### llm-wiki`, `### 가드레일` umbrella
  - SCHEMA.md:150 deciders 예시 정정 — `[mindong, OMC]` → `[dongmin]` + 정책 주석
  - ADR 0006 placeholder 참조는 의도적 (W0.5 산출 예정)
  - index.md self-description은 P3 (선택적)

W0 부트스트랩 산출물의 wiki 내부 일관성 확보. W0.5 진입 가능.

## [2026-05-25] decision | 시스템 정의 확정 + ADR 0006 신설 + ADR 0007 재지정

사용자가 시스템 정의를 명시적으로 확정:

> "하나의 깃허브 레포지토리를 작업 공간으로 추적하는 로컬 에이전트 서버 기반의 에이전트 매니징 시스템"

방침: **1.0 은 단일 repo 로 한정, W0~W7 검증 완료 후 multi-repo 확장을 별도 ADR 로 결정.**

변경사항:

- [decisions/0006-system-scope-single-repo.md](decisions/0006-system-scope-single-repo.md) 신설 (82줄)
- 기존 placeholder 였던 W0.5 검증 결과 ADR → [[ADR 0007]] 로 재지정 (0004, system-design, work-plan, ADR 0006 본문에서 일괄 정정)
- [glossary.md](glossary.md) `## 시스템 정의 / ### 로컬 에이전트 서버` 그룹 신설
- [index.md](index.md) 첫 quote 에 시스템 정의 1줄 + ADR 0006 카탈로그 항목 추가
- [architecture/system-design.md](architecture/system-design.md) section 0 에 `### 시스템 정의` sub-section 삽입
- 루트 `CLAUDE.md` 와 `work-plan.md` 헤더에도 시스템 정의 1줄 추가

근거: 미래 세션이 "왜 이 시스템이 다중 repo 를 다루지 않지?" 라는 질문에 ADR 0006 으로 답할 수 있도록 의사결정 사슬에 명시적으로 포함.
