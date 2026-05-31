# 시스템 설계 (개정 spec)

> 원본 spec `wiki/raw/local-agent-server-spec.md` 의 개정본. 항상 최신 상태로 유지된다.
> 그릴링 결과 (`wiki/raw/grilling/2026-05-22-initial-grilling.md`) 와 ADR 0001~0005 를 반영한다.
> 원본 spec과 충돌하는 부분은 본문에서 ADR 링크로 정당화된다.
>
> *Last updated: 2026-05-25*

---

## 0. 배경 및 목표

### 시스템 정의

> "하나의 깃허브 레포지토리를 작업 공간으로 추적하는 로컬 에이전트 서버 기반의 에이전트 매니징 시스템" (2026-05-25 확정)

1.0 시스템 범위는 단일 GitHub repo 로 한정 ([[ADR 0006]]). 검증 (W0~W7) 완료 후 multi-repo 확장 도모. Discord 채널, [[worktree]], [[target-repo wiki]] distill 대상 모두 1개 repo 기준. 사용자가 동시에 여러 repo를 다루려면 1.0 에서는 별도 인스턴스를 띄워야 한다.

### 문제 상황

- 회사 업무 외 개인 프로젝트 진행할 시간/여유 부족
- Claude Code 토큰이 현재 작업량 대비 잉여 상태
- Mac Mini가 유휴 상태
- 하고 싶은 작업은 많지만 직접 코딩할 여유가 없음

### 목표

- Mac Mini에서 24/7 로컬 에이전트 구동
- Discord 한국어 지시 → 로컬 [[Manager]] 가 [[OMC]] (Claude Code 플러그인) 을 조작 → E2E 개발 진행 → 결과 한국어 보고 → 승인 후 GitHub PR 생성
- Agent-to-Agent: 로컬 LLM이 "한국어 판단/조율/가드레일", [[OMC]] 가 "영문 코드 작성/테스트 실행" 담당. 자세한 책임 분담은 [[ADR 0003]] 참조.

### 부수 목표 (개정 사항)

- 빌드 과정의 노하우를 즉시 누적할 [[dev-wiki]] 구축 ([[ADR 0001]])
- 개발자와 [[Worker]] 가 동일 도구 스택 ([[OMC]] + [[cmux]]) 사용 ([[ADR 0002]])

---

## 1. 시스템 구성

```
[Discord]
   ↕  자연어 한국어
[Manager Agent] ── qwen3.5:9b (Q4_K_M, 6.6GB, 256K context, multimodal) via Ollama (24/7 daemon)
   │  · 한국어 의도 파악, 정보 충분성 판단
   │  · 영문 prompt 빌드, 결과 한국어 요약
   │  · 승인 게이트 / 가드레일 / PR 생성 권한
   ↓  영문 prompt + magic keyword
[Worker Agent] ── OMC (oh-my-claudecode) + cmux pane
   │  · autopilot:/ralph:/ulw 자동 분기
   │  · 코드 작성/실행/테스트 (E2E)
   │  · /deep-interview 로 interrupt #1 트리거
   ↓  diff
[Manager 한국어 요약] → [interrupt #2 코드 승인] → [interrupt #3 PR 승인] → [gh CLI PR 생성]
```

### 인프라 결정

| 항목 | 결정 | 근거 |
|---|---|---|
| 하드웨어 | Mac Mini M4 16GB | 원본 spec 유지 |
| **Manager LLM** | **`qwen3.5:9b`** (Q4_K_M 기본 quant, 6.6GB, 256K context, multimodal) | [[ADR 0004]] — Gemma 3n E4B 대비 한국어 / JSON 일관성 우위. Gemma는 fallback |
| **Worker runtime** | **[[OMC]] + [[cmux]] 조합** (W1부터 즉시) | [[ADR 0002]] — 원본 spec 의 Phase 1 (`claude -p` headless) → Phase 2 cmux 점진 도입 폐기. W0.5 검증 게이트 통과 전제 |
| LLM 런타임 | Ollama | 원본 spec 유지 |
| 오케스트레이션 | LangGraph + FastAPI | 원본 spec 유지 |
| 영속화 | SQLite (LangGraph Checkpointer + 작업 이력) | 원본 spec 유지 |
| 네트워크 | 로컬 only | Discord 봇만 outbound |
| 24/7 구동 | launchd (3개 프로세스) | ollama, fastapi, discord bot |
| **개발자 환경** | [[OMC]] + [[cmux]] | [[ADR 0002]] — 개발자와 Worker 가 동일 도구 스택 ([[Hybrid 책임 분담]]) |

