"""cmux 안에서 비대화형 코드 워커 구동 + diff 캡처 (W1 piece, OMC 워커 PoC).

E2E 척추의 핵심 미검증 부분: cmux 터미널 surface에서 claude headless 워커를
띄워 하드코딩 영문 프롬프트로 작은 코드 변경을 시키고, git diff를 캡처한다.

안전 원칙 (W0.5 / L2 자율성 규약):
  - 격리: 워커는 임시 작업 repo(/tmp)에서 작업 — 스파이크 repo를 건드리지 않음.
  - --dangerously-skip-permissions 금지(글로벌 룰). --permission-mode acceptEdits 사용.
  - 완료 감지: sentinel `__W1_DONE__<exit>__` 로 결정적 판정 (화면 텍스트 추측 금지).
  - gh CLI 미사용(PR은 Manager 책임) — diff만 캡처.

claude -p가 cmux TUI 안에서 도는지(W0.5에서 미룬 "autopilot 단발 호출 안정성")를 확인.
"""

from __future__ import annotations

import re
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import cmux_session as cs

WORKER_CMD = "claude"
PERMISSION_MODE = "acceptEdits"
SENTINEL = "__W1_DONE__"
_SENTINEL_RE = rf"{SENTINEL}(\d+)__"


class WorkerError(RuntimeError):
    pass


@dataclass(frozen=True)
class WorkerResult:
    """워커 실행 결과(불변)."""

    workspace_cwd: str
    exit_code: int
    diff: str
    screen_tail: str


def prepare_workspace(seed_files: dict[str, str]) -> Path:
    """임시 git repo 생성 + 시드 파일 커밋. 경로 반환."""
    if not seed_files:
        raise ValueError("seed_files는 비어 있을 수 없음")
    root = Path(tempfile.mkdtemp(prefix="w1-worker-"))
    for rel, content in seed_files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "w1-worker@local")
    _git(root, "config", "user.name", "w1-worker")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "seed")
    return root


def _git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        raise WorkerError(f"git {' '.join(args)} 실패: {proc.stderr.strip()!r}")
    return proc.stdout


def run_worker(
    cwd: Path,
    prompt: str,
    window: str,
    timeout: float = 180.0,
) -> WorkerResult:
    """cmux 터미널 surface(cwd=임시repo)에서 claude -p 워커 실행 → diff 캡처.

    완료는 sentinel로 감지. 프롬프트는 파일로 전달해 셸 escaping 회피.
    """
    prompt_file = cwd / ".w1_prompt.txt"
    prompt_file.write_text(prompt, encoding="utf-8")

    ref = cs.spawn_terminal(name="w1-worker", window=window, command="zsh", cwd=str(cwd))
    try:
        # claude headless 실행 후 sentinel echo (exit code 포함). 한 줄 명령.
        # 프롬프트 내용은 파일에 있으므로 이 명령줄엔 특수문자 없음.
        cmd = (
            f'{WORKER_CMD} --permission-mode {PERMISSION_MODE} '
            f'-p "$(cat {prompt_file.name})" ; echo {SENTINEL}$?__'
        )
        screen = cs.run_command(ref, cmd, expect=_SENTINEL_RE, timeout=timeout, poll=1.0)
        m = re.search(_SENTINEL_RE, screen)
        exit_code = int(m.group(1)) if m else -1

        # 워커가 만든 산출물 추적 (.w1_prompt.txt는 노이즈라 제외)
        diff = _git(cwd, "diff", "--", ".", ":(exclude).w1_prompt.txt")
        if not diff.strip():
            # staged/untracked까지 포함해 한 번 더 (새 파일 대비)
            _git(cwd, "add", "-A")
            diff = _git(cwd, "diff", "--cached", "--", ".", ":(exclude).w1_prompt.txt")
        return WorkerResult(
            workspace_cwd=str(cwd),
            exit_code=exit_code,
            diff=diff,
            screen_tail=screen[-600:],
        )
    finally:
        cs.close(ref)
