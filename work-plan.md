# 작업 계획 (Work Plan)

> **시스템 정의** (2026-05-25 확정): "하나의 깃허브 레포지토리를 작업 공간으로 추적하는 로컬 에이전트 서버 기반의 에이전트 매니징 시스템" — 1.0 범위는 단일 repo, 검증 완료 후 multi-repo 확장 도모. [wiki/decisions/0006-system-scope-single-repo.md](wiki/decisions/0006-system-scope-single-repo.md).
>
> 원본 spec `local-agent-server-spec.md`에 추가 요구사항 2개 (dev-wiki + OMC/cmux)를 반영한 그릴링 결과 기반 실행 계획.
>
> *Last updated: 2026-05-25*

---

## 0. 추가 요구사항

원본 spec 위에 다음 두 가지를 얹는다:

1. **프로젝트 시작 시 llm-wiki 철학에 따른 wiki 폴더 뼈대 구축 + CLAUDE.md 세팅**
2. **oh-my-claude-code (OMC) + cmux 조합으로 실제 작업 진행**

이 두 요구가 spec section 1, 4, 6, 9, 10, 11과 광범위하게 충돌하며, 그릴링으로 정리한 결과는 아래와 같다.

---

## 1. 그릴링 결정 사항 (8건)

| # | 질문 | 결정 |
|---|---|---|
| 1 | 어떤 wiki를 세팅하는가? | **에이전트 서버 자체의 dev-wiki** (in-repo). spec section 6의 타겟 repo용 wiki와는 별개 |
| 2 | CLAUDE.md의 역할 | **분리**. 현재 generic 내용 유지 + `wiki/SCHEMA.md` 포인터만 추가 |
| 3 | wiki 폴더 뼈대 구조 | **(A) 흡수**. ADR/glossary 모두 `wiki/` 안으로 통합 |
| 4 | OMC+cmux의 사용 범위 | **(C) 개발자 + Worker 양쪽 통일**. 동일 도구 스택 |
| 5 | OMC의 실체 | Claude Code 플러그인. 30개 전문 에이전트 + 매직 키워드 + Hook + cmux 오케스트레이션 내장 |
| 6 | Manager/OMC 책임 분담 | **(C) Hybrid**. Manager는 한국어/승인/가드레일, OMC는 영문 코딩 작업 전체 |
| 7 | 결정 기록 방식 | **(A) spec 인라인 수정 + ADR 병행 + 원본은 `wiki/raw/`에 immutable 보존** |
| 8 | 로드맵 패러다임 | **(C) Tracer-bullet + W0.5 검증 게이트** |

---

## 2. 핵심 변경 사항 (vs 원본 spec)

| 항목 | 원본 spec | 변경 후 |
|---|---|---|
| Manager LLM | Gemma 3n E4B (`gemma3n:e4b`) | **qwen3.5:9b (Q4_K_M 기본 quant, ~6.6GB, 256K context, multimodal)**, Gemma는 백업 |
| Worker 실행 | Phase 1 `claude -p` headless → Phase 2 cmux | **OMC + cmux 조합** |
| 동시 작업 수 | 2~3 | **1~2** (메모리 제약) |
| OMC `ulw` 병렬 캡 | (해당 없음) | **2~3** (기본 5에서 캡) |
| Workflow 노드 | `generate_plan`, `retry_loop` 등 Manager 부담 | `generate_plan`/`retry_loop` 제거, **OMC `autopilot:`로 위임** |
| 로드맵 | Layer-by-layer (Manager → Worker → PR ...) | **Tracer-bullet** (W1에 E2E 가는 라인 먼저) |
| dev-wiki | (없음) | **`wiki/` in-repo로 신설**, 빌드 노하우 누적 |

---

## 3. Manager ↔ OMC 책임 분담 (Hybrid C)

| 책임 | 담당 | 비고 |
|---|---|---|
| 이슈 fetch + 한국어 의도 파악 | Manager | Korean 영역 |
| 정보 충분성 1차 판단 (한국어 측) | Manager | JSON schema 강제로 9B 약점 보완 |
| Worker용 영문 prompt 빌드 + wiki retrieve | Manager | task type에 따라 `autopilot:` / `ralph:` / raw prompt 선택 |
| 계획 분해 (영문 측) | OMC | `autopilot:` 또는 `/deepinit` |
| 코드 작성 / 실행 / 테스트 | OMC | executor + verifier |
| 실행 중 모호함 발생 시 추가 질문 | OMC `/deep-interview` | Manager가 한국어로 옮겨 Discord 전달, 응답 inject |
| 재시도 | OMC | verifier 루프 |
| diff 캡처 + 한국어 요약 | Manager | cmux capture-pane 후 가공 |
| 코드 / PR 2단계 승인 게이트 | Manager | spec L2 자율성 유지 |
| 가드레일 (토큰, turn 카운트) | Manager | OMC 모델 라우팅과 별도 카운팅 |
| PR 생성 (`gh` CLI) | Manager | OMC가 임의로 push 못 하게 차단 |
| wiki distill | Manager | 한국어 요약 → 타겟 repo wiki에 append |

