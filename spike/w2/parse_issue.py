"""parse_issue 노드 — GitHub 이슈 fetch + 한국어 의도 파악 (Manager).

흐름:
  issue_ref("9"|"#9"|URL) → `gh issue view` JSON → qwen 한국어 의도 파싱(Intent).

L2 자율성 규약: 이 노드는 읽기 전용(gh issue view). 쓰기/PR 권한 없음.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import replace

import qwen
from manager_state import Intent, Issue, ManagerState

VALID_TASK_TYPES = ("feature", "bugfix", "refactor", "docs", "chore")


class ParseError(RuntimeError):
    pass


def _issue_number(issue_ref: str) -> str:
    """'9' | '#9' | '.../issues/9' → '9'."""
    ref = issue_ref.strip()
    m = re.search(r"(\d+)\s*$", ref)
    if not m:
        raise ParseError(f"이슈 번호를 못 찾음: {issue_ref!r}")
    return m.group(1)


def fetch_issue(issue_ref: str) -> Issue:
    """gh CLI로 이슈를 가져온다(읽기 전용)."""
    num = _issue_number(issue_ref)
    proc = subprocess.run(
        ["gh", "issue", "view", num, "--json", "number,title,body,url"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        raise ParseError(f"gh issue view {num} 실패: {proc.stderr.strip()!r}")
    data = json.loads(proc.stdout)
    return Issue(
        number=int(data["number"]),
        title=str(data.get("title", "")),
        body=str(data.get("body", "")),
        url=str(data.get("url", "")),
    )


_PROMPT = """\
당신은 GitHub 이슈를 읽고 한국어로 의도를 파악하는 시니어 엔지니어입니다.
아래 이슈를 읽고 **반드시 아래 JSON 구조 그대로** 출력하세요. 다른 텍스트·마크다운 코드펜스 없이 JSON만.

{{
  "summary_ko": "이 이슈가 무엇을 요구하는지 한국어 1~2문장",
  "task_type": "feature|bugfix|refactor|docs|chore 중 하나",
  "target_hint": "변경 대상 파일/위치 힌트. 명시 안 됐으면 빈 문자열"
}}

규칙:
- 키 이름을 정확히 위 3개(summary_ko, task_type, target_hint)로만 사용.
- summary_ko, target_hint는 한국어.
- task_type은 반드시 feature|bugfix|refactor|docs|chore 중 하나(소문자).

=== 이슈 #{number}: {title} ===
{body}
=== 이슈 끝 ===
"""


def _validate(obj: dict) -> Intent:
    for key in ("summary_ko", "task_type", "target_hint"):
        if key not in obj:
            raise qwen.QwenError(f"필수 키 누락: {key} (받은 키: {list(obj)})")
    task_type = str(obj["task_type"]).strip().lower()
    if task_type not in VALID_TASK_TYPES:
        raise qwen.QwenError(
            f"task_type은 {VALID_TASK_TYPES} 중 하나여야 함: {obj['task_type']!r}"
        )
    return Intent(
        summary_ko=str(obj["summary_ko"]).strip(),
        task_type=task_type,
        target_hint=str(obj["target_hint"]).strip(),
    )


def parse_issue(state: ManagerState) -> ManagerState:
    """이슈 fetch + 한국어 의도 파악 → 새 상태 반환."""
    issue = state.issue or fetch_issue(state.issue_ref)
    prompt = _PROMPT.format(number=issue.number, title=issue.title, body=issue.body)
    intent = qwen.generate_json(prompt, _validate)
    return replace(state, issue=issue, intent=intent)
