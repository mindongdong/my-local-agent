"""assess_sufficiency 노드 — 정보 충분성 JSON 판단 (Manager).

9B Manager의 JSON 약점을 별도 노드 + 코드측 스키마 강제로 보완(system-design §2).
착수 가능 여부를 1차 판단한다. 부족하면 한국어 질문 목록을 담아 반환하고,
호출측(manager_graph)이 build_prompt를 건너뛴다. (interrupt 루프는 W3.)
"""

from __future__ import annotations

from dataclasses import replace

import qwen
from manager_state import ManagerState, Sufficiency


class AssessError(RuntimeError):
    pass


_PROMPT = """\
당신은 작업 착수 전 "정보가 충분한가"를 판단하는 시니어 엔지니어입니다.
아래 이슈와 의도 파악 결과를 보고, 코딩 워커가 **추가 질문 없이 바로 착수**할 수 있는지
판단해 **반드시 아래 JSON 구조 그대로** 출력하세요. 다른 텍스트·코드펜스 없이 JSON만.

{{
  "sufficient": true 또는 false,
  "missing_ko": ["부족한 정보를 묻는 한국어 질문 목록. 충분하면 빈 배열 []"],
  "reason_ko": "판단 근거 한국어 한 줄"
}}

판단 기준:
- 무엇을(what)·어디에(where) 변경할지가 명확하면 sufficient=true.
- 대상 파일/동작이 모호하거나 핵심 정보가 빠졌으면 sufficient=false + missing_ko에 질문.
- 과하게 깐깐하게 굴지 말 것: 작은 작업은 합리적 가정으로 착수 가능하면 true.

규칙:
- 키 이름을 정확히 위 3개(sufficient, missing_ko, reason_ko)로만 사용.
- sufficient는 JSON boolean. missing_ko는 배열. reason_ko는 한국어.

=== 이슈 #{number}: {title} ===
{body}
=== 의도 파악(한국어) ===
{intent_ko}
=== 끝 ===
"""


def _validate(obj: dict) -> Sufficiency:
    for key in ("sufficient", "missing_ko", "reason_ko"):
        if key not in obj:
            raise qwen.QwenError(f"필수 키 누락: {key} (받은 키: {list(obj)})")
    if not isinstance(obj["sufficient"], bool):
        raise qwen.QwenError(f"sufficient는 boolean이어야 함: {obj['sufficient']!r}")
    if not isinstance(obj["missing_ko"], list):
        raise qwen.QwenError(f"missing_ko는 배열이어야 함: {obj['missing_ko']!r}")
    return Sufficiency(
        sufficient=obj["sufficient"],
        missing_ko=tuple(str(x).strip() for x in obj["missing_ko"]),
        reason_ko=str(obj["reason_ko"]).strip(),
    )


def assess_sufficiency(state: ManagerState) -> ManagerState:
    """정보 충분성 판단 → 새 상태 반환."""
    if state.issue is None or state.intent is None:
        raise AssessError("parse_issue가 먼저 실행돼야 함 (issue/intent 없음)")
    prompt = _PROMPT.format(
        number=state.issue.number,
        title=state.issue.title,
        body=state.issue.body,
        intent_ko=state.intent.summary_ko,
    )
    sufficiency = qwen.generate_json(prompt, _validate)
    return replace(state, sufficiency=sufficiency)
