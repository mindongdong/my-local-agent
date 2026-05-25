# Initial Grilling — 2026-05-22

> 원본 spec (`wiki/raw/local-agent-server-spec.md`) 에 두 가지 추가 요구사항 (dev-wiki + OMC/cmux) 을 얹은 후 진행한 8개 결정. 결정의 결과는 `work-plan.md`, ADR 0001~0005, `wiki/architecture/system-design.md` 에 반영.

---

## Q1. 어떤 wiki를 세팅하는가?

**선택**: 에이전트 서버 자체의 dev-wiki (in-repo). spec section 6의 타겟 repo용 wiki와는 별개

**대안**:
- (B) 타겟 repo의 wiki를 직접 운영하고 dev 정보는 분산 보관
- (C) 단일 중앙 wiki로 dev-wiki와 target-repo wiki 통합

**근거**: 에이전트 서버 개발 과정과 최종 산출물용 문서는 생명주기가 다르다. dev-wiki는 빌드 단계에서 나오는 결정/실패 패턴/기술 선택을 즉각 ingest해야 빠르게 성장하지만, 타겟 repo wiki는 안정화된 정보만 담아야 사용자 혼동을 줄일 수 있다. 따라서 이 프로젝트 내부의 `wiki/` 폴더에 dev-wiki를 두고, 나중에 W6에서 선별하여 target-repo로 distill하는 구조로 확정.

---

## Q2. CLAUDE.md의 역할

**선택**: 분리. 현재 generic behavioral guidelines 유지 + `wiki/SCHEMA.md` 포인터만 추가

**대안**:
- (A) CLAUDE.md에 dev-wiki 규약을 전부 인라인 작성
- (B) 프로젝트 별도 설정 파일 (SCHEMA.json) 신설

**근거**: CLAUDE.md는 이미 generic behavioral patterns (Think Before Coding, Simplicity First, Surgical Changes, Goal-Driven Execution)으로 안정화되어 있고, 다른 프로젝트에서도 재사용하는 문서다. wiki-specific한 규약 (ingest/query/lint 워크플로우, ADR 형식, log 규약 등)을 섞으면 이 파일의 재사용성이 떨어진다. 따라서 `wiki/SCHEMA.md`를 별도 파일로 두고, CLAUDE.md의 맨 위에 그것을 가리키는 포인터 2줄만 추가하는 것이 맞다.

---

## Q3. wiki 폴더 뼈대 구조

**선택**: **(A) 흡수**. ADR, glossary, index, log를 모두 `wiki/` 안으로 통합

**대안**:
- (B) 루트에 `docs/adr/`, `docs/glossary/`를 분산 배치
- (C) wiki 폴더를 최소화하고 대부분을 spec 본문으로 표현

**근거**: llm-wiki 철학은 의사결정/용어/개념이 일관되게 누적되는 단일 정보 원천을 강조한다. ADR을 `decisions/` 폴더로, glossary를 `wiki/glossary.md`로, raw source를 `wiki/raw/`로 집중화하면 LLM이 나중에 질문할 때 한 곳에서 모두 찾을 수 있다. 분산 구조는 탐색 비용이 높고 모순이 생기기 쉽다.

---

## Q4. OMC+cmux의 사용 범위

**선택**: **(C) 개발자 + Worker 양쪽 통일**. 동일 도구 스택

**대안**:
- (A) 개발자만 OMC 사용, Manager/Worker는 기존 Phase 1 구조 (headless `claude -p`)
- (B) Worker만 OMC, Manager는 순수 Qwen/FastAPI

**근거**: OMC는 30개의 전문 에이전트 + magic keyword + cmux 오케스트레이션을 내장한 플러그인으로, 이미 Claude Code에 통합되어 있다. 개발자와 Worker가 다른 도구를 쓰면 학습 곡선이 2배 필요하고, 통합 문제 (worktree 관리, 환경 변수 동기화, 모델 라우팅) 도 복잡해진다. 따라서 양쪽 모두 OMC 위에서 운영하고, Manager는 한국어/승인/가드레일로 권한을 제한하는 방식이 맞다.

---

## Q5. OMC의 실체

**선택**: Claude Code 플러그인. 30개 전문 에이전트 + magic keyword + Hook + cmux 오케스트레이션 내장

**대안**:
- (A) OMC는 외부 서버 (별도 LLM 포함)
- (B) OMC는 경량 명령 라우터만

