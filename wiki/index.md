# wiki/index.md — 카탈로그

> **시스템 정의** (2026-05-25 확정): "하나의 깃허브 레포지토리를 작업 공간으로 추적하는 로컬 에이전트 서버 기반의 에이전트 매니징 시스템" — 1.0은 단일 repo, 검증 완료 후 multi-repo 확장 도모. [decisions/0006-system-scope-single-repo.md](decisions/0006-system-scope-single-repo.md).
>
> dev-wiki 진입점. 미래 세션은 여기서 시작하라. 모든 페이지에 1줄 요약.
>
> *Last updated: 2026-05-30*

---

## 규약 / 형식

- [../CONTRIBUTING.md](../CONTRIBUTING.md) — git 워크플로우(TBD) + Conventional Commits + PR 규약 ([[ADR 0008]])
- [SCHEMA.md](SCHEMA.md) — wiki 디렉터리 구조, ingest/query/lint 워크플로우, log/ADR/glossary 형식 규약
- [glossary.md](glossary.md) — 도메인 용어 사전 (Manager, Worker, OMC, cmux, magic keyword, interrupt, L2 자율성, qwen3.5:9b, tracer-bullet, ...)
- [log.md](log.md) — 시계열 활동 로그 (ingest / decision / query / lint / phase)

---

## 원본 (immutable)

- [raw/local-agent-server-spec.md](raw/local-agent-server-spec.md) — 원본 에이전트 서버 spec (개정 전)
- [raw/llm-wiki.md](raw/llm-wiki.md) — llm-wiki 철학 원본
- [raw/grilling/2026-05-22-initial-grilling.md](raw/grilling/2026-05-22-initial-grilling.md) — 초기 그릴링 8개 결정 압축본

---

## 결정 (ADR)

- [decisions/0001-dev-wiki-as-bootstrap.md](decisions/0001-dev-wiki-as-bootstrap.md) — dev-wiki를 부트스트랩 단계에 통합
- [decisions/0002-omc-as-worker-runtime.md](decisions/0002-omc-as-worker-runtime.md) — Worker 실행을 OMC + cmux 조합으로 통일
- [decisions/0003-hybrid-manager-omc-split.md](decisions/0003-hybrid-manager-omc-split.md) — Manager / OMC 간 Hybrid 책임 분담
- [decisions/0004-qwen3.5-9b-as-manager.md](decisions/0004-qwen3.5-9b-as-manager.md) — Manager LLM으로 qwen3.5:9b 채택, Gemma 3n E4B는 fallback
- [decisions/0005-tracer-bullet-roadmap.md](decisions/0005-tracer-bullet-roadmap.md) — Layer-by-layer 대신 Tracer-bullet + W0.5 검증 게이트
- [decisions/0006-system-scope-single-repo.md](decisions/0006-system-scope-single-repo.md) — 시스템 범위는 단일 GitHub repo (1.0), 검증 후 multi-repo 확장 도모
- [decisions/0007-omc-validation-result.md](decisions/0007-omc-validation-result.md) — W0.5 검증 결과: **Go (헤드리스 전제)**, qwen3.5:9b + OMC + cmux 스택 유지, 모델 라우팅은 W1 연기
- [decisions/0008-git-workflow-tbd.md](decisions/0008-git-workflow-tbd.md) — Git 워크플로우로 Trunk-Based Development + Conventional Commits + PR 템플릿 채택

---

## 아키텍처

- [architecture/system-design.md](architecture/system-design.md) — 현재 시스템 설계 (원본 spec section 1~12 개정판, 항상 최신 상태 유지)

---

## Phase 노트

- [phases/w0.5-validation.md](phases/w0.5-validation.md) — W0.5 검증 게이트 **완료 (Go, 헤드리스 전제)**. 메모리(8.5GB binding) / cmux round-trip 300·100% / 동시 워커 / JSON 14·14·93% 측정. 모델 라우팅은 W1 연기.
- [phases/w1-handoff.md](phases/w1-handoff.md) — **W1 핸드오프** (다른 머신 → 타겟 Mac Mini). ⚠️ W0.5 실측은 다른 머신 → Mac Mini 환경 셋업 + 재검증 후 W1 착수. 운영 사실 distill + 시작 지시문 포함.

---

## 개념 페이지

> 필요 시 점진 생성. 현재는 ADR + glossary로 충분.

(아직 없음)