핵심 원칙:

> **OMC는 코드 작성/테스트까지만 책임진다. PR 생성 권한은 없고, 가드레일은 외부 (Manager) 에서 강제한다.**

---

## 4. 메모리 현실 (Mac Mini M4 16GB)

| 항목 | 점유 (추정) | 실측 (2026-05-30) |
|---|---|---|
| macOS baseline | 4~5GB | — |
| Ollama + qwen3.5:9b (Q4_K_M loaded) | ~~6.6GB~~ | **8.5GB** (6.6GB는 *디스크*, 로드 시 RAM 8.5GB @ ctx 4096) |
| Claude Code 세션 × 2 (OMC 활성) | ~1GB | — |
| LangGraph + FastAPI + SQLite + Discord bot | ~1GB | — |
| 여유 buffer | ~2GB | **모델 + 세션 1개에서 이미 free 105M, swapout 이력** |
| **합계** | **~15GB (빡빡)** | **binding constraint 확정** |

> 실측 출처: [wiki/phases/w0.5-validation.md](wiki/phases/w0.5-validation.md). 256K context는 명목 스펙 — 16GB에서 full로 채우면 KV 캐시가 초과하므로 **Manager 컨텍스트를 보수적으로 캡**해야 한다.

- ~~OMC `ulw` 5병렬 → +1.5GB~~ → **반증 (2026-05-30 실측)**: `ulw` subagent는 서버측 실행이라 로컬 RAM을 N배로 늘리지 않음. claude 워커는 ~213MB/개, +2 워커 시 free% 변동 없음. 메모리 리스크는 워커 수가 아니라 **모델 8.5GB + 데스크톱 앱**.
- 동시 task 1~2개 — 메모리 제약보다는 가드레일/추적성 관점에서 유지
- **Mac Mini에서 VSCode/GUI(Chrome 등) 앱 띄우지 않을 것** — 실측상 데스크톱 앱이 ~1~1.5GB 점유, 헤드리스 운영이 14GB 임계값 준수의 관건

---

## 5. wiki 뼈대 구조 (확정)

```
my-local-agent/
├── CLAUDE.md                          # generic behavioral (현재 그대로) + wiki/SCHEMA.md 포인터
├── README.md
├── work-plan.md                       # 이 문서
├── local-agent-server-spec.md         # 원본 spec — W0 실행 시 wiki/raw/로 이동
├── llm-wiki.md                        # llm-wiki 철학 — W0 실행 시 wiki/raw/로 이동
└── wiki/
    ├── SCHEMA.md                      # llm-wiki 스키마 + ingest/query/lint 규약 + ADR/glossary 형식
    ├── index.md                       # 카탈로그 (페이지 + 1줄 요약)
    ├── log.md                         # 시계열 (## [YYYY-MM-DD] {ingest|decision|query|lint|phase} | <title>)
    ├── glossary.md                    # 도메인 용어 (Manager, Worker, OMC, magic keyword, L2, interrupt, ...)
    ├── raw/                           # immutable 원본
    │   ├── local-agent-server-spec.md
    │   ├── llm-wiki.md
    │   └── grilling/
    │       └── 2026-05-22-initial-grilling.md
    ├── decisions/                     # ADR (0001-<slug>.md 형식)
    │   ├── 0001-dev-wiki-as-bootstrap.md
    │   ├── 0002-omc-as-worker-runtime.md
    │   ├── 0003-hybrid-manager-omc-split.md
    │   ├── 0004-qwen3.5-9b-as-manager.md
    │   └── 0005-tracer-bullet-roadmap.md
    ├── concepts/                      # 개념별 페이지 (필요 시 점진 생성)
    ├── architecture/
    │   └── system-design.md           # 개정 spec — 항상 최신 상태
    └── phases/                        # W0, W0.5, W1...W7 작업 노트
        └── w0-bootstrap.md
```

