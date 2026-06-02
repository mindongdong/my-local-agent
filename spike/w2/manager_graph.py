"""Manager 파이프라인 러너 (W2: 순수 함수 순차 실행).

  parse_issue → assess_sufficiency → [충분하면] build_prompt

LangGraph는 W3에서 도입한다(분기·interrupt·checkpointer가 그때 필요). 각 노드는
`ManagerState -> ManagerState` 순수 함수라, W3에서는 이 셋을 그대로 LangGraph
노드로 등록하고 `assess → interrupt#1 → build` 분기/체크포인트만 얹으면 된다.

정보 부족(sufficient=false) 시 build_prompt를 건너뛰고 상태를 그대로 반환한다.
호출측이 `state.sufficiency.missing_ko`(한국어 질문)를 사용자에게 전달한다 —
W2는 출력 후 중단, W3에서 interrupt#1 + resume으로 루프.
"""

from __future__ import annotations

from assess_sufficiency import assess_sufficiency
from build_prompt import build_prompt
from manager_state import ManagerState
from parse_issue import parse_issue


def run_manager(issue_ref: str, *, log=print) -> ManagerState:
    """이슈 참조 → Manager 두뇌 파이프라인 → 최종 상태."""
    state = ManagerState(issue_ref=issue_ref)

    state = parse_issue(state)
    log(f"[parse_issue] #{state.issue.number} {state.issue.title!r}")
    log(f"             의도(ko): {state.intent.summary_ko}")
    log(f"             task_type: {state.intent.task_type} | 대상 힌트: {state.intent.target_hint or '(없음)'}")

    state = assess_sufficiency(state)
    log(f"[assess_sufficiency] sufficient={state.sufficiency.sufficient} — {state.sufficiency.reason_ko}")
    if not state.sufficiency.sufficient:
        log(f"             부족 정보: {list(state.sufficiency.missing_ko)}")
        return state

    state = build_prompt(state)
    log(f"[build_prompt] keyword={state.keyword or '(raw)'}")
    log(f"             EN prompt: {state.en_prompt}")
    return state
