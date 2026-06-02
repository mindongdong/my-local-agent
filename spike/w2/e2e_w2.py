"""W2 E2E — Manager 두뇌화를 W1 척추에 인서트.

흐름:
  GitHub 이슈(#n)
    → [Manager 두뇌] parse_issue → assess_sufficiency → build_prompt   (W2 신규)
    → [W1 척추]      cmux claude 워커 → git diff → qwen 한국어 요약      (재사용)
    → stdout (Discord 자리)

W1과의 차이: 입력이 '하드코딩 영문 prompt'에서 '실제 GitHub 이슈 + Manager가
빌드한 영문 prompt'로 바뀐 것. 워커/요약 경로는 W1에서 검증된 것을 그대로 쓴다.

사용:
  python3 spike/w2/e2e_w2.py 9          # 이슈 #9를 fetch해서 E2E
  python3 spike/w2/e2e_w2.py 9 --dry    # Manager 단계만(워커 미실행) — cmux 불필요

전제: ollama + qwen3.5:9b 가동, gh 인증. --dry가 아니면 cmux 터미널 안에서 실행.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# W1 척추 헬퍼 재사용 (스파이크 경로 주입)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "w1"))
import cmux_session as cs  # noqa: E402
import qwen_summarize as qs  # noqa: E402
import worker_spawn as ws  # noqa: E402

from manager_graph import run_manager  # noqa: E402

# 워커 격리 repo 시드. 스파이크에선 이슈가 NOTES.md를 다루므로 그 파일을 시드한다
# (실운영에선 타겟 repo를 클론 — W1과 동일한 스파이크 스탠드인).
SEED = {"NOTES.md": "# Notes\n\n"}


def run(issue_ref: str, *, dry: bool) -> int:
    print("=" * 60)
    print("W2 E2E — Manager 두뇌화 (이슈 → 영문 prompt → 워커 → 한국어 요약)")
    print("=" * 60)

    # --- Manager 두뇌 (W2 신규) ---
    state = run_manager(issue_ref)

    if not state.sufficiency.sufficient:
        print("\n" + "─" * 60)
        print("⏸ 정보 부족 — 착수 보류 (W3에서 interrupt#1로 사용자에게 질문)")
        for i, q in enumerate(state.sufficiency.missing_ko, 1):
            print(f"  {i}. {q}")
        print("─" * 60)
        return 2

    if dry:
        print("\n[--dry] Manager 단계까지만 실행. 워커 생략.")
        return 0

    # --- W1 척추 인서트: 빌드된 영문 prompt를 cmux 워커에 ---
    me = cs.identify()
    print(f"\n[worker] caller surface: {me['workspace']}/{me['surface']}")
    root = ws.prepare_workspace(SEED)
    print(f"[worker] isolated workspace: {root}")
    print(f"[worker] spawning claude worker (keyword={state.keyword or 'raw'}) ...")
    t = time.time()
    res = ws.run_worker(root, state.en_prompt, window=me["window"], timeout=180)
    print(f"[worker] done: exit={res.exit_code}, {time.time()-t:.1f}s")

    if not res.diff.strip():
        print("[!] 워커가 변경을 만들지 않음. screen tail:")
        print(res.screen_tail)
        return 1
    print(f"[worker] captured diff ({len(res.diff)} bytes)")

    # --- qwen 한국어 요약 (W1 재사용) ---
    print("[summarize] qwen3.5:9b 한국어 요약 중 ...")
    t = time.time()
    summary = qs.summarize_diff(res.diff)
    print(f"[summarize] done: {time.time()-t:.1f}s")

    # --- 출력 어댑터 (Discord 자리) ---
    print("\n" + "─" * 60)
    print(f"📋 이슈 #{state.issue.number}: {state.issue.title}")
    print("─" * 60)
    print(f"의도(ko): {state.intent.summary_ko}")
    print(f"변경 요약: {summary.summary_ko}")
    print(f"변경 파일: {', '.join(summary.files_changed)}")
    print(f"리스크: {summary.risk_ko}")
    print("─" * 60)
    return 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--dry"]
    dry = "--dry" in sys.argv
    if not args:
        print("사용: python3 spike/w2/e2e_w2.py <issue_number> [--dry]")
        raise SystemExit(64)
    raise SystemExit(run(args[0], dry=dry))