---

## 6. CLAUDE.md 변경 사항

현재 [CLAUDE.md](CLAUDE.md)의 generic behavioral guidelines (Think Before Coding / Simplicity First / Surgical Changes / Goal-Driven Execution)는 **유지**한다. 맨 위에 다음 두 줄만 추가:

```markdown
> **이 repo는 llm-wiki 방식으로 운영됩니다. wiki 구조/규약/워크플로우는 [wiki/SCHEMA.md](wiki/SCHEMA.md) 참조.**
>
> **현재 시스템 설계는 [wiki/architecture/system-design.md](wiki/architecture/system-design.md). 원본 spec은 [wiki/raw/local-agent-server-spec.md](wiki/raw/local-agent-server-spec.md).**
```

---

## 7. W0 부트스트랩 (이번 주)

**산출물**: dev-wiki 뼈대 + ADR 5개 + 개정 spec + OMC/Qwen/cmux 설치 확인

### W0-1. wiki 디렉터리 생성 + raw 이동

- `wiki/` 및 하위 디렉터리 (`raw/`, `raw/grilling/`, `decisions/`, `concepts/`, `architecture/`, `phases/`) 생성
- `local-agent-server-spec.md`, `llm-wiki.md`를 `wiki/raw/`로 이동 (git mv)

### W0-2. `wiki/SCHEMA.md` 작성

들어갈 내용:
- wiki 디렉터리 구조 + 각 디렉터리의 역할
- **ingest 워크플로우**: 새 raw source 들어왔을 때 LLM이 따라야 할 단계 (read → discuss → summarize → index 업데이트 → 관련 페이지 업데이트 → log 항목 추가)
- **query 워크플로우**: 질문에 답할 때 어떤 순서로 wiki를 탐색하는지 (index.md 먼저 → 관련 페이지 drill → 인용 + 답변)
- **lint 워크플로우**: 주기적 점검 (contradiction, stale claim, orphan page, missing cross-reference)
- **log.md 항목 prefix 규약**: `## [YYYY-MM-DD] {ingest|decision|query|lint|phase} | <title>`
- **ADR 형식**: frontmatter (status, date, deciders, supersedes/superseded-by), 본문 (Context / Decision / Consequences / Alternatives considered)
- **glossary 형식**: `### 용어` + 정의 + 관련 용어 `[[link]]`

### W0-3. `wiki/glossary.md` 시드

이번 그릴링에서 정해진 용어:
- Manager / Worker
- dev-wiki / target-repo wiki
- OMC (oh-my-claude-code) / magic keyword (`autopilot:` / `ralph:` / `ulw` / `team` / `eco:`)
- Hybrid (C) 책임 분담
- L2 자율성 (코드 + PR 2단계 승인)
- interrupt #1 (정보 부족) / #2 (코드 승인) / #3 (PR 승인)
- cmux send/send-key / capture-pane
- 가드레일 (일일 $20, 작업당 turn 50)
- worktree
- `/deepinit` / `/deep-interview` / `/omc-doctor`

### W0-4. ADR 5개 작성

| 번호 | 제목 | 핵심 |
|---|---|---|
| 0001 | `dev-wiki-as-bootstrap.md` | 프로젝트 시작 시 dev-wiki를 함께 구축. 빌드 자체가 wiki ingest 대상 |
| 0002 | `omc-as-worker-runtime.md` | Worker 실행을 OMC + cmux 조합으로 통일 |
| 0003 | `hybrid-manager-omc-split.md` | Manager는 한국어/승인/가드레일, OMC는 영문 코딩 작업 전체 |
| 0004 | `qwen3.5-9b-as-manager.md` | qwen3.5:9b (Q4_K_M)를 Manager LLM으로 채택, Gemma 3n E4B는 백업 |
| 0005 | `tracer-bullet-roadmap.md` | Layer-by-layer 대신 Tracer-bullet + W0.5 검증 게이트 |

각 ADR 본문: Context (배경) / Decision (결정) / Consequences (영향) / Alternatives considered (대안) / Status (Accepted).

### W0-5. `wiki/architecture/system-design.md` (개정 spec) 작성

