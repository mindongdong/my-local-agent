"""W2 Manager 상태 + 값 객체 (모두 불변).

LangGraph는 W3에서 도입(checkpointer/interrupt가 그때 필요). W2는 노드를
`ManagerState -> ManagerState` 순수 함수로 쓰고, 각 노드는 `dataclasses.replace`로
**새 상태를 반환**한다(코딩 규약: 제자리 변경 금지). 이 시그니처는 W3에서 동일
함수를 LangGraph 노드로 그대로 등록할 수 있게 맞춰져 있다.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Issue:
    """GitHub 이슈 (gh로 fetch한 원본)."""

    number: int
    title: str
    body: str
    url: str


@dataclass(frozen=True)
class Intent:
    """이슈에 대한 한국어 의도 파악 결과 (parse_issue 산출)."""

    summary_ko: str   # 이슈가 원하는 것 한국어 1~2문장
    task_type: str    # feature|bugfix|refactor|docs|chore — build_prompt 키워드 라우팅용
    target_hint: str  # 변경 대상 파일/위치 힌트 (없으면 "")


@dataclass(frozen=True)
class Sufficiency:
    """정보 충분성 판단 결과 (assess_sufficiency 산출)."""

    sufficient: bool
    missing_ko: tuple[str, ...]  # 부족 시 한국어 질문 목록 (충분하면 빈 튜플)
    reason_ko: str               # 판단 근거 한 줄


@dataclass(frozen=True)
class ManagerState:
    """Manager 파이프라인의 누적 상태 (노드마다 새 인스턴스로 교체)."""

    issue_ref: str                       # 입력: "9" | "#9" | 이슈 URL
    issue: Issue | None = None           # parse_issue
    intent: Intent | None = None         # parse_issue
    sufficiency: Sufficiency | None = None  # assess_sufficiency
    keyword: str | None = None           # build_prompt: OMC magic keyword (없으면 "")
    en_prompt: str | None = None         # build_prompt: OMC용 영문 작업 명세
