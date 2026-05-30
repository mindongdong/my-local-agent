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

## [2026-05-30] phase | W0.5 진입 — 환경 셋업 + 메모리/모델 선측정

W0-9 환경 셋업 완료 및 W0.5 측정 항목 일부 선측정:

- `brew install ollama` (0.24.0) + `brew services start ollama` (launchd 등록)
- `ollama pull qwen3.5:9b` 완료 → **정품 Qwen3.5 (Tongyi Lab) 확정** (`ollama show`: arch `qwen35`, 9.7B, 262144 ctx, Q4_K_M, vision+tools+thinking, Apache 2.0)
- 메모리 실측: **로드 RAM 8.5GB@4k ctx** (plan 가정 6.6GB는 디스크 크기), 모델+세션1개에서 free 105M + swapout 이력 → 메모리 binding constraint 확정
- 추론 ~25 tok/s (warm). interactive `think:true`에서 thinking 트레이스 헛소리 관측 → Manager는 `think:false` + JSON schema 강제 권고

영향 페이지: [phases/w0.5-validation.md](phases/w0.5-validation.md) 신설, [decisions/0004-qwen3.5-9b-as-manager.md](decisions/0004-qwen3.5-9b-as-manager.md) 메모리 정정 노트, 루트 work-plan.md §4 표 보정, [index.md](index.md) Phase 노트 항목.

미측정 W0.5 항목 (다음): cmux round-trip(실제 0.64.10 API로 재설계), `ulw` 2 동시성, JSON schema 준수율, 모델 라우팅. 완료 후 ADR 0007.

## [2026-05-30] phase | W0.5 cmux round-trip 측정 — 300/300 PASS

cmux 스킬 기반으로 cmux 통신 안정성 실측 ([work-plan.md](../work-plan.md) §8 / [[ADR 0002]] 핵심 리스크):

- 이 Claude Code 세션이 cmux `workspace:2/surface:4` 안에서 직접 구동됨을 `cmux identify`로 확인 → Manager가 다른 surface를 구동하는 실제 시나리오 재현
- probe: `cmux new-workspace --focus false` → `workspace:5/surface:9`, round-trip = `send` + `send-key Enter` + `read-screen`, 출력 토큰을 `$((i*7))` 산술 결과로 설계해 실제 실행만 카운트
- 결과: **300회 (100+200) 전부 성공 (100%)**, 평균 지연 0.277s / 최대 0.329s, 실패율 95% 상한 ~1%
- `close-workspace` 후 토폴로지 원상복구 + caller 포커스 유지 = 비파괴 자동화 확인
- 판정: **cmux 통신 PASS** → ADR 0002 리스크 해소

영향 페이지: [phases/w0.5-validation.md](phases/w0.5-validation.md) cmux 결과 섹션, [decisions/0002-omc-as-worker-runtime.md](decisions/0002-omc-as-worker-runtime.md) 측정 노트.

## [2026-05-30] lint | TODO — cmux API 어휘 정합화 (stale claim)

cmux 0.64.10 실측 결과 tmux식 `send-keys`(복수형)·`new-session`은 존재하지 않음 (`capture-pane`은 tmux-compat로 유효). 다음 페이지의 `send-keys`/`new-session` 표현을 `send`+`send-key`/`new-workspace`로 정정 필요 — **별도 패스로 진행 예정**:

- `architecture/system-design.md` — L79, L211~215, L258, L371, L416, L429, L497 (~10곳, section 4 lifecycle 포함)
- `glossary.md` — L129 (`### cmux` 정의)
- `decisions/0005-tracer-bullet-roadmap.md` — L70 (이미 "재정의 필요"로 예고됨)
- `work-plan.md` — L168, L232, L257, L280
- 제외: `raw/grilling/2026-05-22-initial-grilling.md` (immutable)
- ADR 0002는 본 turn에 측정 노트로 정정 완료.

## [2026-05-30] phase | W0.5 동시 워커/메모리 측정 — ulw 가정 반증

[work-plan.md](../work-plan.md) §8 `ulw` 동시성 항목 실측:

- 모델 로드(8.5GB)가 지배적 메모리 이벤트: free 76%→14~17%, swap +1.3GB
- claude 워커 각 idle RSS ~213MB. `cmux new-workspace --command 'claude' --focus false` ×2 spawn 시 free% 평탄(17%→17%), +0.43GB. `close-workspace`로 즉시 회수
- 측정 내내 기존 claude 3개 가동 = 사실상 ≥3 동시 워커
- **결론**: `ulw` 병렬은 서버측 subagent라 로컬 RAM N배 증가 없음 → plan §4 "ulw 5병렬 +1.5GB" 반증. 메모리 리스크 = 모델(8.5GB) + 데스크톱 앱(Chrome/VSCode ~1~1.5GB), 워커 수 아님. 2 동시 워커 메모리 안전. 헤드리스 운영이 14GB 임계값 관건
- 측정 후 모델 언로드(`keep_alive:0`) → free 73% 복구

영향 페이지: [phases/w0.5-validation.md](phases/w0.5-validation.md) 동시 워커 섹션 + 흔들린 가정 #4, [work-plan.md](../work-plan.md) §4 표.

W0.5 진척: 메모리 ✅ / 모델 ✅ / cmux round-trip ✅ / 동시 워커 ✅. 남은 항목: JSON schema 준수율, 모델 라우팅 → 완료 후 ADR 0007.

