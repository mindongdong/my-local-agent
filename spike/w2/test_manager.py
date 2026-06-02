"""W2 Manager 순수 로직 단위 테스트 (네트워크/cmux/gh 불필요).

LLM 호출(parse/assess/build의 qwen 부분)과 워커(cmux)는 E2E 스모크로 검증한다
(`e2e_w2.py`). 여기서는 **결정적 로직**만 본다: 키워드 라우팅, 상태 불변성,
코드측 JSON 검증, JSON 추출 견고성. qwen 규약(`spike/w1`)과 같은 스타일.

실행: python3 spike/w2/test_manager.py
"""

from __future__ import annotations

import build_prompt as bp
import parse_issue as pi
import assess_sufficiency as asf
import qwen
from manager_state import Intent, Issue, ManagerState


def _check(name, cond):
    if not cond:
        raise AssertionError(f"FAIL: {name}")
    print(f"  ok: {name}")


def test_keyword_routing():
    _check("feature→autopilot:", bp.select_keyword("feature") == "autopilot:")
    _check("bugfix→autopilot:", bp.select_keyword("bugfix") == "autopilot:")
    _check("refactor→ralph:", bp.select_keyword("refactor") == "ralph:")
    _check("docs→raw", bp.select_keyword("docs") == "")
    _check("unknown→raw", bp.select_keyword("???") == "")


def test_state_immutability():
    from dataclasses import replace

    s0 = ManagerState(issue_ref="9")
    s1 = replace(s0, keyword="autopilot:")
    _check("원본 불변", s0.keyword is None)
    _check("새 상태 반영", s1.keyword == "autopilot:")
    _check("frozen 강제", _raises(lambda: setattr(s0, "keyword", "x")))


def test_issue_number_parsing():
    _check("'9'→9", pi._issue_number("9") == "9")
    _check("'#9'→9", pi._issue_number("#9") == "9")
    _check("URL→9", pi._issue_number("https://github.com/o/r/issues/9") == "9")
    _check("없으면 에러", _raises(lambda: pi._issue_number("no-number")))


def test_intent_validate():
    good = {"summary_ko": "요약", "task_type": "Feature", "target_hint": ""}
    intent = pi._validate(good)
    _check("정상 파싱", isinstance(intent, Intent))
    _check("task_type 소문자 정규화", intent.task_type == "feature")
    _check("잘못된 task_type 거부", _raises(lambda: pi._validate({**good, "task_type": "bogus"})))
    _check("키 누락 거부", _raises(lambda: pi._validate({"summary_ko": "x"})))


def test_sufficiency_validate():
    ok = {"sufficient": True, "missing_ko": [], "reason_ko": "명확"}
    suf = asf._validate(ok)
    _check("충분 파싱", suf.sufficient is True and suf.missing_ko == ())
    bad = {"sufficient": True, "missing_ko": [], "reason_ko": "x"}
    _check("배열 missing 변환", asf._validate({**bad, "missing_ko": ["q1", "q2"]}).missing_ko == ("q1", "q2"))
    _check("sufficient 비-bool 거부", _raises(lambda: asf._validate({**ok, "sufficient": "yes"})))
    _check("missing 비-배열 거부", _raises(lambda: asf._validate({**ok, "missing_ko": "x"})))


def test_build_validate():
    _check("en_prompt 추출", bp._validate({"en_prompt": " do X "}) == "do X")
    _check("빈 en_prompt 거부", _raises(lambda: bp._validate({"en_prompt": "  "})))
    _check("키 누락 거부", _raises(lambda: bp._validate({})))


def test_extract_json():
    _check("순수 JSON", qwen.extract_json('{"a": 1}') == {"a": 1})
    _check("코드펜스 제거", qwen.extract_json('```json\n{"a": 1}\n```') == {"a": 1})
    _check("잡텍스트 앞뒤", qwen.extract_json('설명...\n{"a": 1}\n끝') == {"a": 1})
    _check("중첩 균형", qwen.extract_json('{"a": {"b": 2}} 뒤쪽 무시') == {"a": {"b": 2}})
    _check("객체 없으면 에러", _raises(lambda: qwen.extract_json("no json here")))


def _raises(fn) -> bool:
    try:
        fn()
        return False
    except Exception:
        return True


if __name__ == "__main__":
    tests = [
        test_keyword_routing,
        test_state_immutability,
        test_issue_number_parsing,
        test_intent_validate,
        test_sufficiency_validate,
        test_build_validate,
        test_extract_json,
    ]
    for t in tests:
        print(f"\n{t.__name__}:")
        t()
    print(f"\n✅ 전체 {len(tests)}개 테스트 통과")
