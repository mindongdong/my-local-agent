"""cmux 0.64.10 세션 제어 래퍼 (W1 tracer-bullet).

W0.5 Mac Mini 재측정에서 확정한 교정 API를 코드로 고정한다:
  1. send/read-screen은 `--surface surface:N`에 `--window window:K` 컨텍스트 필수.
     (짧은 ref는 window-scoped index라 모호 → window 없이는 "Surface is not a terminal".)
  2. 기본 new-workspace는 비-터미널(welcome) surface → 터미널은 `--layout`으로 명시 spawn.
  3. close-workspace로 토폴로지 비파괴 복구.

설계 원칙: 입력은 경계에서 검증, cmux 오류는 명시적 예외로 승격(조용히 삼키지 않음),
불변 데이터(SurfaceRef는 frozen). 한 모듈 = 한 책임(cmux 제어).
"""

from __future__ import annotations

import json
import re
import subprocess
import time
from dataclasses import dataclass

CMUX = "cmux"
_REF_RE = re.compile(r"(workspace|surface|window):\d+")


class CmuxError(RuntimeError):
    """cmux CLI가 0이 아닌 종료코드 또는 오류 메시지를 반환."""


@dataclass(frozen=True)
class SurfaceRef:
    """터미널 surface를 가리키는 불변 핸들. send/read에 필요한 3-튜플을 함께 보관."""

    workspace: str  # e.g. "workspace:5"
    surface: str    # e.g. "surface:5"
    window: str     # e.g. "window:1"


def _run(args: list[str], timeout: float = 15.0) -> str:
    """cmux 명령 1회 실행 → stdout(strip). 오류 시 CmuxError."""
    try:
        proc = subprocess.run(
            [CMUX, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:  # cmux not on PATH
        raise CmuxError(f"cmux 실행 파일을 찾을 수 없음 (PATH 확인): {exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise CmuxError(f"cmux {' '.join(args)} timeout({timeout}s)") from exc

    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    # cmux는 일부 오류를 stdout에 "Error: ..."로 출력하기도 한다.
    if proc.returncode != 0 or out.startswith("Error:") or err.startswith("Error:"):
        raise CmuxError(f"cmux {' '.join(args)} 실패: rc={proc.returncode} out={out!r} err={err!r}")
    return out


def _first_ref(text: str, kind: str) -> str:
    """text에서 첫 `{kind}:N` ref 추출. 없으면 CmuxError."""
    for m in _REF_RE.finditer(text):
        if m.group(0).startswith(kind + ":"):
            return m.group(0)
    raise CmuxError(f"{kind} ref를 찾지 못함: {text!r}")


def identify() -> dict:
    """caller(=이 프로세스가 속한 surface)의 위치를 반환.

    반환: {"window": "window:1", "workspace": "workspace:2", "surface": "surface:2"}
    """
    raw = _run(["identify", "--json"])
    data = json.loads(raw)
    caller = data.get("caller") or data.get("focused")
    if not caller:
        raise CmuxError(f"identify 결과에 caller/focused 없음: {raw!r}")
    return {
        "window": caller["window_ref"],
        "workspace": caller["workspace_ref"],
        "surface": caller["surface_ref"],
    }


def spawn_terminal(name: str, window: str, command: str = "zsh", cwd: str | None = None) -> SurfaceRef:
    """터미널 surface를 가진 새 워크스페이스를 비포커스로 spawn.

    교정 API: 기본 new-workspace는 비-터미널이므로 --layout으로 터미널 surface 명시.
    """
    if not name:
        raise ValueError("name은 비어 있을 수 없음")
    surfaces: dict = {"type": "terminal", "command": command}
    if cwd:
        surfaces["cwd"] = cwd
    layout = json.dumps({"pane": {"surfaces": [surfaces]}})

    out = _run(["new-workspace", "--name", name, "--focus", "false", "--layout", layout])
    ws = _first_ref(out, "workspace")

    # surface ref는 spawn 직후 조회 (짧은 재시도로 레이스 방지)
    surface = _list_surface(ws)
    return SurfaceRef(workspace=ws, surface=surface, window=window)


def _list_surface(workspace: str, retries: int = 5, delay: float = 0.2) -> str:
    last = ""
    for _ in range(retries):
        last = _run(["list-pane-surfaces", "--workspace", workspace])
        try:
            return _first_ref(last, "surface")
        except CmuxError:
            time.sleep(delay)
    raise CmuxError(f"{workspace}의 surface를 찾지 못함: {last!r}")


def send(ref: SurfaceRef, text: str) -> None:
    """텍스트를 surface에 입력(Enter는 별도). --window 컨텍스트 포함(교정 API)."""
    _run(["send", "--surface", ref.surface, "--window", ref.window, text])


def send_enter(ref: SurfaceRef) -> None:
    _run(["send-key", "--surface", ref.surface, "--window", ref.window, "enter"])


def read_screen(ref: SurfaceRef, lines: int | None = None) -> str:
    args = ["read-screen", "--surface", ref.surface, "--window", ref.window]
    if lines is not None:
        args += ["--lines", str(lines)]
    return _run(args)


def close(ref: SurfaceRef) -> None:
    """워크스페이스 종료 → 토폴로지 비파괴 복구."""
    _run(["close-workspace", "--workspace", ref.workspace])


def run_command(
    ref: SurfaceRef,
    cmd: str,
    expect: str,
    timeout: float = 10.0,
    poll: float = 0.2,
) -> str:
    """cmd를 보내고 화면에서 `expect`(정규식, MULTILINE)가 나타날 때까지 폴링.

    반환: expect가 매칭된 시점의 화면 텍스트. 실패 시 TimeoutError.
    """
    pattern = re.compile(expect, re.MULTILINE)
    send(ref, cmd)
    send_enter(ref)
    deadline = time.time() + timeout
    screen = ""
    while time.time() < deadline:
        time.sleep(poll)
        screen = read_screen(ref)
        if pattern.search(screen):
            return screen
    raise TimeoutError(f"expect {expect!r} 미발견 (timeout {timeout}s). last screen tail:\n{screen[-400:]}")