## [2026-05-30] lint | cmux API 어휘 정합화 완료 (위 TODO 처리)

위 `[2026-05-30] lint | TODO` 항목 실행 완료 (executor 위임 + grep 검증):

- `architecture/system-design.md` (7곳), `glossary.md` (1곳), `decisions/0005-tracer-bullet-roadmap.md` (1곳), `work-plan.md` (5곳)에서 `send-keys`→`send`+`send-key`, `new-session -d`→`new-workspace --focus false` 정정
- `capture-pane`은 cmux tmux-compat로 유효하여 전부 보존 (system-design 10곳 등 무손상)
- 검증: `grep -rn -E "send-keys|new-session" wiki/ work-plan.md` → 남은 것은 ADR 0002(errata 노트 방식, 본문 유지), log.md·phases 이력 기록, raw/grilling(immutable)뿐
- ADR 0002는 본문을 직접 고치지 않고 `[API 어휘 정정]` errata 노트로 처리 (ADR=결정 기록 불변 원칙)

## [2026-05-30] decision | git 워크플로우 체계 수립 + ADR 0008

코드 phase(W1~) 진입 전 git 작업 규약을 명시적으로 고정 (사용자 결정: TBD + Conventional Commits + PR 형식):

- [decisions/0008-git-workflow-tbd.md](decisions/0008-git-workflow-tbd.md) 신설 — Trunk-Based Development(짧은 수명 브랜치 + PR로 트렁크 통합), Conventional Commits(영어·간결), PR 템플릿
- `CONTRIBUTING.md` (root) — 운영 가이드 (브랜치/커밋/PR 규약)
- `.github/pull_request_template.md` — PR 형식 (Summary/Changes/Related/Verification/Checklist)
- `.gitignore` — `.omc/` 런타임 상태 제외
- [glossary.md](glossary.md) `## 개발 프로세스` 그룹 신설 (Trunk-Based Development, Conventional Commits), qwen3.5:9b 메모리 표기 8.5GB 정정
- [index.md](index.md) decisions에 ADR 0008 + 0007 예약 표기, 규약 섹션에 CONTRIBUTING 링크

통합 방식: 짧은 브랜치 + PR. 이 변경부터 해당 규약 적용.

## [2026-05-30] phase | W0.5 JSON schema 준수율 측정 — 93% PASS (방법 정정)

[work-plan.md](../work-plan.md) §10 High 리스크(9B의 JSON 일관성) 실측:

- **1차 함정**: ollama `format`(JSON schema 객체)에 의존 → triage 0/8 → 잘못된 "21%". raw 출력 확인 결과 모델이 스키마를 무시하고 임의 키(`issue_type/severity` 등) 생성
- **원인 규명 (probe)**: `{verdict: enum[APPROVE,REJECT]}` + "Say hello" → `"Hello there!..."` (JSON조차 아님). **ollama 0.24.0 + qwen3.5:9b + /api/chat에서 `format` 스키마가 강제되지 않음**
- **정정 측정 (prompt-explicit + 코드 검증, temp=0)**: 14개 한국어 케이스 — triage 구조 8/8·의미 7/8, 충분성 구조 6/6·의미 6/6 → **구조 14/14(100%), 의미 13/14(93%)**. temp=0 결정성·temp=1 안정성 양호
- **판정**: JSON 신뢰성 PASS. 단 plan/ADR의 "JSON schema 강제" 완화책은 **ollama format이 아니라 프롬프트 구조 명시 + 코드 검증 + 재시도**로 구현해야 함 (ADR 0004·system-design 리스크에 측정 노트 추가)

영향 페이지: [phases/w0.5-validation.md](phases/w0.5-validation.md) JSON schema 섹션 + 흔들린 가정 #5, [decisions/0004-qwen3.5-9b-as-manager.md](decisions/0004-qwen3.5-9b-as-manager.md), [architecture/system-design.md](architecture/system-design.md) High 리스크.

W0.5 진척: 메모리 ✅ / 모델 ✅ / cmux round-trip ✅ / 동시 워커 ✅ / JSON schema ✅. **남은 항목: 모델 라우팅(`eco:`→haiku) 1개** → 완료 후 ADR 0007.

## [2026-05-30] decision | W0.5 게이트 종료 — ADR 0007 Go (헤드리스 전제)

[[W0.5]] 검증 게이트 종료. 사용자 결정: 모델 라우팅 측정은 연기하고 ADR 0007 작성:

- [decisions/0007-omc-validation-result.md](decisions/0007-omc-validation-result.md) 신설 — **Go**. qwen3.5:9b + OMC + cmux 스택 유지, [[W1]] 진입
- Go 기준 3개: ① 메모리(헤드리스 전제 충족) ② cmux 300/300 ✅ ③ ulw 2 ✅. 보너스 JSON 93% ✅
- 운영 전제: 헤드리스 / Manager 컨텍스트 캡 / JSON은 프롬프트+검증 / 라우팅은 W1에서 `/trace`로 확인
- No-go fallback(Gemma, headless 회귀, 동시성 1) 미발동
- [phases/w0.5-validation.md](phases/w0.5-validation.md) 상태 완료 처리, [index.md](index.md) 0007 카탈로그 갱신

다음: W1 E2E 스파이크 (Discord → cmux OMC → 한국어 diff).