> Manager LLM 변경 근거 ([[ADR 0004]]): 9B 모델의 한국어 의도 파싱과 JSON 도구 호출 일관성이 [[Manager]] 핵심 책임에 더 적합하다. 256K context 는 [[interrupt #1]] 왕복과 wiki retrieve 결과 첨부에 여유를 준다. multimodal 은 향후 스크린샷 첨부 이슈 처리 여지를 열어 둔다.

### 레이어 분리 원칙

| 레이어 | 책임 |
|---|---|
| **FastAPI** | HTTP I/O, 인증/권한, 요청 검증, 백그라운드 태스크 트리거 |
| **LangGraph** | 에이전트 추론, 상태 전이, [[Manager]] LLM 호출, interrupt 게이트, 가드레일 집행 |
| **OMC orchestrator** | [[cmux]] 세션 spawn, `send`/`send-key`/`capture-pane` 래핑, [[magic keyword]] 분기 |
| **Discord Bot** | 사용자 인터페이스, thread 관리 (별도 프로세스) |

> FastAPI 에 LLM 코드 없음, LangGraph 에 HTTP 코드 없음, OMC orchestrator 는 LangGraph 의 한 tool 로 wrap → 테스트/유지보수 용이.

---

## 2. 워크플로우 (LangGraph)

### 노드 그래프 (개정)

```
[GitHub Issue 링크 수신 (Discord)]
    ↓
[parse_issue]            — 이슈 fetch + 본문 파싱 (Manager)
    ↓
[assess_sufficiency]     — 정보 충분성 JSON 판단 (Manager, JSON schema 강제)
    ↓
[interrupt #1]           — 정보 부족 시만, Discord thread 자유 응답 ─┐
    ↓                                                                 │ 충분해질 때까지 루프
[build_prompt]           — OMC용 영문 prompt + wiki retrieve (Manager)
    ↓
[invoke_omc_autopilot]   — cmux pane 에서 OMC autopilot:/ralph:/ulw 실행
    ↓                      (계획 분해 + 코드 작성 + 테스트 + 재시도 모두 OMC 내부)
[capture_diff]           — cmux capture-pane 으로 diff 수집 (Manager)
    ↓
[summarize_diff]         — 한국어 변경 파일 + diff 요약 (Manager)
    ↓
[interrupt #2]           — 코드 결과 승인 게이트
    ↓
[interrupt #3]           — PR 생성 승인 게이트
    ↓
[create_pr]              — Manager 가 gh CLI 로 PR 생성 (OMC 권한 없음)
    ↓
[distill_to_wiki]        — target-repo wiki append (Manager)
    ↓
END
```

### 원본 spec 대비 변경

| 변경 | 근거 |
|---|---|
| `generate_plan` 노드 **제거** | [[OMC]] 의 `autopilot:` 키워드가 계획 분해를 내장. [[Manager]] 가 계획을 다시 짤 필요 없음 ([[ADR 0003]]) |
| `retry_loop` 노드 **제거** | [[OMC]] 내부의 `ralph:`/`ultraqa:` verifier 루프가 자율 재시도. [[Manager]] 는 외부 가드레일 (turn cap) 만 집행 ([[ADR 0003]]) |
| `invoke_claude_code` → **`invoke_omc_autopilot`** 으로 통합 | [[Worker]] 호출이 단일 magic keyword 기반 ([[ADR 0002]]) |
| `assess_sufficiency` 노드 **추가** | 9B Manager 의 JSON 일관성 약점 보완 — 별도 노드로 JSON schema 강제 ([[ADR 0004]]) |

### 한국어 / 영문 round-trip

[[ADR 0003]] 의 Hybrid 책임 분담에 따라 round-trip 은 다음과 같이 흐른다.

```
사용자 한국어 (Discord)
    → Manager 한국어 의도 파악
    → Manager 영문 prompt 빌드 (task type → autopilot:/ralph:/ulw 선택)
    → OMC 영문 실행
        → (OMC 모호함 발견) /deep-interview 한국어 질문 생성 ── interrupt #1
            → Manager 가 Discord 로 전달 → 사용자 한국어 응답 → Manager 가 영문으로 옮겨 resume
        → OMC 코드 작성 / 테스트 / verifier 루프
    → Manager diff 영문 → 한국어 요약 (interrupt #2)
    → 사용자 승인 → Manager PR 승인 요청 (interrupt #3)
    → 사용자 승인 → Manager gh CLI PR 생성
```

> [[OMC]] 의 `/deep-interview` 와 [[Manager]] 의 [[interrupt #1]] 간 매핑은 [[W3]] 에서 별도 검증한다 ([[ADR 0003]] Consequences 참조).

### 자율성 레벨: [[L2 자율성]]

- 2단계 승인 ([[interrupt #2]] 코드 + [[interrupt #3]] PR)
- 정보 부족 시 [[interrupt #1]] 발동 (총 최대 3개 interrupt)
- [[OMC]] 자율 루프 (`autopilot:`/`ralph:`) 는 코드 작성 / 테스트까지만 허용. PR 생성 권한 없음 ([[ADR 0003]])

---

## 3. Manager / Worker 책임 분담

[[ADR 0003]] (Hybrid C) 의 책임 분담을 그대로 인용한다.

### Manager 담당 영역

| 책임 | 세부 내용 |
|------|-----------|
| 이슈 fetch | GitHub issue 를 가져와 한국어 의도 파악 |
| 정보 충분성 판단 | 작업 착수 가능 여부를 한국어로 1차 판단 (JSON schema 강제) |
| 영문 prompt 빌드 | [[OMC]] 에 전달할 영문 작업 명세 구성. task type 에 따라 `autopilot:` / `ralph:` / raw prompt 선택 |
| wiki retrieve | [[dev-wiki]] 또는 [[target-repo wiki]] 에서 관련 항목 grep 후 prompt 첨부 |
| 2단계 승인 게이트 | [[interrupt #2]] (코드 승인) + [[interrupt #3]] (PR 승인) |
| 가드레일 집행 | [[일일 토큰 cap]], [[작업당 turn cap]] 외부 강제 |
| diff 한국어 요약 | OMC 결과물을 한국어로 사용자에게 설명 |
| PR 생성 | 승인 후 `gh` CLI 로 PR 생성 — OMC 에는 이 권한 없음 |
| wiki distill | 작업 완료 후 [[target-repo wiki]] 갱신 |

### OMC (Worker) 담당 영역

| 책임 | 세부 내용 |
|------|-----------|
| 영문 계획 분해 | `autopilot:` magic keyword 또는 `/deepinit` 으로 계획 생성 |
| 코드 작성 / 실행 / 테스트 | Worker 역할 전체 — 멀티 파일 변경, 빌드, 테스트 포함 |
| 모호함 발생 시 추가 질문 | `/deep-interview` 를 통해 [[interrupt #1]] 트리거 |
| 재시도 | verifier 루프 (`ralph:` / `ultraqa:`) 로 자율 수정 |

### 핵심 원칙

> [[OMC]] 는 코드 작성/테스트까지만 책임진다. PR 생성 권한은 없고, 가드레일은 외부 ([[Manager]]) 에서 강제한다.

### task type 별 magic keyword 라우팅 (Manager 가 결정)

| task type | 선택 키워드 | 근거 |
|---|---|---|
| 단순 기능 추가 / 버그 수정 | `autopilot:` | 계획 분해 + 실행 + 검증 자동 |
| 복잡한 리팩토링 / 다중 파일 | `ralph:` | 자율 루프, verifier 강함 |
| 독립 병렬 가능 작업 (여러 파일) | `ulw` (병렬 캡 2~3) | 메모리 제약 (Mac Mini 16GB) |
| 비용 절감 우선 (단순 lint/format) | `eco:` (token-efficient 모드) | 토큰 절약 (haiku 고정 아님 — W1 검증, 아래 주석) |
| 다중 에이전트 협력 필요 | `team` | 특수 케이스 |

---

## 4. 격리 + 안전장치

### 환경 격리

- **git [[worktree]]** 작업당 1개 (동일 repo 다중 복제)
- 동시 작업 **1~2개** (원본 spec 의 2~3개에서 축소) — Mac Mini 16GB 메모리 제약 ([[ADR 0004]])
- 초과 시 FIFO 큐 + 대기 알림

### [[cmux]] 세션 라이프사이클

[[ADR 0002]] 에 따라 [[Worker]] 는 [[cmux]] pane 에서 실행된다.

| 단계 | 행동 |
|---|---|
| spawn | 작업 시작 시 [[Manager]] 가 `cmux new-workspace --name task-<id> --focus false` 로 detached session 생성 |
| attach worktree | 해당 session 의 cwd 를 worktree 경로로 설정 (`send`+`send-key` 로 `cd <worktree>`) |
| 환경 가드레일 | `.env` 차단 + `gh` CLI 차단 — worktree env 에서 PATH 조작 또는 wrapper script 로 처리 |
| 작업 실행 | `send`+`send-key` 로 `claude` 띄우고 magic keyword 전송 |
| 출력 수집 | `capture-pane` 로 결과 / diff / interrupt 신호 수집 |
| 종료 | 작업 완료 또는 `/cancel` → SIGTERM → 5초 후 SIGKILL → `cmux kill-session` → worktree 정리 |

### 금지 작업 (다층 방어)

| 금지 항목 | 차단 메커니즘 |
|---|---|
| `main`/`master` 직접 push | GitHub branch protection |
| Force push, branch 삭제 | OMC allowed tools 에서 `git push --force`, `git branch -D` 차단 |
| `.env` 접근, 비밀값 수정 | worktree 에 `.env` 미복사 (또는 dummy 로 대체) |
| DB 마이그레이션 / 스키마 변경 | worktree env 에 DB 접속정보 미주입 |
| 외부 API 결제/과금 호출 | 결제 API 키 worktree env 에 미주입 |
| **`gh` CLI 호출 ([[OMC]] 측)** | **worktree env 의 `PATH` 에서 `gh` 차단 또는 wrapper 로 에러 반환.** PR 생성 권한은 [[Manager]] 만 보유 ([[ADR 0003]]) |

> 시스템 prompt 만으로는 우회 가능. 환경 자체에서 원천 차단해야 안전. [[OMC]] 의 `autopilot:`/`ralph:` 루프가 자체적으로 PR 까지 가버리는 시나리오를 막는 핵심 가드 ([[ADR 0002]] Consequences).

### 취소

- `/cancel <task_id>` → SIGTERM (graceful) → 5초 후 SIGKILL → `cmux kill-session` → worktree 정리

---

## 5. Discord 인터랙션 + interrupt 시점

### 트리거

- 사용자가 GitHub Issue 링크를 Discord 에 게시 → 봇이 자동 감지
- 봇이 작업 thread 생성 → 이후 모든 통신은 thread 안에서 (`task_id` ↔ thread 매핑)

### interrupt 3종 시점

| interrupt | 시점 | 트리거 | 사용자 응답 방식 |
|---|---|---|---|
| **[[interrupt #1]]** | `assess_sufficiency` 노드 정보 부족 OR [[OMC]] 가 `/deep-interview` 호출 | [[Manager]] 가 한국어 질문 Discord 포스팅 | thread reply 자유 응답 → Manager 가 영문으로 옮겨 LangGraph resume |
| **[[interrupt #2]]** | `summarize_diff` 노드 완료 후 | [[Manager]] 가 diff 한국어 요약 + 승인 요청 포스팅 | reaction (✅/❌) 또는 thread reply 로 승인/거부 |
| **[[interrupt #3]]** | `interrupt #2` 승인 직후 | [[Manager]] 가 PR 생성 승인 요청 포스팅 | reaction (✅/❌) 또는 thread reply |

### [[OMC]] `/deep-interview` ↔ Manager `interrupt #1` round-trip

[[ADR 0003]] Consequences 의 명시된 round-trip:

1. [[OMC]] 가 실행 중 모호함 발견 → `/deep-interview` 로 영문 질문 생성 (`cmux capture-pane` 으로 [[Manager]] 가 감지)
2. [[Manager]] 가 영문 질문을 한국어로 옮겨 Discord thread 에 포스팅
3. 사용자가 한국어로 응답 → [[Manager]] 가 영문으로 다시 옮겨 `send`+`send-key` 로 [[OMC]] 에 inject
4. [[OMC]] 가 작업 재개

> 이 round-trip 의 안정성은 [[W3]] 에서 별도 검증한다.

### 알림 정책 (조용함)

| 단계 | 알림 | 멘션 |
|---|---|---|
| 작업 시작 | O | X |
| 정보 부족 추가 질문 (interrupt #1) | O | O |
| 코드 승인 요청 (interrupt #2) | O | O |
| PR 승인 요청 (interrupt #3) | O | O |
| 완료 | O | X |
| 실패 | O | O |
| 가드레일 초과 | O | O |
| 진행 중 단계 알림 | X | X |

### 명령

- `/cancel <task_id>` — 작업 취소
- `/tasks` — 현재 작업 목록
- `/status <task_id>` — 상태 조회

### Manager 한국어 보고 형식

- 변경 파일 목록 + diff 요약 (한국어)
- 변경 의도 (왜 이렇게 짰는지) 한국어 설명
- 코드 승인 요청 시 함께 제시

---

## 6. 컨텍스트 학습 ([[llm-wiki]] 두 갈래)

[[ADR 0001]] 에 따라 wiki 는 두 갈래로 운영된다.

### [[dev-wiki]] (in-repo)

- **위치**: 이 repo 의 `wiki/` 디렉터리
- **목적**: 에이전트 서버 자체를 빌드하는 과정에서 얻은 결정 / 실패 패턴 / 기술 선택 누적
- **소유자**: 모든 LLM 세션이 [[SCHEMA.md]] 에 정의된 ingest/query/lint 워크플로우 준수
- **누적 방식**: 새 raw source 가 `wiki/raw/` 에 추가될 때마다 LLM 이 read → discuss → summarize → index 업데이트 → 관련 페이지 갱신 → log 기록
- **버전 관리**: git 으로 commit, repo 와 함께 진화

### [[target-repo wiki]] (외부 target 저장소)

- **위치**: 작업 대상 외부 repo 의 wiki (또는 Obsidian Vault PARA `Resources/agent-wiki/<repo>/`)
- **목적**: [[Manager]] 가 작업 완료 시 distill 한 안정화된 노하우. 사용자 개인 자산으로 누적, repo 에 commit 하지 않음
- **누적 방식**: PR 완료 시 `distill_to_wiki` 노드가 마크다운 자동 append. 기록 내용: 작업 요약 / 결정 이유 / 마주친 함정 / 코드 패턴
- **Worker prompt 주입**: `build_prompt` 노드에서 관련 wiki 항목 retrieve → [[OMC]] prompt 에 컨텍스트로 첨부

### 두 갈래의 구분 ([[ADR 0001]])

> [[dev-wiki]] 는 빌드 단계에서 결정/노하우를 즉각 ingest 한다. [[target-repo wiki]] 는 안정화된 정보만 담아 사용자 혼동을 줄인다. 이 둘은 생명주기가 다르므로 분리한다.

### Retrieval 진화 경로

1. **초기 ([[W6]])**: grep 기반
2. **다음 단계**: SQLite FTS5
3. **필요 시**: embedding + vector search

---

## 7. 가드레일 (이중 구조)

| 범위 | 한도 | 초과 시 |
|---|---|---|
| **일일** | 총 토큰 비용 $20 (UTC 자정 리셋) | 신규 작업 거절, 진행 중은 유지 |
| **작업당** | [[OMC]] 외부 turn 50 ([[Manager]] 카운트) | 중단 + 사용자 보고 |
| **재시도** | OMC 내부 verifier 루프 자체 한도 + 외부 turn cap 으로 이중 차단 | 중단 + 사용자 보고 |

> [[일일 토큰 cap]] 과 [[작업당 turn cap]] 이 곱셈 폭주를 방지하는 핵심.

### [[OMC]] 모델 라우팅과 비용 추정 복잡성

[[ADR 0003]] Consequences 에서 명시된 리스크:

- [[OMC]] 는 자체 모델 라우팅 (haiku / sonnet / opus) 을 한다 — **단, 결정적 키워드→모델 테이블이 아니라 LLM(에이전트)이 작업 복잡도를 보고 `Task(..., model="haiku|sonnet|opus")` 로 명시 선택한다** (`ultrawork/SKILL.md`: simple→haiku, standard→sonnet, complex→opus). `eco:` 는 그 선택을 저렴한 쪽으로 편향시키는 **token-efficient 모드**일 뿐 haiku 고정이 아니다. (W1 검증 — [[ADR 0007]] Addendum)
- → 비용 추정이 더 복잡하다: 모델 선택이 비결정적(LLM 판단)이므로 사전 예측 불가, **실제 spawn된 model을 사후 관측**해야 한다 (`/trace` 파싱 또는 PostToolUse hook). 정적 "eco=haiku" 가정으로 비용을 추정하면 틀린다.
- [[Manager]] 가 외부에서 turn 만 세면 실제 토큰 비용을 정확히 알 수 없음
- 비용 추정 옵션:
  1. **Anthropic API metering** — 공식 usage API 호출로 실제 사용량 조회
  2. **`/trace` 출력 파싱** — OMC 의 `/trace` 명령어가 모델별 토큰을 출력. capture-pane 으로 파싱
  3. **OMC hook (PostToolUse)** — 모든 LLM 호출 후 usage 를 SQLite 에 기록

W5 에서 이 중 하나를 채택. 우선 (1) Anthropic API metering 을 시도하고, 실패 시 (2) 로 회귀.

---

## 8. 디렉터리 구조

```
~/agent-server/
├── app/                     FastAPI
│   ├── main.py
│   ├── routers/
│   │   ├── tasks.py
│   │   └── webhooks.py
│   ├── schemas/             Pydantic
│   ├── templates/           Jinja2 대시보드
│   └── deps.py
├── agent/                   LangGraph
│   ├── graph.py             그래프 빌더
│   ├── state.py             State TypedDict
│   ├── nodes/
│   │   ├── parse_issue.py
│   │   ├── assess_sufficiency.py
│   │   ├── build_prompt.py
│   │   ├── invoke_omc.py
│   │   ├── capture_diff.py
│   │   ├── summarize_diff.py
│   │   ├── create_pr.py
│   │   └── distiller.py
│   └── tools/
│       ├── cmux_wrapper.py  send/send-key/capture-pane 헬퍼
│       ├── omc_router.py    magic keyword 라우팅
│       └── gh_cli.py        PR 생성 (Manager 전용)
├── bot/                     Discord 봇 (별도 프로세스)
│   └── discord_client.py
├── worktrees/               git worktree 동적 생성/제거
├── data/
│   ├── checkpoints.sqlite   LangGraph 상태
│   └── tasks.sqlite         작업 이력
├── wiki/                    dev-wiki (이 repo 의 wiki/)
└── launchd/                 .plist 파일 3개
```

### API 엔드포인트

| Method | Path | 용도 |
|---|---|---|
| POST | `/tasks` | 새 작업 시작 (봇이 호출) |
| POST | `/tasks/{id}/approve` | 승인 게이트 응답 |
| GET | `/tasks/{id}/status` | 상태 조회 (snapshot.next, values) |
| GET | `/tasks/{id}/stream` | SSE 진행 스트리밍 (옵션) |
| GET | `/dashboard` | 웹 대시보드 |

### 옵저버빌리티

- **FastAPI 대시보드 v1**: Jinja2 + HTMX (가볍게). 작업 이력 / 상태 / diff / wiki 항목 통합 조회
- **로그**: 구조화 JSON → SQLite + stdout. 작업 이력 영속 저장 (재해 시 분석)
- **OMC 통합 로그**: `cmux capture-pane` 결과를 SQLite 에 영속화

---

## 9. 로드맵 ([[tracer-bullet 로드맵]])

[[ADR 0005]] 에 따라 원본 spec 의 Layer-by-layer 로드맵을 폐기하고 tracer-bullet 으로 교체한다.

### 핵심 패러다임

> 시스템을 관통하는 가는 E2E 라인 하나를 먼저 구현하고, 이후 라인 위에 두께를 더해 나간다.

### Phase 표

| 주차 | Phase | 산출물 | 핵심 작업 조각 |
|---|---|---|---|
| **[[W0]]** | 부트스트랩 | [[dev-wiki]] 뼈대 + ADR 0001~0005 + 개정 system-design + 환경 셋업 | (1) `wiki/` 디렉터리 + SCHEMA + glossary + index + log, (2) ADR 5개, (3) 이 문서, (4) Ollama + qwen3.5:9b pull, (5) [[OMC]] 설치 + `/omc-doctor` 통과, (6) [[cmux]] 설치 확인 |
| **[[W0.5]]** | 검증 게이트 | Go/No-go 결정 + ADR 0007 | (1) 메모리 peak < 14GB 측정, (2) `autopilot:` 단발 호출 성공, (3) [[cmux]] round-trip 100회 (실패율 ≤ 1%), (4) `ulw` 2 동시성 OOM 없음, (5) 모델 라우팅 정상 분기 |
| **[[W1]]** | E2E 스파이크 | Discord msg → 하드코딩 영문 prompt → cmux OMC → diff 한국어 출력 (PR/승인/가드레일 없음) | (1) Discord bot mention 수신, (2) [[cmux]] 세션 spawn 헬퍼, (3) [[OMC]] `send`/`send-key` + capture-pane 래퍼, (4) diff 캡처 → [[qwen3.5:9b]] 한국어 요약, (5) Discord thread 결과 포스팅 |
| **[[W2]]** | Manager 두뇌화 | 이슈 fetch + 한국어 의도 파싱 + 영문 prompt 빌드 | (1) GitHub API 이슈 fetch, (2) LangGraph minimal (parse_issue → build_prompt), (3) `assess_sufficiency` JSON schema, (4) 기존 E2E 에 인서트 |
| **[[W3]]** | interrupt + checkpointer | SQLite checkpointer + interrupt #1 (정보 부족 시 추가 질문) + OMC `/deep-interview` round-trip | (1) SQLite checkpointer 도입, (2) `interrupt()` + resume, (3) Discord thread reply → resume 매핑, (4) `/deep-interview` ↔ interrupt #1 매핑 검증 |
| **[[W4]]** | 승인 게이트 | interrupt #2 (코드) + interrupt #3 (PR) | (1) diff 한국어 요약 + 승인 요청 메시지, (2) reaction/reply 로 승인 캡처, (3) PR 승인 분리 |
| **[[W5]]** | PR + 가드레일 | `gh` CLI 래핑 + 토큰/turn 카운터 + 금지 작업 환경 차단 | (1) PR 생성 함수 (Manager 전용), (2) 토큰 카운터 (Anthropic API metering 우선) + 일일 리셋 (UTC), (3) turn 카운터, (4) worktree env 에서 `.env`/DB/결제 키/`gh` 제외 |
| **[[W6]]** | wiki distill + 대시보드 | [[target-repo wiki]] (dev-wiki 와 별개) + HTML 대시보드 v1 | (1) `distill_to_wiki` 노드, (2) Obsidian Vault 경로 통합 (또는 in-repo 경로 확정), (3) grep retrieve, (4) FastAPI + Jinja2/HTMX `/dashboard` |
| **[[W7]]** | 운영 안정화 | 동시 task 1~2 검증, FIFO 큐, 실패 패턴 분석 | (1) 작업 큐, (2) 동시성 락, (3) 실패 ingest → wiki, (4) 알림 정책 튜닝 |

### [[W0.5]] Go 기준

세 가지 모두 충족:

1. 메모리 peak < 14GB
2. `send`/`send-key`/`capture-pane` 안정 (≥ 99% 성공)
3. `ulw` 2 동시 통과

### No-go 시 fallback ([[ADR 0005]])

- **메모리만 문제** → [[qwen3.5:9b]] → [[Gemma 3n E4B]] 다운그레이드 ([[ADR 0004]] 일부 reverse)
- **[[OMC]] 통신 불안정** → `claude -p` headless 회귀 ([[ADR 0002]] 일부 reverse), [[OMC]] 는 [[W6]]+ 로 미룸
- **둘 다 문제** → 동시성 1 + Gemma + headless

---

## 10. 의사결정 기록

원본 spec section 10 의 grilling 결과를 ADR 로 이동. 본문에는 한 줄 요약 + 링크만 둔다.

| ADR | 제목 | 한 줄 요약 |
|---|---|---|
| [[ADR 0001]] ([wiki/decisions/0001-dev-wiki-as-bootstrap.md](../decisions/0001-dev-wiki-as-bootstrap.md)) | dev-wiki 를 부트스트랩 단계에 통합 | [[W0]] 시점부터 `wiki/` 에 결정/노하우 누적 시작 |
| [[ADR 0002]] ([wiki/decisions/0002-omc-as-worker-runtime.md](../decisions/0002-omc-as-worker-runtime.md)) | Worker 실행을 OMC + cmux 조합으로 통일 | 원본 spec 의 Phase 1 headless → Phase 2 cmux 점진 도입 폐기. [[W1]] 부터 [[OMC]] + [[cmux]] |
| [[ADR 0003]] ([wiki/decisions/0003-hybrid-manager-omc-split.md](../decisions/0003-hybrid-manager-omc-split.md)) | Manager / OMC Worker 간 Hybrid 책임 분담 | Manager 는 한국어/승인/가드레일, OMC 는 영문 코드 작업 전체 |
| [[ADR 0004]] ([wiki/decisions/0004-qwen3.5-9b-as-manager.md](../decisions/0004-qwen3.5-9b-as-manager.md)) | Manager LLM 으로 `qwen3.5:9b` 채택 | Gemma 3n E4B 대신 한국어/JSON 일관성 우위. Gemma 는 fallback |
| [[ADR 0005]] ([wiki/decisions/0005-tracer-bullet-roadmap.md](../decisions/0005-tracer-bullet-roadmap.md)) | Tracer-bullet 로드맵 + [[W0.5]] 검증 게이트 채택 | Layer-by-layer 대신 가는 E2E 라인 먼저, [[W0.5]] 에서 Go/No-go |

### 원본 spec 의 작업 범위 결정 (유지)

ADR 화되지 않은 작업 범위 결정은 원본 spec 그대로 유지한다.

- Repo: 1개 집중 (whitelist 단순화)
- 자율성: [[L2 자율성]] (코드 + PR 2단계 승인)
- 작업 유형: 기능 추가 / 버그 수정 / 리팩토링 / 문서화 / 라이브러리 업데이트 / 테스트 작성
- 트리거: GitHub Issue 링크
- 이슈 명세: 자유 형식, 부족 시 [[Manager]] 가 자유 응답으로 역질문 ([[interrupt #1]])
- 작업 범위: E2E (테스트 실행 통과까지)
- 격리: git [[worktree]]
- 가드레일: [[일일 토큰 cap]] $20 + [[작업당 turn cap]] 50
- 금지 작업: 5종 + `gh` CLI ([[OMC]] 측 차단)
- 알림: 조용함, 멘션은 실패/승인/초과 시만
- 일일 상한 도달: 신규 거절, 다음날까지 대기
- 큐: FIFO

---

## 11. 주요 리스크 및 주의사항 (갱신)

원본 spec section 11 에 [[OMC]] 통합 리스크와 [[qwen3.5:9b]] 메모리 수치 갱신을 반영한다.

### 메모리 현실 (Mac Mini M4 16GB, 갱신)

| 항목 | 점유 (추정) |
|---|---|
| macOS baseline | 4~5GB |
| Ollama + [[qwen3.5:9b]] (Q4_K_M loaded) | ~6.6GB |
| Claude Code 세션 × 2 ([[OMC]] 활성) | ~1GB |
| LangGraph + FastAPI + SQLite + Discord bot | ~1GB |
| 여유 buffer | ~2GB |
| **합계** | **~15GB (빡빡)** |

> 원본 spec 의 Gemma (~3GB) 대비 [[qwen3.5:9b]] 가 6.6GB 로 약 3.6GB 더 점유. 동시 작업을 2~3 에서 1~2 로 축소 ([[ADR 0004]]).

### High

- **[[qwen3.5:9b]] 의 tool calling / JSON 출력 일관성** — 9B Q4_K_M 은 명백히 작음. JSON schema 강제 + 체크리스트 기반 출력으로 완화. 그래도 흔들리면 [[W0.5]] 결과에 따라 [[Gemma 3n E4B]] fallback ([[ADR 0004]]). **[W0.5 측정: 구조 100% / 의미 93% PASS]** — 단 "JSON schema 강제"는 ollama `format`이 아니라 **프롬프트 구조 명시 + 코드 검증**으로 구현 (ollama format 미강제 확인, [[w0.5-validation]])
- **Mac Mini 16GB 메모리 한계** — [[qwen3.5:9b]] (6.6GB) + [[OMC]] 다중 세션 + [[cmux]] + macOS = ~15GB. peak 에서 스왑 가능성. [[W0.5]] 에서 실측 + 동시성 축소
- **[[OMC]] `autopilot:` / `ralph:` 가 [[L2 자율성]] 과 충돌** — [[OMC]] 가 자체적으로 PR 까지 가버리는 시나리오 차단 필요. worktree env 에서 `gh` CLI 제거, [[Manager]] 만 PR 생성 ([[ADR 0002]] Consequences, [[ADR 0003]])
- **자유 형식 이슈 → 의도 파싱 부담** — [[Manager]] 시스템 prompt 설계가 시스템 품질의 80% 좌우

### Medium

- **[[cmux]] 통신 (`send`/`send-key`/`capture-pane`) 안정성** — 검증되지 않음. [[W0.5]] 에서 100회 round-trip 테스트로 결판 ([[ADR 0005]])
- **[[OMC]] `/deep-interview` ↔ [[Manager]] [[interrupt #1]] 매핑** — [[OMC]] 가 영문으로 물으면 [[Manager]] 가 한국어로 옮겨 Discord 전달 → 응답 받아 inject. 이 round-trip 이 매끄럽게 동작하는지는 [[W3]] 에서 검증 ([[ADR 0003]] Consequences)
- **가드레일 카운팅 정확도** — [[OMC]] 는 자체 모델 라우팅 (haiku/sonnet/opus) 을 하므로 토큰 비용 추정이 복잡. Anthropic API metering 또는 [[OMC]] `/trace` 출력 파싱 또는 PostToolUse hook 중 택일 ([[ADR 0003]] Consequences)
- **E2E 테스트 실행으로 인한 토큰 폭주** — 재시도 × 멀티턴 곱셈. 가드레일 이중화로 완화
- **금지 작업 강제 메커니즘** — prompt 만으로는 우회 가능. 환경 차단 (`.env` 미복사, `gh` 차단) 이 진짜 안전장치
- **wiki retrieval 품질** — grep 기반은 초기엔 충분하나, repo 성장 시 한계. FTS5 → embedding 진화 경로 명시

### Low

- **[[dev-wiki]] vs [[target-repo wiki]] 혼선** — 같은 "wiki" 단어를 다른 의미로 씀. [[SCHEMA.md]] + glossary 에서 명시적으로 구분 ([[ADR 0001]])
- **이슈 자동 감지 vs 봇 명령 혼선** — Discord 메시지에 이슈 링크가 우연히 포함된 경우 오탐 가능 → trigger 키워드 병행 권장
- **launchd 프로세스 의존성 순서** — Ollama 준비 전 FastAPI 시작 시 첫 호출 실패. KeepAlive 로 재시작은 되나 startup grace 필요

---

## 12. 운영 (launchd / 시작 순서)

원본 spec 의 운영 부분은 그대로 유지한다.

### launchd 프로세스 3개

| 순서 | 프로세스 | 역할 |
|---|---|---|
| 1 | `ollama serve` | LLM 런타임 ([[qwen3.5:9b]] 호스팅) |
| 2 | FastAPI (`agent-server`) | HTTP API + LangGraph 오케스트레이션 |
| 3 | Discord bot (`agent-bot`) | 사용자 인터페이스 (별도 프로세스) |

### 시작 순서

1. **Ollama 먼저** — 모델 로딩 시간 (~10초) 필요
2. **FastAPI 둘째** — Ollama 준비된 후 `/health` 응답 가능
3. **Discord bot 마지막** — FastAPI `/tasks` 엔드포인트 준비된 후 mention 수신 시작

### 실패 시 동작

- 각 프로세스 `KeepAlive: true` + `ThrottleInterval: 30` 으로 자동 재시작
- 시작 순서가 깨져 첫 호출이 실패해도 KeepAlive 가 복구
- 단, Ollama 모델 로딩이 30초를 넘으면 FastAPI 첫 호출 실패할 수 있음 → startup grace 권장

### 디렉터리 구조 (운영)

```
~/agent-server/
├── launchd/
│   ├── com.dongmin.ollama.plist
│   ├── com.dongmin.fastapi.plist
│   └── com.dongmin.discord-bot.plist
├── logs/                # stdout/stderr → SQLite 보조
└── data/
    ├── checkpoints.sqlite
    └── tasks.sqlite
```

---

## 다음 단계

[[W0]] 부트스트랩 완료 직후 [[W0.5]] 검증 게이트 진입. 자세한 작업 조각은 `work-plan.md` section 7 (W0 부트스트랩) 및 section 8 (W0.5 검증 게이트) 참조.

### W0.5 산출물 (다음)

- `wiki/decisions/0007-omc-validation-result.md` — 결과 ADR (Accepted/Rejected/Modified). ADR 0006은 시스템 범위 정의로 선점
- `wiki/phases/w0.5-validation.md` — 측정 데이터 표, 스크린샷 경로, 결정 근거

---

*개정 이력*
- 2026-05-25: W0 부트스트랩에서 원본 spec section 1~12 개정. ADR 0001~0005 반영.
