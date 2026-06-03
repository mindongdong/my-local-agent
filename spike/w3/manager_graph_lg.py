"""W3 Manager 그래프 (LangGraph 전환 + interrupt#1 + SQLite checkpointer).

W2의 순수 함수 3노드(parse_issue/assess_sufficiency/build_prompt)를 **수정 없이**
LangGraph 노드로 등록하고, W2가 연기했던 분기·interrupt·checkpointer를 얹는다.

  START → parse → assess ─┬─ sufficient ──→ build → END
                          └─ insufficient → clarify(interrupt#1)
                                 ↑________________ 답변 → assess (재판단)

정보 부족 처리: `clarify` 노드가 `interrupt(질문)`로 일시정지 → 사용자 답변을
**이슈 본문에 Q&A로 append** → assess 재실행. 이러면 W2의 assess/build가 더 풍부한
본문을 그대로 읽어 노드를 수정할 필요가 없다(상태에 새 필드 추가 없이 재사용).

체크포인터: SqliteSaver. interrupt 경계에서 상태를 SQLite에 직렬화 → 재개 시 복원.
W2 dataclass(ManagerState/Issue/Intent/Sufficiency)를 그래프 state로 그대로 쓰되,
serde allowlist에 등록해 future-proof(미등록 커스텀 타입 경고/차단 회피).
"""

from __future__ import annotations

import sqlite3
import sys
from dataclasses import replace
from pathlib import Path

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

# W2 노드/타입 재사용 (스파이크 경로 주입)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "w2"))
from assess_sufficiency import assess_sufficiency  # noqa: E402
from build_prompt import build_prompt  # noqa: E402
from manager_state import ManagerState  # noqa: E402
from parse_issue import parse_issue  # noqa: E402

# 체크포인트 직렬화 허용 모듈 (W2 dataclass가 `manager_state` 모듈 소속)
_ALLOWED_MSGPACK = [("manager_state", name) for name in ("ManagerState", "Issue", "Intent", "Sufficiency")]


# --- LangGraph 노드 래퍼: W2 순수 함수를 호출하고 변경 필드만 델타로 반환 ---

def n_parse(state: ManagerState) -> dict:
    ns = parse_issue(state)
    return {"issue": ns.issue, "intent": ns.intent}


def n_assess(state: ManagerState) -> dict:
    ns = assess_sufficiency(state)
    return {"sufficiency": ns.sufficiency}


def n_build(state: ManagerState) -> dict:
    ns = build_prompt(state)
    return {"keyword": ns.keyword, "en_prompt": ns.en_prompt}


def append_clarification(issue, questions, answer: str):
    """이슈 본문에 Q&A 한 묶음을 append한 새 Issue 반환(불변). 순수 함수(테스트 용이)."""
    qa = "Q: " + " / ".join(questions) + f"\nA: {answer}"
    return replace(issue, body=f"{issue.body}\n\n[clarification]\n{qa}")


def n_clarify(state: ManagerState) -> dict:
    """interrupt#1: 한국어 질문으로 일시정지 → 답변을 이슈 본문에 append → 재assess."""
    payload = {
        "questions": list(state.sufficiency.missing_ko),
        "reason": state.sufficiency.reason_ko,
    }
    answer = interrupt(payload)  # 재개 시 Command(resume=answer)의 값이 반환됨
    new_issue = append_clarification(state.issue, state.sufficiency.missing_ko, answer)
    return {"issue": new_issue}


def route_after_assess(state: ManagerState) -> str:
    return "build" if state.sufficiency.sufficient else "clarify"


def build_graph(checkpointer):
    """컴파일된 Manager 그래프 반환."""
    g = StateGraph(ManagerState)
    g.add_node("parse", n_parse)
    g.add_node("assess", n_assess)
    g.add_node("clarify", n_clarify)
    g.add_node("build", n_build)
    g.add_edge(START, "parse")
    g.add_edge("parse", "assess")
    g.add_conditional_edges("assess", route_after_assess, {"build": "build", "clarify": "clarify"})
    g.add_edge("clarify", "assess")
    g.add_edge("build", END)
    return g.compile(checkpointer=checkpointer)


def make_saver(db_path: str) -> SqliteSaver:
    """파일 기반 SqliteSaver (allowlist serde). 상위 디렉터리 자동 생성."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    serde = JsonPlusSerializer(allowed_msgpack_modules=_ALLOWED_MSGPACK)
    saver = SqliteSaver(conn, serde=serde)
    saver.setup()
    return saver
