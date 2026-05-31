# W1 핸드오프 — 다른 머신 → 타겟 Mac Mini 전환

**작성**: 2026-05-30
**대상**: 타겟 Mac Mini(M4 16GB)에서 W1을 이어서 진행할 새 Claude Code 세션
**상태**: W0/W0.5 완료(다른 머신), Mac Mini 환경 셋업·재검증 전

> 읽는 순서: **이 문서 → `CLAUDE.md` → `wiki/SCHEMA.md` → `wiki/index.md` → §3 필독 wiki → W1 착수.**

---

## 1. ⚠️ 머신 전환 주의 (가장 중요)

W0/W0.5의 **모든 실측치**(메모리 8.5GB·free%·swap, cmux round-trip 300/300, JSON 14/14·93%)는 **이 Mac Mini가 아닌 개발용 다른 Mac**에서 측정됐다.

- **메모리는 binding constraint이자 머신 특정값**이다. [[ADR 0007]]의 Go는 "헤드리스 전제"였고 **다른 머신 기준**이다.
- cmux/ollama/OMC도 그 머신에 설치된 것이다. **Mac Mini에는 아무것도 깔려 있지 않다고 가정**한다.

→ Mac Mini에서 **환경 셋업(§5) + W0.5 핵심 재검증(§6)** 을 **W1 착수 전에 반드시** 다시 한다. 결과가 다르면 [`w0.5-validation.md`](w0.5-validation.md)에 "Mac Mini 재측정" 섹션을 추가하고, 필요 시 [[ADR 0007]]을 보완(또는 머신별 결과 ADR 신설)한다.

---

## 2. 현재 위치

| Phase | 상태 |
|---|---|
| W0 (부트스트랩) | ✅ wiki 뼈대 + ADR 0001~0006 + system-design |
| W0.5 (검증 게이트) | ✅ **Go (헤드리스 전제, 다른 머신)** — [[ADR 0007]] |
| git 체계 | ✅ TBD + Conventional Commits + PR 템플릿 ([[ADR 0008]], `CONTRIBUTING.md`) |
| **W1 (E2E 스파이크)** | ⏳ **다음 — 이 핸드오프의 목표** |

---

## 3. 필독 wiki (repo에 모두 있음 — 클론하면 바로 읽힘)

- `CLAUDE.md` — 행동 지침 + wiki 포인터
- `wiki/SCHEMA.md` — wiki 운영 규약 (ingest/query/lint, ADR/glossary/log 형식)
- `wiki/index.md` — 카탈로그 진입점
- `wiki/architecture/system-design.md` — **현재 시스템 설계** (워크플로우 노드, cmux 라이프사이클, W1 정의 포함)
- `wiki/phases/w0.5-validation.md` — W0.5 실측 데이터 + **측정 방법**(cmux round-trip, JSON, 메모리)
- 핵심 ADR: **0002**(Worker=OMC+cmux), **0003**(Hybrid 책임 분담), **0004**(qwen3.5:9b Manager), **0007**(W0.5 Go), **0008**(git workflow)
- `work-plan.md` — 로드맵 (§9 W1~W7, §4 메모리 현실, §10 리스크)

---

## 4. 반드시 기억할 운영 사실 (W0.5에서 확정 — 자세한 건 wiki)

- **Manager LLM = `qwen3.5:9b` (ollama)**. 호출 시 **`think:false` + `temperature:0`**. **JSON은 ollama `format` 스키마가 강제되지 않음**(probe로 확인) → **프롬프트에 정확한 키 명시 + 코드 파싱/검증 + 재시도**로 구현. (구조 100% / 의미 93%)
- **cmux 0.64.10 (소켓/GUI 기반)**: tmux식 `send-keys`/`new-session`은 **없다**. 실제 API:
  - spawn: `cmux new-workspace --name <n> --command 'claude' --focus false`
  - 입력: `cmux send --surface <s> "<text>"` + `cmux send-key --surface <s> Enter`
  - 캡처: `cmux read-screen --surface <s>` (tmux-compat `capture-pane`도 동작)
  - caller 파악: `cmux identify --json` / 정리: `cmux close-workspace`
  - round-trip 안정 측정됨(300/300, 다른 머신). 네이티브 `cmux omc`/`cmux claude-teams`/`cmux hooks`도 있음 — 활용 여부는 미결정.
- **메모리**: 모델 로드 RAM ~8.5GB(ctx 4096). 256K는 명목 — **컨텍스트 캡 필수**. claude 워커 ~213MB/개. **`ulw` 병렬은 서버측이라 로컬 RAM을 N배로 안 늘림** — 메모리 레버는 모델 + 데스크톱 앱. **헤드리스 운영(Chrome/VSCode 금지)**이 14GB 임계값의 관건.
- **L2 자율성**: OMC는 **코드/테스트까지만**. PR 생성·가드레일은 **Manager**. worker env에서 `gh` CLI 제거.
- **git**: TBD, 짧은 브랜치 + PR(`.github/pull_request_template.md`), Conventional Commits 영어·간결. `.omc/`는 gitignore.

---

## 5. Mac Mini 환경 셋업 (W0-9 재실행)

- **ollama**: 설치(`brew install ollama` → `brew services start ollama`) + `ollama pull qwen3.5:9b` (~6.6GB 디스크). `ollama --version`, `ollama list` 확인.
- **OMC**: `/plugin marketplace add https://github.com/Yeachan-Heo/oh-my-claudecode` → `/plugin install oh-my-claudecode` → `/oh-my-claudecode:omc-setup` → `/omc-doctor` 통과.
- **cmux**: `cmux version`, `cmux ping`(PONG) 확인. (이미 설치돼 있다면 버전만.)
- **gh CLI**: `gh auth status` (PR 생성용).