원본 spec section 1~12을 기반으로:
- **section 1 (인프라)**: Manager LLM → qwen3.5:9b, Worker → OMC+cmux 반영
- **section 2 (워크플로우)**: `generate_plan` / `retry_loop` 노드 제거, OMC autopilot 통합 노드 추가
- **section 4 (격리)**: cmux 언급 제거, cmux 세션 라이프사이클 명시
- **section 6 (llm-wiki)**: dev-wiki와 target-repo wiki 구분 명시
- **section 9 (로드맵)**: Tracer-bullet 로드맵으로 교체
- **section 10 (의사결정 기록)**: ADR로 이동, 본문에는 한 줄 요약 + ADR 링크만
- **section 11 (리스크)**: OMC 통합 리스크 추가 (메모리, send/send-key 안정성, 모델 라우팅), 메모리 수치 갱신

### W0-6. `wiki/raw/grilling/2026-05-22-initial-grilling.md` 작성

오늘 그릴링 8개 질문/답변의 압축본. 미래에 "왜 이렇게 결정했나" 추적용.

### W0-7. `wiki/index.md` + `wiki/log.md` 초기화

`index.md`: 카탈로그 (SCHEMA / glossary / raw 목록 / ADR 목록 / architecture / phases)
`log.md`: 첫 항목 — `## [2026-05-22] bootstrap | dev-wiki 뼈대 구축 + ADR 5개 시딩`

### W0-8. CLAUDE.md 최소 수정

위 6번 항목대로 2줄 추가.

### W0-9. 환경 셋업 (사용자 손 필요)

- Ollama 설치 확인 (`ollama --version`)
- qwen3.5:9b 다운로드 — `ollama pull qwen3.5:9b` (Q4_K_M 기본 quant, ~6.6GB)
- OMC 설치:
  - `/plugin marketplace add https://github.com/Yeachan-Heo/oh-my-claudecode`
  - `/plugin install oh-my-claudecode`
  - `/oh-my-claudecode:omc-setup`
- `/omc-doctor` 통과 확인
- cmux 설치 확인 (`cmux -V`)

---

## 8. W0.5 검증 게이트 (W0 직후 1~2일)

**목적**: 코드 작성 들어가기 전에 OMC/cmux/Qwen 조합이 Mac Mini에서 실제로 돌아가는지 결판.

### 측정 항목

| 항목 | 방법 | 기준 |
|---|---|---|
| 메모리 peak | Activity Monitor + `top` | < 14GB (wiki 정본 임계값) |
| OMC `autopilot:` 단발 호출 | 새 worktree에서 `claude` 띄우고 `autopilot: hello world 함수 추가` | 1회 성공 |
| cmux 통신 round-trip | Python 스크립트로 `new-workspace --focus false` → `send`+`send-key` → 5초 대기 → `capture-pane` | 100회 중 실패 ≤ 1% |
| OMC `ulw` 2~3 동시성 | `ulw` 2병렬 실행 후 메모리/CPU 측정 | OOM/스왑 없음 |
| 모델 라우팅 | `eco:` 키워드 사용 시 모델 라우팅 로그 확인 | 의도대로 haiku 라우팅 |

### Go 기준
세 가지 모두 충족:
1. 메모리 peak < 14GB
2. send/send-key/capture-pane 안정 (≥ 99% 성공)
3. `ulw` 2 동시 통과

### No-go 시 fallback
- **메모리 문제만**: qwen3.5:9b → Gemma 3n E4B로 다운그레이드
- **OMC 통신 불안정**: spec 원래 경로로 회귀 — Phase 1 `claude -p` headless로 W1 시작, OMC는 W6+로 미룸
- **둘 다 문제**: 동시성 1로 축소 + Gemma + headless

### W0.5 산출물
- `wiki/decisions/0007-omc-validation-result.md` — 결과 ADR (Accepted/Rejected/Modified). ADR 0006은 시스템 범위 정의로 선점됨
- `wiki/phases/w0.5-validation.md` — 측정 데이터 표, 스크린샷 경로, 결정 근거

---

## 9. W1~W7 로드맵 (Tracer-bullet)