**근거**: OMC는 Anthropic이 만든 Claude Code의 네이티브 플러그인이며, Claude Code를 띄운 순간 사용 가능하다. 그 안에 이미 30개의 전문 에이전트 (executor, verifier, planner, architect, etc.), magic keyword (`autopilot:`, `ralph:`, `ulw`, `team` 등), 설정 hooks (PreToolUse, PostToolUse, Stop), cmux 연동이 전부 들어 있다. 따라서 OMC를 외부 서버로 구축할 필요 없다. 우리가 해야 할 일은 이 플러그인을 명시적으로 활성화하고, Manager와의 책임 분담 경계를 그리는 것뿐이다.

---

## Q6. Manager/OMC 책임 분담

**선택**: **(C) Hybrid**. Manager는 한국어/승인/가드레일, OMC는 영문 코딩 작업 전체

**대안**:
- (A) Manager가 전부 담당 (OMC는 보조 도구)
- (B) OMC가 전부 담당 (Manager는 이슈 수신만)

**근거**: Manager는 사람이고 OMC는 에이전트인데, 각각의 강점이 다르다. Manager는 한국어를 모국어로 이해하고 이슈 의도를 맥락적으로 파악하며 승인/거부 판단을 내린다. OMC는 영문 코드 작성/테스트/리팩터링을 빠르게 한다. 따라서 Manager가 이슈 fetch → 한국어 의도 파악 → 정보 충분성 판단 → 영문 prompt 빌드까지 하고, OMC가 그것을 받아 계획 분해/코드 작성/테스트를 끝낸 뒤 Manager한테 승인을 받는 구조가 맞다. 이렇게 하면 양쪽 모두 과부하를 피할 수 있다.

---

## Q7. 결정 기록 방식

**선택**: **(A) spec 인라인 수정 + ADR 병행 + 원본은 `wiki/raw/`에 immutable 보존**

**대안**:
- (B) spec 원본 보존 + 변경사항은 별도 CHANGELOG.md
- (C) 매 결정마다 새로운 spec 버전 생성 (spec-v1, spec-v2, ...)

**근거**: 원본 spec은 `wiki/raw/local-agent-server-spec.md`로 이동하여 immutable로 보존한다. 그 위에 진행 중인 시스템 설계는 `wiki/architecture/system-design.md`에서 항상 최신 상태로 유지한다 (spec의 개정본). 각 큰 결정은 ADR로 formal하게 기록해서 나중에 "왜 이걸 했나"를 빠르게 추적할 수 있게 한다. 이렇게 하면 최신 상태도 명확하고, 원본 spec도 참고할 수 있고, 결정 근거도 분명하다.

---

## Q8. 로드맵 패러다임

**선택**: **(C) Tracer-bullet + W0.5 검증 게이트**

**대안**:
- (A) Layer-by-layer (Manager → Worker → PR 처리 → wiki distill → 운영 → ...)
- (B) Waterfall (단계 간 종료 확인 후 진입)

**근거**: 원본 spec은 Manager LLM (Gemma) + Phase 1/2 구조를 가정했는데, 우리는 Qwen + OMC + cmux로 바꿨다. 이게 실제로 Mac Mini 16GB에서 돌아가는지 미리 검증하지 않으면 W1에서 메모리 터질 수 있다. 따라서 W0 (wiki 뼈대 + 환경 셋업) 직후 W0.5에서 send-keys/capture-pane 안정성 + 메모리 peak + 모델 라우팅을 100회 테스트로 결판 낸다. Go 기준을 만족하면 W1 (E2E 스파이크)으로 들어가고, No-go면 Gemma 다운그레이드 또는 headless fallback을 실행한다. 이 방식이 layer-by-layer보다 위험이 적다.

---

## 참고: 이 그릴링의 결과

이 8개 결정은 다음 문서들에 반영되어 있다:

- **work-plan.md** — 전체 맥락, 책임 분담, W0~W7 로드맵
- **wiki/architecture/system-design.md** — 개정된 시스템 설계 (spec 업데이트 버전)
- **wiki/decisions/000X-*.md** — ADR 5개 (dev-wiki, OMC, Hybrid, Qwen, Tracer-bullet)
- **wiki/SCHEMA.md** — wiki 규약 (ingest/query/lint/ADR 형식)
- **wiki/glossary.md** — 도메인 용어 (Manager, Worker, OMC, magic keyword, ...)
