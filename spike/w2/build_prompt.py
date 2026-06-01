"""build_prompt 노드 — OMC용 영문 작업 명세 빌드 + magic keyword 라우팅 (Manager).

두 가지를 만든다:
  1. keyword — task_type → OMC magic keyword (결정적, system-design §3 라우팅 표).
  2. en_prompt — 한국어 이슈를 워커가 바로 쓸 영문 작업 명세로 (qwen).

W2 스코프 메모: 실제 OMC keyword **호출**(`invoke_omc_autopilot` 노드)은 W2 조각이
아니다. W2는 keyword를 **선택·기록**만 하고, E2E는 W1에서 검증된 평문 `claude -p`
경로에 en_prompt를 인서트한다. keyword 실주입은 invoke_omc 노드(차기)에서.
"""

from __future__ import annotations

from dataclasses import replace

import qwen
from manager_state import ManagerState

# system-design §3 "task type 별 magic keyword 라우팅" 표 (Manager가 결정).
# 빈 문자열 = raw prompt(키워드 없음).
KEYWORD_BY_TASK = {
    "feature": "autopilot:",   # 계획 분해 + 실행 + 검증 자동
    "bugfix": "autopilot:",
    "refactor": "ralph:",      # 자율 루프, verifier 강함
    "docs": "",                # 단순 문서 — raw
    "chore": "",
}


def select_keyword(task_type: str) -> str:
    """task_type → OMC magic keyword (없으면 빈 문자열)."""
    return KEYWORD_BY_TASK.get(task_type, "")


_PROMPT = """\
You translate a software task (written in Korean) into a precise English work
specification for a coding agent. Output **exactly this JSON structure** and
nothing else — no prose, no markdown code fences.

{{
  "en_prompt": "A clear, imperative English work spec the coding agent can act on directly. State what to change and where. Keep it tight."
}}

Rules:
- Use exactly the one key: en_prompt.
- en_prompt must be in English, imperative, self-contained.
- Do not invent requirements beyond the issue. Constrain scope: change only what the issue asks.

=== Issue #{number}: {title} ===
{body}
=== Korean intent ===
{intent_ko}
=== target hint ===
{target_hint}
=== end ===
"""


def _validate(obj: dict) -> str:
    if "en_prompt" not in obj:
        raise qwen.QwenError(f"필수 키 누락: en_prompt (받은 키: {list(obj)})")
    en = str(obj["en_prompt"]).strip()
    if not en:
        raise qwen.QwenError("en_prompt가 비어 있음")
    return en


def build_prompt(state: ManagerState) -> ManagerState:
    """영문 작업 명세 + keyword 선택 → 새 상태 반환."""
    if state.issue is None or state.intent is None:
        raise RuntimeError("parse_issue가 먼저 실행돼야 함 (issue/intent 없음)")
    prompt = _PROMPT.format(
        number=state.issue.number,
        title=state.issue.title,
        body=state.issue.body,
        intent_ko=state.intent.summary_ko,
        target_hint=state.intent.target_hint or "(none specified)",
    )
    en_prompt = qwen.generate_json(prompt, _validate)
    keyword = select_keyword(state.intent.task_type)
    return replace(state, en_prompt=en_prompt, keyword=keyword)