| 주 | Phase | 산출물 | 핵심 작업 조각 |
|---|---|---|---|
| **W1** | E2E 스파이크 | Discord msg → 하드코딩 영문 prompt → cmux OMC → diff 한국어 출력 (PR/승인/가드레일 없음) | (1) Discord bot mention 수신, (2) cmux 세션 spawn 헬퍼, (3) OMC `send`/`send-key` + capture-pane 래퍼, (4) diff 캡처 → Qwen 한국어 요약, (5) Discord thread에 결과 포스팅 |
| **W2** | Manager 두뇌화 | 이슈 fetch + 한국어 의도 파싱 + 영문 prompt 빌드 | (1) GitHub API로 이슈 fetch, (2) LangGraph minimal (parse_issue → build_prompt), (3) 정보 충분성 JSON schema, (4) 기존 E2E에 인서트 |
| **W3** | interrupt | checkpointer (SQLite) + interrupt #1 (정보 부족 시 추가 질문) | (1) SQLite checkpointer 도입, (2) `interrupt()` + resume, (3) Discord thread reply → resume 매핑 |
| **W4** | 승인 게이트 | interrupt #2 (코드) + #3 (PR) | (1) diff 한국어 요약 + 승인 요청 메시지, (2) reaction/reply로 승인 캡처, (3) PR 승인 분리 |
| **W5** | PR + 가드레일 | `gh` CLI 래핑 + 토큰/turn 카운터 + 금지 작업 환경 차단 | (1) PR 생성 함수, (2) 토큰 카운터 (Anthropic API metering) + 일일 리셋 (UTC), (3) turn 카운터, (4) worktree env에서 `.env`/DB/결제 키 제외 |
| **W6** | wiki distill + 대시보드 | **target-repo용** wiki (dev-wiki와 별개) + HTML 대시보드 v1 | (1) `distill_to_wiki` 노드, (2) Obsidian Vault 경로 통합 (또는 in-repo 경로 확정), (3) grep retrieve, (4) FastAPI + Jinja2/HTMX `/dashboard` |
| **W7** | 운영 안정화 | 동시 task 1~2 검증, FIFO 큐, 실패 패턴 분석 | (1) 작업 큐, (2) 동시성 락, (3) 실패 ingest → wiki, (4) 알림 정책 튜닝 |

각 phase 종료 시:
- `wiki/log.md`에 `## [YYYY-MM-DD] phase | W<n> complete` 항목
- `wiki/phases/w<n>.md`에 했던 일 + 흔들렸던 가정 + 다음 phase로 넘어가는 의문점 정리
- 비싸게 되돌릴 결정이 있었으면 ADR 추가

---

## 10. 리스크 (갱신)

### High
- **qwen3.5:9b의 tool calling/JSON 일관성** — 9B Q4_K_M은 명백히 작음. JSON schema 강제 + 체크리스트 기반 출력으로 완화. 그래도 흔들리면 W0.5 결과에 따라 Gemma 3n E4B fallback
- **Mac Mini 16GB 메모리** — qwen3.5:9b + OMC 다중 세션 + cmux + macOS = ~15GB. peak에서 스왑 가능성. W0.5에서 실측 + 동시성 축소
- **OMC `autopilot:` / `ralph:`가 L2 자율성과 충돌** — OMC가 자체적으로 PR까지 가버리는 시나리오 차단 필요. worktree env에서 `gh` CLI 제거, Manager만 PR 생성

### Medium
- **OMC cmux 통신 (send/send-key/capture-pane) 안정성** — 검증되지 않음. W0.5에서 100회 round-trip 테스트로 결판
- **OMC `/deep-interview` ↔ Manager interrupt #1 매핑** — OMC가 영문으로 물으면 Manager가 한국어로 옮겨 Discord 전달 → 응답 받아 inject. 이 round-trip이 매끄럽게 동작하는지는 W3에서 검증
- **가드레일 카운팅 정확도** — OMC는 자체 모델 라우팅 (haiku/sonnet/opus)을 하므로 토큰 비용 추정이 복잡. Anthropic API metering API 사용 또는 OMC `/trace` 출력 파싱

### Low
- **dev-wiki vs target-repo wiki 혼선** — 같은 "wiki" 단어를 다른 의미로 씀. SCHEMA.md + glossary.md에서 명시적으로 구분
- **launchd 시작 순서** — Ollama 먼저, FastAPI 둘째, Discord bot 마지막. 첫 실패 시 KeepAlive로 재시작 (spec 그대로)

---

## 11. 다음 행동

1. **이 문서 확정** — 빠진 부분, 틀린 부분, 다른 방향 검토
2. **W0 실행 시작** — 위 W0-1 ~ W0-8을 순서대로 실행. wiki 뼈대 + SCHEMA + glossary + ADR 5개 + 개정 system-design을 한 번에 생성
3. **W0-9 환경 셋업** — Qwen pull, OMC 설치는 사용자 손이 필요
4. **W0.5 검증** — Mac Mini에서 손으로 측정 후 ADR 0007 작성 (ADR 0006은 시스템 범위 정의로 사용됨)
5. **W1 진입** — E2E 스파이크 시작
