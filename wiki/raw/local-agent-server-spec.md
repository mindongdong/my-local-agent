# 로컬 에이전트 서버 시스템 설계 명세

> Mac Mini 24/7 로컬 에이전트 서버 구축 계획서  
> Manager Agent(로컬 LLM) + Worker(Claude Code) Agent-to-Agent 구조

---

## 0. 배경 및 목표

### 문제 상황
- 회사 업무 외 개인 프로젝트 진행할 시간/여유 부족
- Claude Code 토큰이 현재 작업량 대비 잉여 상태
- Mac Mini가 유휴 상태
- 하고 싶은 작업은 많지만 직접 코딩할 여유가 없음

### 목표
- Mac Mini에서 24/7 로컬 에이전트 구동
- 디스코드로 작업 지시 → 로컬 Manager가 Claude Code를 조작 → E2E 개발 진행 → 결과 한국어 보고 → 승인 후 GitHub PR
- Agent-to-Agent: 로컬 LLM이 "판단/조율", Claude Code가 "실행" 담당

---

## 1. 시스템 구성

```
[Discord]
   ↕  자연어 한국어
[Manager Agent] ── Gemma 3n E4B via Ollama (24/7 daemon)
   │  · 의도 파악, 작업 계획, 프롬프트 엔지니어링
   │  · 결과 검증, 한국어 요약, 승인 게이트 관리
   ↓  구조화된 영문 프롬프트
[Worker Agent] ── Claude Code (Phase 1 headless → Phase 2 cmux)
   │  · 실제 코드 작성/수정/테스트 (E2E)
   ↓
[GitHub PR]
```

### 인프라 결정

| 항목 | 결정 | 비고 |
|---|---|---|
| 하드웨어 | Mac Mini M4 16GB | |
| Manager LLM | **Gemma 3n E4B** (`gemma3n:e4b`) | Qwen 2.5 7B는 백업 옵션 |
| Worker | Claude Code | Phase 1 headless → Phase 2 cmux |
| LLM 런타임 | Ollama | |
| 오케스트레이션 | LangGraph + FastAPI | |
| 영속화 | SQLite (LangGraph Checkpointer + 작업 이력) | |
| 네트워크 | 로컬 only | 디스코드 봇만 outbound |
| 24/7 구동 | launchd (3개 프로세스) | ollama, fastapi, discord bot |

### 레이어 분리 원칙

| 레이어 | 책임 |
|---|---|
| **FastAPI** | HTTP I/O, 인증/권한, 요청 검증, 백그라운드 태스크 트리거 |
| **LangGraph** | 에이전트 추론, 상태 전이, LLM/도구 호출, 인간 개입 게이트 |
| **Discord Bot** | 사용자 인터페이스, thread 관리 (별도 프로세스) |

> FastAPI에 LLM 코드 없음, LangGraph에 HTTP 코드 없음 → 테스트/유지보수 용이

---

## 2. 워크플로우 (LangGraph)

```
[GitHub Issue 링크 수신 (Discord)]
    ↓
[parse_issue]      — 이슈 fetch + 본문 파싱
    ↓
[generate_plan]    — 작업 분해 + 정보 충분성 판단
    ↓
[interrupt #1]     — 정보 부족 시만, 디스코드 thread 자유 응답 ─┐
    ↓                                                              │ 충분해질 때까지 루프
[build_prompt]     — Claude Code용 영문 프롬프트 + wiki retrieve
    ↓
[invoke_claude_code] — worktree에서 E2E 실행 (test 포함)
    ↓
[retry_loop]       — 테스트/빌드 실패 시 최대 2~3회
    ↓
[summarize_diff]   — 한국어 변경 파일 + diff 요약
    ↓
[interrupt #2]     — 코드 결과 승인 게이트
    ↓
[interrupt #3]     — PR 생성 승인 게이트
    ↓
[create_pr] → [distill_to_wiki] → END
```

### 자율성 레벨: L2
- 2단계 승인 (코드 결과 + PR 생성)
- 정보 부족 시 추가 질문 interrupt 발동 (총 최대 3개 interrupt)

---

## 3. 가드레일 (이중 구조)

| 범위 | 한도 | 초과 시 |
|---|---|---|
| **일일** | 총 토큰 비용 $20 (UTC 자정 리셋) | 신규 작업 거절, 진행 중은 유지 |
| **작업당** | Claude Code turn 50 | 중단 + 사용자 보고 |
| **재시도** | 테스트/빌드 실패 시 최대 2~3회 | 중단 + 사용자 보고 |

> 일일 상한과 작업당 상한이 곱셈 폭주를 방지하는 핵심.

---

## 4. 격리 + 안전장치

### 환경 격리
- **git worktree** 작업당 1개 (동일 repo 다중 복제)
- 동시 작업 최대 2~3개, 초과 시 FIFO 큐 + 대기 알림

### 금지 작업 (다층 방어)

