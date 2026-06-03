"""W3 그래프 순수 로직 단위 테스트 (네트워크/cmux/gh 불필요).

LLM 노드(parse/assess/build)와 interrupt 루프는 E2E 스모크로 검증한다
(`e2e_w3.py`). 여기서는 결정적 로직만: assess 후 라우팅, clarification 본문 append,
그래프/체크포인터 구성, serde allowlist.

실행: python3 spike/w3/test_w3.py
"""

from __future__ import annotations

import sqlite3
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "w2"))
from manager_state import Issue, ManagerState, Sufficiency  # noqa: E402

import manager_graph_lg as mg  # noqa: E402


def _check(name, cond):
    if not cond:
        raise AssertionError(f"FAIL: {name}")
    print(f"  ok: {name}")


def _state(sufficient: bool) -> ManagerState:
    suf = Sufficiency(
        sufficient=sufficient,
        missing_ko=() if sufficient else ("무엇을 정리?", "어떤 형식?"),
        reason_ko="근거",
    )
    issue = Issue(number=11, title="Clean up NOTES.md", body="NOTES.md 좀 정리해줘", url="")
    return ManagerState(issue_ref="11", issue=issue, sufficiency=suf)


def test_route_after_assess():
    _check("sufficient→build", mg.route_after_assess(_state(True)) == "build")
    _check("insufficient→clarify", mg.route_after_assess(_state(False)) == "clarify")


def test_append_clarification():
    issue = _state(False).issue
    new = mg.append_clarification(issue, ("무엇을?", "형식?"), "중복 줄 제거, 제목만 남겨")
    _check("원본 불변", "clarification" not in issue.body)
    _check("질문 포함", "무엇을?" in new.body and "형식?" in new.body)
    _check("답변 포함", "중복 줄 제거, 제목만 남겨" in new.body)
    _check("기존 본문 보존", new.body.startswith("NOTES.md 좀 정리해줘"))
    _check("Issue 타입 유지", new.number == 11 and new.title == issue.title)


def test_allowlist():
    mods = dict(mg._ALLOWED_MSGPACK)
    _check("ManagerState 등록", ("manager_state", "ManagerState") in mg._ALLOWED_MSGPACK)
    _check("Issue/Intent/Sufficiency 등록",
           all(("manager_state", n) in mg._ALLOWED_MSGPACK for n in ("Issue", "Intent", "Sufficiency")))


def test_graph_builds():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
    from langgraph.checkpoint.sqlite import SqliteSaver

    saver = SqliteSaver(conn, serde=JsonPlusSerializer(allowed_msgpack_modules=mg._ALLOWED_MSGPACK))
    saver.setup()
    graph = mg.build_graph(saver)
    nodes = set(graph.get_graph().nodes)
    _check("노드 4개 존재", {"parse", "assess", "clarify", "build"} <= nodes)


def test_make_saver_tmp(tmp="/tmp/claude-501/_w3_test_ckpt.sqlite"):
    Path(tmp).unlink(missing_ok=True)
    saver = mg.make_saver(tmp)
    _check("SqliteSaver 생성", saver is not None)
    _check("db 파일 생성", Path(tmp).exists())
    Path(tmp).unlink(missing_ok=True)


if __name__ == "__main__":
    tests = [
        test_route_after_assess,
        test_append_clarification,
        test_allowlist,
        test_graph_builds,
        test_make_saver_tmp,
    ]
    for t in tests:
        print(f"\n{t.__name__}:")
        t()
    print(f"\n✅ 전체 {len(tests)}개 테스트 통과")
