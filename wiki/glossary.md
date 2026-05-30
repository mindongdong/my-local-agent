# Glossary

프로젝트 전체에서 사용되는 핵심 용어 정의. 각 용어는 1~3문장으로 간결하게 설명되며, 관련 용어는 `[[링크]]` 형식으로 참조된다.

---

## 시스템 정의

### 로컬 에이전트 서버

> "하나의 깃허브 레포지토리를 작업 공간으로 추적하는 로컬 에이전트 서버 기반의 에이전트 매니징 시스템" (2026-05-25 확정)

1.0 시스템 범위는 단일 GitHub repo 로 한정 ([[ADR 0006]] 참고). 검증 (W0~W7) 완료 후 multi-repo 확장 도모. Mac Mini 등 로컬 머신에서 돌아가는 매니징 서버가 [[Manager]] LLM 으로 의도를 해석하고, [[OMC]] + [[cmux]] 환경에서 [[Worker]] 를 띄워 코드 작업을 수행하며, 결과를 GitHub PR + [[target-repo wiki]] 로 외부화한다.

**관련**: [[Manager]], [[Worker]], [[OMC]], [[cmux]], [[worktree]], [[dev-wiki]], [[target-repo wiki]]

---

## 역할 분담

### Manager

한국어 측에서 이슈 fetch, 의도 파악, 승인 게이트, 가드레일을 담당하는 역할. [[Worker]]와 [[OMC]]의 작업을 감독하고, PR 생성 권한을 보유한다. 현재는 qwen3.5:9b LLM으로 자동화되며, 사용자가 수동 승인 게이트로도 개입할 수 있다.

**관련**: [[Worker]], [[OMC]], [[Hybrid 책임 분담]]

### Worker