| 금지 항목 | 차단 메커니즘 |
|---|---|
| `main`/`master` 직접 push | GitHub branch protection |
| Force push, branch 삭제 | Claude Code allowed tools에서 `git push --force`, `git branch -D` 차단 |
| `.env` 접근, 비밀값 수정 | worktree에 `.env` 미복사 (또는 dummy로 대체) |
| DB 마이그레이션 / 스키마 변경 | worktree env에 DB 접속정보 미주입 |
| 외부 API 결제/과금 호출 | 결제 API 키 worktree env에 미주입 |

> 시스템 프롬프트만으로는 우회 가능. 환경 자체에서 원천 차단해야 안전.

### 취소
- `/cancel <task_id>` → SIGTERM (graceful) → 5초 후 SIGKILL → worktree 정리

---

## 5. 디스코드 인터랙션

### 트리거
- 사용자가 GitHub Issue 링크를 디스코드에 게시 → 봇이 자동 감지
- 봇이 작업 thread 생성 → 이후 모든 통신은 thread 안에서 (task_id ↔ thread 매핑)

### 알림 정책 (조용함)

| 단계 | 알림 | 멘션 |
|---|---|---|
| 작업 시작 | ✅ | ❌ |
| 정보 부족 추가 질문 | ✅ | ✅ |
| 코드 승인 요청 | ✅ | ✅ |
| PR 승인 요청 | ✅ | ✅ |
| 완료 | ✅ | ❌ |
| 실패 | ✅ | ✅ |
| 가드레일 초과 | ✅ | ✅ |
| 진행 중 단계 알림 | ❌ | ❌ |

### 명령
- `/cancel <task_id>` — 작업 취소
- `/tasks` — 현재 작업 목록
- `/status <task_id>` — 상태 조회

### Manager 한국어 보고 형식
- 변경 파일 목록 + diff 요약
- 코드 승인 요청 시 함께 제시

---

## 6. 컨텍스트 학습 (llm-wiki)

### 위치
- **Obsidian Vault의 PARA `Resources/agent-wiki/<repo>/`**
- 사용자 개인 자산으로 누적, repo에 commit하지 않음

### 누적 방식
- PR 완료 시 `distill_to_wiki` 노드가 마크다운 자동 append
- 기록 내용: 작업 요약 / 결정 이유 / 마주친 함정 / 코드 패턴

### Retrieval 진화 경로
1. **초기 (W6)**: grep 기반
2. **다음 단계**: SQLite FTS5
3. **필요 시**: embedding + vector search

### Worker 프롬프트 주입
- `build_prompt` 노드에서 관련 wiki 항목 retrieve → Claude Code 프롬프트에 컨텍스트로 첨부

---

## 7. 옵저버빌리티

### FastAPI 대시보드 v1
- Jinja2 + HTMX 권장 (가볍게)
- 표시: 작업 이력, 상태, diff, wiki 항목 통합 조회

### 로그
- 구조화 JSON → SQLite + stdout
- 작업 이력 영속 저장 (재해 시 분석)