---

## 6. Mac Mini W0.5 재검증 (W1 착수 전 필수)

1. **메모리**: 모델 로드(`ollama run qwen3.5:9b ...` 또는 `/api/generate` keep_alive) 후 `ollama ps`(RSS) + `memory_pressure`/`top`/`sysctl vm.swapusage`. **헤드리스에서 peak < 14GB** 확인.
2. **cmux round-trip**: `new-workspace --focus false` → `send` + `send-key Enter` → `read-screen` 스모크(출력 토큰을 산술 결과로 만들어 "실제 실행"만 카운트). 성공률 ≥ 99%. 방법은 [`w0.5-validation.md`](w0.5-validation.md) 참조.
3. 결과를 [`w0.5-validation.md`](w0.5-validation.md)에 **"Mac Mini 재측정"** 섹션으로 기록. 다르면 [[ADR 0007]] 보완.
4. **No-go(메모리 초과)** 시: [[ADR 0004]] fallback(Gemma 3n E4B) 또는 동시성 축소 — 새 ADR로 결정.

---

## 7. W1 정의 (tracer-bullet E2E 스파이크)

**목표**: Discord 메시지 → 하드코딩 영문 prompt → cmux OMC 실행 → **diff 한국어 출력**. (PR·승인·가드레일 **없음** — 가는 라인부터.) 출처: `work-plan.md` §9, `system-design.md`.

조각:
1. Discord bot mention 수신
2. cmux 세션 spawn 헬퍼 (`new-workspace --command 'claude' --focus false`)
3. OMC 구동 래퍼 (`send` + `send-key Enter` → `read-screen`/`capture-pane`)
4. diff 캡처 → `qwen3.5:9b` 한국어 요약 (`think:false`, `temp:0`)
5. Discord thread에 결과 포스팅

\+ W0.5에서 **연기한 모델 라우팅(`eco:`→haiku)**을 이 과정 중 OMC `/trace`로 확인.

---

## 8. W1 권장 시작점

tracer-bullet이므로 **통신 척추부터**:
1. ✅ **(2)+(3)** cmux 세션 spawn + OMC `send`/`read` 래퍼 PoC (Python). — `spike/w1/cmux_session.py`, `worker_spawn.py` (PR #6)
2. ✅ **(4)** Qwen 한국어 요약 함수. — `spike/w1/qwen_summarize.py` (PR #6)
3. ✅ **(1)(5)** Discord 양끝 연결. — `spike/w1/discord_bot.py` (@멘션→thread 포스팅, `feat/w1-discord`)

**W1 E2E 완료 (2026-05-31)**: 실 Discord `#일반` @멘션 → cmux `claude -p` 워커(격리 /tmp) → diff → qwen 한국어 요약 → thread 포스팅 끝까지 동작. 상세는 [log.md](../log.md) 2026-05-31 항목.
**남은 항목**: 모델 라우팅(`eco:`→haiku) — 순수 `claude -p`라 OMC 라우팅 미발생, OMC autopilot 워커 확장 시 `/trace`로 확인.

각 조각은 짧은 브랜치 + PR. 막히거나 결정이 필요하면 **한국어로 질문**.

---

## 부록: Mac Mini Claude Code 시작 지시문

> 아래를 Mac Mini의 새 Claude Code 세션에 붙여넣어 시작한다.

```text
너는 `local-agent-server` 프로젝트를 타겟 Mac Mini(M4 16GB)에서 이어서 개발하는 세션이다. 전체 맥락은 GitHub repo(https://github.com/mindongdong/my-local-agent)에 있다.

0. repo 준비: 없으면 `git clone https://github.com/mindongdong/my-local-agent.git`, 있으면 `git pull`.
1. 반드시 이 순서로 읽고 시작: wiki/phases/w1-handoff.md → CLAUDE.md → wiki/SCHEMA.md → wiki/index.md → 거기서 가리키는 ADR/architecture/w0.5-validation.
2. ⚠️ 중요: W0/W0.5는 다른 머신에서 측정됐다. 이 Mac Mini에서 환경 셋업(ollama+qwen3.5:9b, OMC, cmux) + W0.5 핵심 재검증(헤드리스 메모리 peak < 14GB, cmux round-trip ≥99%)을 W1 착수 전에 다시 한다. 결과를 wiki/phases/w0.5-validation.md에 "Mac Mini 재측정" 섹션으로 기록하고, 다르면 ADR 0007 보완.
3. 운영 규약 준수: Manager=qwen3.5:9b(think:false/temp:0, JSON은 프롬프트 키 명시+코드 검증 — ollama format은 강제 안 됨), cmux는 new-workspace/send+send-key/read-screen(tmux식 send-keys 아님), 헤드리스(Chrome/VSCode 금지), L2 자율성(OMC는 코드까지/PR·가드레일은 Manager), git은 TBD+Conventional Commits(영어·간결)+PR 템플릿(CONTRIBUTING.md).
4. 그다음 W1 E2E 스파이크: 핸드오프 §7~8대로 cmux spawn + OMC send/read 래퍼부터 → Qwen 요약 → Discord 양끝. 연기된 모델 라우팅(eco:→haiku)도 이때 /trace로 확인.
5. 각 작업은 짧은 브랜치 + PR. 막히거나 결정이 필요하면 한국어로 질문.

먼저 0~1을 수행하고, 읽은 내용 요약 + Mac Mini 환경 셋업/재검증 계획을 제시한 뒤 승인받고 진행해라.
```