실제 코드를 작성하고 실행하고 테스트하는 역할. 현재는 [[OMC]]에 의해 수행되며, 영문 측 작업 전체를 담당한다. [[Manager]]의 지시를 받아 작업을 진행하고, 실행 중 모호함이 발생하면 [[interrupt #1]]로 추가 질문한다.

**관련**: [[Manager]], [[OMC]], [[interrupt #1]]

### Hybrid 책임 분담 (Hybrid C)

[[Manager]]는 한국어/승인/가드레일만 책임지고, [[OMC]]는 영문 측 코드 작업 전체를 책임지는 분담 구조. PR 생성 권한은 [[Manager]]에만 있고, [[OMC]]의 자율성은 코드 작성과 테스트까지로 제한된다.

**관련**: [[Manager]], [[OMC]], [[L2 자율성]]

---

## wiki 종류

### dev-wiki

이 저장소 (`wiki/`) 내부에 축적되는 빌드 노하우와 결정 기록. 용어, 아키텍처, ADR, 작업 로그 등을 포함하며, 미래 세션의 컨텍스트 복구용이다. [[target-repo wiki]]와는 별개 개념.

**관련**: [[target-repo wiki]], [[SCHEMA.md]]

### target-repo wiki

[[Manager]]가 작업을 완료한 후, 빌드 과정에서 얻은 노하우를 타겟 저장소에 distill하는 wiki. 별도 저장소에 위치하며, [[dev-wiki]]와는 다른 대상이다.

**관련**: [[dev-wiki]]

### llm-wiki

LLM이 살아있는 지식 베이스로 사용하고 갱신하는 마크다운 wiki 운영 철학. `wiki/raw/llm-wiki.md` 에 원본 철학 문서가 있다. [[dev-wiki]]는 이 철학을 in-repo로 구체화한 인스턴스이며, [[SCHEMA.md]]가 ingest/query/lint 워크플로우로 운영 규약을 정의한다.

**관련**: [[dev-wiki]], [[SCHEMA.md]]

---

## OMC (oh-my-claudecode) 관련

### OMC (oh-my-claudecode)

Claude Code 플러그인으로, 30개 이상의 전문 에이전트 + [[magic keyword]] + Hook + cmux 오케스트레이션을 내장한 다중 에이전트 오케스트레이션 레이어. [[Worker]] 역할을 수행하며, 코드 작성/실행/테스트를 자동화한다.

**관련**: [[Worker]], [[magic keyword]], [[cmux]]

### magic keyword

OMC가 인식하는 특수 키워드로, 작업 모드를 선택한다. 주요 키워드는 `autopilot:` (자동 계획 분해 + 실행), `ralph:` (자율성 루프), `ulw` (병렬 작업), `team` (다중 에이전트 협력), `eco:` (경량 모델 라우팅)이 있다.

**관련**: [[OMC]], [/deepinit], [/deep-interview], [/omc-doctor]

### /deepinit

OMC의 명령어로, 프로젝트 초기 컨텍스트를 깊이 있게 수집하고 정리한다. 새 작업 시작 시 사용된다.

**관련**: [[OMC]], [/deep-interview], [/omc-doctor]

### /deep-interview

OMC의 명령어로, 작업 실행 중 모호함이 발생했을 때 사용자(또는 [[Manager]])에게 추가 질문을 한다. [[interrupt #1]]과 연동된다.

**관련**: [[OMC]], [[interrupt #1]], [/deepinit], [/omc-doctor]

### /omc-doctor

OMC의 진단 명령어로, 현재 환경 (플러그인, 모델 라우팅, hook, cmux 연결)의 상태를 점검한다.

**관련**: [[OMC]], [/deepinit], [/deep-interview]

---

## 자율성 / interrupt

### L2 자율성

코드 승인 + PR 승인 두 단계를 거치는 자율성 제한 구조. [[OMC]]는 코드까지만 작성하고, [[interrupt #2]]에서 코드 승인을 받고, [[interrupt #3]]에서 PR 승인을 받은 후 최종 merge된다.

**관련**: [[interrupt #2]], [[interrupt #3]], [[Hybrid 책임 분담]]

### interrupt #1

[[Worker]]가 작업을 진행하던 중 정보 부족 또는 모호함이 발생했을 때, [[Manager]]나 사용자에게 추가 질문을 하는 인터럽트. `[[/deep-interview]]`로 구현된다.

**관련**: [[interrupt #2]], [[interrupt #3]], [[L2 자율성]], [/deep-interview]

### interrupt #2

[[Worker]]가 코드 작성을 완료한 후, [[Manager]]의 코드 승인을 대기하는 인터럽트. 승인 없이는 다음 단계로 진행할 수 없다.

**관련**: [[interrupt #1]], [[interrupt #3]], [[L2 자율성]]

### interrupt #3

[[Worker]]가 PR을 생성하기 전, [[Manager]]의 PR 승인을 대기하는 인터럽트. [[Manager]]만 최종 `gh` CLI로 PR을 생성할 수 있다.

**관련**: [[interrupt #1]], [[interrupt #2]], [[L2 자율성]]

---

## 런타임 도구

### cmux

멀티 pane 워크스페이스 터미널 도구로, [[OMC]]가 cmux 세션 내에 여러 worker를 병렬로 배치한다. `send`/`send-key` (명령 전송)와 `capture-pane` (출력 캡처) 두 가지 핵심 작업으로 [[Manager]]와 [[Worker]] 간 통신을 중개한다.

**관련**: [[OMC]], [[worktree]]

### worktree

git working tree로, 각 작업별로 격리된 브랜치와 파일 시스템 이미지를 제공한다. [[Manager]]가 각 작업을 worktree로 분리하여 독립적으로 실행할 수 있게 한다.

**관련**: [[cmux]]

---

## 가드레일

### 가드레일

[[Manager]]가 외부에서 강제하는 자원/권한 제한의 통칭. 일일 토큰 cap, 작업당 turn cap, worktree env 격리, PR 생성 권한 분리 등이 포함된다. [[L2 자율성]]의 안전망 역할을 하며, [[OMC]]가 의도치 않게 가드레일을 우회하지 못하도록 [[Manager]]가 카운팅/차단을 담당한다.

**관련**: [[일일 토큰 cap]], [[작업당 turn cap]], [[L2 자율성]], [[worktree]]

### 일일 토큰 cap

[[Manager]]와 [[OMC]]의 총 토큰 소비량을 제한하는 가드레일. 기본값은 일일 $20으로 설정되며, UTC 기준으로 매일 리셋된다. [[Manager]]가 외부에서 강제한다.

**관련**: [[작업당 turn cap]], [[Hybrid 책임 분담]]

### 작업당 turn cap

단일 작업의 최대 LLM 턴(round-trip) 수를 제한하는 가드레일. 기본값은 50 turn이며, 무한 루프를 방지한다. [[Manager]]가 외부에서 강제한다.

**관련**: [[일일 토큰 cap]], [[Hybrid 책임 분담]]

---

## 로드맵

### tracer-bullet 로드맵

Layer-by-layer 구조 대신, 가는 E2E 라인을 먼저 구현하고 점진적으로 완성하는 로드맵 패러다임. [[W0]] 부트스트랩 후 [[W1]]에서 Discord → OMC → 한국어 출력까지의 최소 E2E를 먼저 돌린다.

**관련**: [[W0]], [[W0.5]], [[W1]]

### W0 / W0.5 / W1~W7

프로젝트 진행을 나누는 단계별 명명 규약. [[W0]]는 wiki 뼈대 + ADR + 환경 셋업 (부트스트랩), [[W0.5]]는 OMC/cmux/Qwen 검증 게이트, [[W1]]~[[W7]]는 각각 기능 구현 주차이다.

**관련**: [[tracer-bullet 로드맵]]

---

## Manager LLM

### qwen3.5:9b (Q4_K_M)

[[Manager]] 역할을 수행하기 위해 채택된 로컬 LLM. Ollama로 실행된다. Q4_K_M quant의 디스크 크기는 약 6.6GB이나 **로드 시 RAM 점유는 8.5GB**(ctx 4096 실측, [[w0.5-validation]]). 256K 컨텍스트 윈도우와 멀티모달을 지원하나, 16GB에서 full context는 불가하여 운영 컨텍스트를 캡한다.

**관련**: [[Manager]], [[Gemma 3n E4B]]

### Gemma 3n E4B

[[qwen3.5:9b]]의 백업 옵션으로, 메모리 문제 발생 시 대체할 수 있는 로컬 LLM. 필요에 따라 [[W0.5]]에서 평가된다.

**관련**: [[qwen3.5:9b]], [[Manager]]

---

## 개발 프로세스

### Trunk-Based Development (TBD)

이 repo의 git 워크플로우 ([[ADR 0008]]). `main`을 단일 트렁크로 두고, 모든 변경을 `main`에서 분기한 짧은 수명 브랜치에서 작업해 PR로 자주 통합한다. 장수 브랜치(Git Flow의 develop/release)를 두지 않는다. 운영 세부는 `CONTRIBUTING.md`.

**관련**: [[Conventional Commits]], [[tracer-bullet 로드맵]]

### Conventional Commits

커밋 메시지 컨벤션. `type(scope): subject` 형식, 영어·간결. type은 feat/fix/refactor/docs/test/chore/perf/ci. 이 repo의 커밋 규약이며 [[Trunk-Based Development (TBD)]]와 함께 [[ADR 0008]]에서 채택.

**관련**: [[Trunk-Based Development (TBD)]]
