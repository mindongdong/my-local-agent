"""W1 E2E tracer-bullet (Discord 제외, 로컬 CLI 버전).

흐름 (wiki/phases/w1-handoff.md §7):
  [입력 어댑터: stdin/하드코딩]  →  cmux claude 워커 구동  →  git diff 캡처
  →  qwen3.5:9b 한국어 요약  →  [출력 어댑터: stdout]

Discord 양끝(1,5)은 토큰 준비 후 입출력 어댑터만 교체하면 됨 — 척추는 이 파일이 증명.

사용:
  python3 spike/w1/e2e_local.py            # 기본 하드코딩 작업
  python3 spike/w1/e2e_local.py "Append a TODO line to NOTES.md"
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import cmux_session as cs
import qwen_summarize as qs
import worker_spawn as ws

# 하드코딩 데모 작업 (영문 prompt — W1은 prompt 하드코딩 단계)
DEFAULT_PROMPT = (
    "Append one short English haiku about the ocean (exactly 3 lines) "
    "to the end of NOTES.md. Do not create or modify any other file."
)
SEED = {"NOTES.md": "# Notes\n\n"}


def run(prompt: str) -> int:
    print("=" * 60)
    print("W1 E2E tracer-bullet (local CLI)")
    print("=" * 60)

    me = cs.identify()
    print(f"[1] caller surface: {me['workspace']}/{me['surface']}")

    # --- cmux 워커 구동 + diff 캡처 ---
    root = ws.prepare_workspace(SEED)
    print(f"[2] isolated workspace: {root}")
    print(f"[3] spawning claude worker in cmux ... (prompt: {prompt[:50]}...)")
    t = time.time()
    res = ws.run_worker(root, prompt, window=me["window"], timeout=180)
    print(f"    worker done: exit={res.exit_code}, {time.time()-t:.1f}s")

    if not res.diff.strip():
        print("[!] 워커가 변경을 만들지 않음. screen tail:")
        print(res.screen_tail)
        return 1
    print(f"[4] captured diff ({len(res.diff)} bytes)")

    # --- Qwen 한국어 요약 ---
    print("[5] qwen3.5:9b 한국어 요약 중 ...")
    t = time.time()
    summary = qs.summarize_diff(res.diff)
    print(f"    summary done: {time.time()-t:.1f}s")

    # --- 출력 어댑터 (Discord 자리) ---
    print("\n" + "─" * 60)
    print("📋 변경 요약 (한국어)")
    print("─" * 60)
    print(f"요약: {summary.summary_ko}")
    print(f"변경 파일: {', '.join(summary.files_changed)}")
    print(f"리스크: {summary.risk_ko}")
    print("─" * 60)
    return 0


if __name__ == "__main__":
    user_prompt = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PROMPT
    raise SystemExit(run(user_prompt))