### API 엔드포인트
| Method | Path | 용도 |
|---|---|---|
| POST | `/tasks` | 새 작업 시작 (봇이 호출) |
| POST | `/tasks/{id}/approve` | 승인 게이트 응답 |
| GET | `/tasks/{id}/status` | 상태 조회 (snapshot.next, values) |
| GET | `/tasks/{id}/stream` | SSE 진행 스트리밍 (옵션) |
| GET | `/dashboard` | 웹 대시보드 |

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
│   │   ├── planner.py
│   │   ├── claude_code.py
│   │   ├── summarizer.py
│   │   ├── pr_creator.py
│   │   └── distiller.py
│   └── tools/               cmux/gh CLI 래퍼
├── bot/                     Discord 봇 (별도 프로세스)
│   └── discord_client.py
├── worktrees/               git worktree 동적 생성/제거
├── data/
│   ├── checkpoints.sqlite   LangGraph 상태
│   └── tasks.sqlite         작업 이력
└── launchd/                 .plist 파일 3개
```

---

## 9. 로드맵 (주 3~5시간, 조각내기 패턴)

각 phase는 **명확한 산출물 = 끝낸 느낌**을 주도록 1주 단위로 구성.

| 주차 | Phase | 산출물 | 작업 조각 |
|---|---|---|---|
| **W1** | 0. 환경 셋팅 | Ollama + Gemma 동작, FastAPI hello, 봇 메시지 수신 | (1) launchd 3개 등록, (2) Ollama 모델 다운로드 + 응답 테스트, (3) FastAPI `/health`, (4) discord.py 봇 → mention 응답 |
| **W2** | 1. Manager 단독 | 이슈 링크 → 한국어 계획 출력 (Claude Code 호출 X) | (1) GitHub API로 이슈 fetch, (2) LangGraph minimal (parse → plan), (3) 봇 thread 생성 + 결과 포스팅 |
| **W3** | 2. interrupt + 추가 질문 | 정보 부족 시 자유 질문 → 응답 → 그래프 재개 | (1) checkpointer 도입, (2) `interrupt()` + resume, (3) thread reply → resume 매핑 |
| **W4** | 3. Claude Code 호출 (headless) | 단일 이슈 → `claude -p` → diff 한국어 요약 → 승인 → 로컬 commit | (1) git worktree 생성/정리, (2) `claude -p` 래퍼 + turn 제한, (3) diff 파싱 + Manager 요약, (4) 코드 승인 interrupt |
| **W5** | 4. PR 자동화 + 가드레일 | `gh` CLI로 PR 생성, 토큰 측정 + 차단 | (1) PR 승인 interrupt, (2) gh CLI 래핑, (3) 토큰 카운터 + 일일 리셋, (4) 금지 작업 환경 차단 |
| **W6** | 5. llm-wiki + 대시보드 | PR 완료 시 자동 노트 누적 + retrieval, 대시보드 v1 | (1) distill 노드, (2) Obsidian Vault 경로 통합, (3) grep retrieve, (4) `/tasks` HTML 뷰 |
| **W7** | 6. cmux 전환 (옵션) | 장기 세션, 멀티턴 가능 | (1) cmux 세션 spawn, (2) headless → cmux 추상화 |
| **W8+** | 7. 운영 안정화 | 실패 패턴 분석, 동시 2~3개 검증, 큐 도입 | 운영하며 발견된 이슈 대응 |

---

## 10. 의사결정 기록 (Grilling 결과)

### 인프라
- 하드웨어: M4 16GB → 7B Q4 모델 권장 영역
- 네트워크: 로컬 only → 봇만 outbound로 충분
- 동시 작업: 2~3개 상한

### 작업 범위
- Repo: 1개 집중 (whitelist 단순화)
- 자율성: L2 (코드 + PR 2단계 승인)
- 작업 유형: 기능 추가 / 버그 수정 / 리팩토링 / 문서화 / 라이브러리 업데이트 / 테스트 작성

### 입력/실행
- 트리거: GitHub Issue 링크
- 이슈 명세: 자유 형식, 부족 시 Manager가 자유 응답으로 역질문
- Claude Code 호출: Phase 1 headless, Phase 2 cmux
- 작업 범위: E2E (테스트 실행 통과까지)

### 안전
- 격리: git worktree
- 재시도: 2~3회
- 가드레일: 일일 $20 + 작업당 turn 50
- 금지 작업: 5종 (push to main, force push/branch 삭제, .env/secret, DB schema, 결제 API)

### 인터페이스
- 알림: 조용함 (시작/승인/완료)
- 멘션: 실패/승인/초과 시만
- 취소: `/cancel` 즉시 중단
- 일일 상한 도달: 신규 거절, 다음날까지 대기

### 학습 / 관찰
- 컨텍스트: llm-wiki를 Obsidian Vault PARA에 누적
- 큐: FIFO
- 옵저버빌리티: FastAPI 대시보드

---

## 11. 주요 리스크 및 주의사항

### High
- **Gemma 3n E4B의 tool calling/JSON 출력 일관성** — 정보 충분성 판단, 구조화 출력에서 흔들릴 수 있음. 안정성 미달 시 Qwen 2.5 7B로 전환
- **16GB 메모리 한계** — Gemma(~3GB) + cmux 세션 2~3개 + Claude Code + macOS = 빠듯. 모니터링 필수, 스왑 발생 시 동시 작업 1개로 축소
- **자유 형식 이슈 → 의도 파싱 부담** — Manager 시스템 프롬프트 설계가 시스템 품질의 80%를 좌우

### Medium
- **E2E 테스트 실행으로 인한 토큰 폭주** — 재시도 × 멀티턴 곱셈. 가드레일 이중화로 완화
- **금지 작업 강제 메커니즘** — 프롬프트 만으로는 우회 가능. 환경 차단(.env 미복사 등)이 진짜 안전장치
- **llm-wiki retrieval 품질** — grep 기반은 초기엔 충분하나, repo 성장 시 한계. FTS5 → embedding 진화 경로 명시

### Low
- **이슈 자동 감지 vs 봇 명령 혼선** — 디스코드 메시지에 이슈 링크가 우연히 포함된 경우 오탐 가능 → trigger 키워드 병행 권장
- **launchd 프로세스 의존성 순서** — Ollama 준비 전 FastAPI 시작 시 첫 호출 실패. KeepAlive로 재시작은 되나 startup grace 필요

---

## 12. 다음 단계 (선택)

세 가지 중 하나로 진행:

1. **W1 Phase 0 실행 가이드** — launchd `.plist`, Ollama 설치, FastAPI 골격, 디스코드 봇 토큰까지 단계별 체크리스트
2. **State 스키마 + 그래프 골격 코드** — `agent/state.py`, `agent/graph.py` 실제 코드 (W2~W4 한 번에)
3. **이슈 템플릿 + Manager 시스템 프롬프트 설계** — 정보 충분성 판단 프롬프트 (모델 성능 좌우)

---

*Last updated: 2026-05-21*
