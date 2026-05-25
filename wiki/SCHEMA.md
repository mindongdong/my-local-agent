# wiki/SCHEMA.md

> **이 파일은 dev-wiki의 헌법이다.** 새 LLM 세션이 시작되면 가장 먼저 읽어야 한다.
> 모든 ingest·query·lint 작업은 여기 정의된 규약을 따른다.

---

## 1. 개요

이 wiki는 `my-local-agent` (로컬 멀티 에이전트 서버) 빌드 과정에서 얻은 **노하우를 누적하는 in-repo dev-wiki**다. 코드와 함께 버전 관리되며, 미래 세션이 과거 결정의 맥락을 즉시 파악할 수 있도록 유지된다.

**llm-wiki 철학**: LLM이 raw source를 읽고 wiki를 직접 작성·갱신한다. 지식은 질문마다 재발견되는 것이 아니라 wiki에 한 번 컴파일되어 복리로 축적된다. 인간은 소스 수집·방향 결정·좋은 질문을 담당하고, LLM은 요약·상호 참조·분류·기록을 담당한다.

> **dev-wiki vs target-repo wiki**: 이 wiki는 에이전트 서버 자체를 빌드하는 노하우를 담는다. 에이전트가 외부 타겟 repo에 생성하는 wiki(W6 이후)와는 완전히 별개다. glossary 참조: `[[dev-wiki]]`, `[[target-repo wiki]]`.

---

## 2. 디렉터리 구조

```
wiki/
├── SCHEMA.md              # 이 파일. 전체 규약의 단일 출처
├── index.md               # 카탈로그 — 모든 페이지의 링크 + 1줄 요약
├── log.md                 # 시계열 append-only 기록
├── glossary.md            # 도메인 용어 정의
├── raw/                   # immutable 원본 소스. LLM이 읽기만 함
│   ├── local-agent-server-spec.md
│   ├── llm-wiki.md
│   └── grilling/          # 설계 그릴링 세션 압축본
├── decisions/             # ADR (Architecture Decision Records)
│   └── NNNN-<slug>.md
├── concepts/              # 개념별 페이지 (필요 시 점진 생성)
├── architecture/          # 항상 최신 시스템 설계
│   └── system-design.md
└── phases/                # 각 개발 phase의 작업 노트
    └── w<n>-<name>.md
```

| 디렉터리/파일 | 역할 | 소유자 |
|---|---|---|
| `SCHEMA.md` | 규약 단일 출처 | 인간 + LLM 공동 진화 |
| `index.md` | 전체 페이지 카탈로그, 탐색 진입점 | LLM (매 ingest마다 갱신) |
| `log.md` | 시계열 기록, grep 가능한 append-only | LLM (항목 추가만) |
| `glossary.md` | 도메인 용어 정의 및 상호 참조 | LLM |
| `raw/` | 원본 소스. 절대 수정 불가 | 인간이 투입, LLM은 read-only |
| `decisions/` | 아키텍처 결정 기록 (ADR) | LLM (인간 승인 후 확정) |
| `concepts/` | 주제별 심층 페이지, 필요 시 생성 | LLM |
| `architecture/` | 현재 시스템 설계 (항상 최신) | LLM |
| `phases/` | phase별 작업 노트, 흔들린 가정, 다음 의문점 | LLM |

---

## 3. ingest 워크플로우

새 raw source가 `wiki/raw/`에 추가됐을 때 LLM이 따르는 단계.

| 단계 | 행동 | 산출물 |
|---|---|---|
| 1. **read** | raw source 전체 읽기 | (내부 이해) |
| 2. **discuss** | 핵심 테이크어웨이를 사용자와 확인. 강조점·생략할 내용 합의 | (대화) |
| 3. **summarize** | `wiki/concepts/` 또는 적절한 위치에 요약 페이지 작성/갱신 | 신규 또는 갱신된 마크다운 페이지 |
| 4. **index 업데이트** | `wiki/index.md`에 새 페이지 항목 추가 또는 기존 항목 갱신 | `index.md` 갱신 |
| 5. **관련 페이지 갱신** | 영향받는 `decisions/`, `architecture/`, `phases/`, `glossary.md` 페이지 업데이트 및 cross-reference 추가 | 복수 페이지 갱신 |
| 6. **log 기록** | `wiki/log.md`에 항목 추가 (아래 prefix 규약 따름) | `log.md` 항목 추가 |

**원칙**: 단계를 건너뛰지 않는다. 특히 step 5 (관련 페이지 갱신)는 하나의 source가 10-15개 페이지에 영향을 줄 수 있다. step 6는 항상 마지막에 한다.

---

## 4. query 워크플로우

사용자 질문에 답할 때 wiki 탐색 순서.

| 단계 | 행동 |
|---|---|
| 1. **index.md 먼저** | `wiki/index.md` 읽기 → 관련 카테고리·페이지 식별 |
| 2. **drill** | 관련 페이지들을 순서대로 읽기. 필요하면 `raw/` source까지 내려감 |
| 3. **synthesize** | 읽은 내용을 종합하여 답변 작성. 출처 페이지를 `[[링크]]`로 인용 |
| 4. **file back** | 답변 자체가 새로운 통찰이라면 `wiki/concepts/` 또는 적절한 위치에 페이지로 저장하고 `index.md`, `log.md` 갱신 |

**원칙**: 추측으로 답하지 않는다. wiki에 없으면 없다고 말하고, ingest 후 답하거나 raw source를 찾아본다.

---

## 5. lint 워크플로우

주기적으로 (phase 완료 시, 또는 요청 시) wiki 건강 상태 점검.

점검 항목:

| 항목 | 설명 |
|---|---|
| **contradiction** | 두 페이지가 같은 사실에 대해 상충되는 내용을 담고 있는지 |
| **stale claim** | 이후 결정/구현이 무효화한 오래된 주장이 남아있는지 |
| **orphan page** | inbound link가 없는 페이지 (`index.md`와 다른 페이지에서 아무도 참조하지 않음) |
| **missing cross-reference** | 페이지 본문에서 언급되는 용어·개념 중 `[[link]]`가 누락된 것 |
| **undefined term** | `glossary.md`에 없는 도메인 용어가 사용된 경우 |
| **phase gap** | `phases/` 에 작업 노트가 없는 완료된 phase |

lint 결과는 `log.md`에 `lint` 타입으로 기록한다. 발견된 문제는 즉시 수정하거나 TODO로 남긴다.

---

## 6. log.md 항목 prefix 규약

`log.md`의 모든 항목은 다음 형식을 따른다:

```
## [YYYY-MM-DD] {ingest|decision|query|lint|phase} | <title>
```

| 타입 | 사용 시점 |
|---|---|
| `ingest` | raw source를 wiki에 통합한 경우 |
| `decision` | ADR이 작성되거나 기존 결정이 변경된 경우 |
| `query` | 답변을 wiki에 페이지로 file back한 경우 |
| `lint` | lint 워크플로우 실행 후 |
| `phase` | 개발 phase 시작 또는 완료 시 |

예시:

```markdown
## [2026-05-22] ingest | llm-wiki.md + local-agent-server-spec.md

llm-wiki 철학 및 초기 spec을 wiki/raw/에 이동하고 bootstrap ingest 완료.
영향 페이지: glossary.md, architecture/system-design.md, index.md

## [2026-05-25] phase | W0 bootstrap 완료

wiki 뼈대, ADR 5개, glossary 시드, 개정 spec 생성.
다음 단계: W0.5 검증 게이트 (OMC/cmux/Qwen 실측).
```

**log.md는 append-only다. 기존 항목을 수정하지 않는다.**

grep 활용: `grep "^## \[" wiki/log.md | tail -10` → 최근 10개 항목 확인.

---

## 7. ADR 형식

`wiki/decisions/NNNN-<slug>.md` 형식으로 저장. `NNNN`은 4자리 순번.

### frontmatter

```yaml
---
status: Accepted | Proposed | Deprecated | Superseded
date: YYYY-MM-DD
deciders: [dongmin]   # 인간 의사결정자. LLM 도구 (OMC 등) 를 함께 표기할지는 프로젝트 정책 — 본 repo는 인간만 표기
supersedes: ""
superseded-by: ""
---
```

### 본문 구조

```markdown
# NNNN: <제목>

## Context

왜 이 결정이 필요했는가. 배경 상황, 제약, 당시 알고 있던 것.

## Decision

무엇을 결정했는가. 1~2 문단으로 명확하게.

## Consequences

이 결정이 가져오는 영향 — 긍정적·부정적·중립적.
나중에 뒤집기 얼마나 어려운가.

## Alternatives considered

고려했지만 채택하지 않은 대안들. 각 대안을 거부한 이유.
```

예시 파일명: `wiki/decisions/0001-dev-wiki-as-bootstrap.md`

ADR 작성 후 `wiki/index.md`의 decisions 섹션에 1줄 추가하고, `log.md`에 `decision` 타입 항목을 기록한다.

---

## 8. glossary 형식

`wiki/glossary.md`의 모든 용어는 다음 형식을 따른다:

```markdown
### 용어명

정의 1~3 문장. 이 프로젝트의 맥락에서 어떤 의미인지 명확하게.
일반적 의미와 다르게 쓰인다면 그 차이를 명시.

관련 용어: [[용어A]], [[용어B]]
```

예시:

```markdown
### Manager

로컬에서 실행되는 경량 LLM (qwen3.5:9b Q4_K_M). 이슈를 한국어로 해석하고,
Worker용 영문 프롬프트를 구성하며, 승인 게이트와 가드레일을 집행한다.
코드를 직접 작성하지 않으며, PR 생성 권한을 가진다.

관련 용어: [[Worker]], [[가드레일]], [[L2 자율성]]

### dev-wiki

`wiki/` 디렉터리에 위치한 이 repo 자체의 빌드 노하우 wiki.
에이전트가 타겟 repo에 생성하는 [[target-repo wiki]]와 구분된다.

관련 용어: [[target-repo wiki]], [[llm-wiki]]
```

**glossary.md에 새 용어를 추가할 때는 `index.md`의 glossary 섹션도 갱신한다.**

---

## 9. phases/ 작업 노트 형식

각 phase 완료 시 `wiki/phases/w<n>-<name>.md` 작성.

```markdown
# W<n>: <phase 이름>

**기간**: YYYY-MM-DD ~ YYYY-MM-DD
**상태**: 완료 | 진행 중 | 취소

## 한 일

주요 산출물 목록.

## 흔들렸던 가정

처음 생각과 달랐던 것. 예상치 못한 장애물.

## 다음 phase로 넘기는 의문점

아직 답이 없는 것, 다음 phase에서 검증해야 할 것.

## 관련 ADR

이 phase에서 생성된 ADR 링크.
```

---

## 이 SCHEMA.md 갱신 방법

SCHEMA.md는 wiki가 성장하면서 함께 진화한다. 새 규약이 필요하거나 기존 규약이 잘못됐음이 드러나면:

1. 변경 이유를 사용자와 합의한다.
2. 이 파일을 수정한다.
3. `log.md`에 `ingest` 또는 `decision` 타입으로 변경 사항을 기록한다.

**SCHEMA.md는 `wiki/raw/`에 원본을 두지 않는다. 이 파일 자체가 진화하는 문서다.**
