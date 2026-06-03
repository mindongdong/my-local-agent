"""W3 E2E (CLI) — interrupt#1 정보 부족 루프를 결정적으로 증명.

흐름:
  이슈(#n) → LangGraph(parse→assess) → 정보 부족 시 interrupt(질문)
    → [CLI] 답변 입력(--answer 또는 stdin) → Command(resume) → 재assess
    → 충분해지면 build → [W1 척추] cmux 워커 → diff → qwen 한국어 요약

Discord thread reply↔resume 어댑터는 PR-b. 여기선 입출력이 CLI일 뿐,
interrupt/resume/checkpointer 기계장치는 동일하다(상태는 SQLite에 체크포인트).

사용:
  python3 spike/w3/e2e_w3.py 11                      # 대화형(질문 시 stdin)
  python3 spike/w3/e2e_w3.py 11 --answer "중복 줄 제거, 제목만" --dry
  python3 spike/w3/e2e_w3.py 11 --answer "..." --answer "..."   # 라운드별 답변

전제: ollama+qwen3.5:9b, gh 인증. --dry가 아니면 cmux 터미널 안에서 실행.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from langgraph.types import Command

HERE = Path(__file__).resolve().parent
# W1 척추(워커/요약) + manager_graph_lg(자체적으로 w2 주입)
sys.path.insert(0, str(HERE.parent / "w1"))
import cmux_session as cs  # noqa: E402
import qwen_summarize as qs  # noqa: E402
import worker_spawn as ws  # noqa: E402

from manager_graph_lg import build_graph, make_saver  # noqa: E402

SEED = {"NOTES.md": "# Notes\n\n- 첫 줄\n- 첫 줄\n- 둘째 줄\n"}  # 중복 줄 포함(정리 작업 대상)
MAX_ROUNDS = 3
DB_PATH = str(HERE / "data" / "checkpoints.sqlite")


def make_answer_fn(scripted: list[str]):
    """질문 payload를 출력하고 답변 반환. 스크립트 소진 시 stdin."""
    queue = list(scripted)

    def fn(payload: dict) -> str:
        print("  ⏸ interrupt#1 — 정보 부족:")
        print(f"     근거: {payload.get('reason', '')}")
        for i, q in enumerate(payload.get("questions", []), 1):
            print(f"     {i}. {q}")
        if queue:
            ans = queue.pop(0)
            print(f"     [answer<scripted>] {ans}")
        else:
            ans = input("     [answer> ] ").strip()
        return ans

    return fn


def _intent(state) -> str:
    it = state.get("intent")
    return f"{it.task_type} | {it.summary_ko}" if it else "(없음)"


def run(issue_ref: str, *, dry: bool, scripted: list[str]) -> int:
    print("=" * 60)
    print("W3 E2E — interrupt#1 정보 부족 루프 (LangGraph + SQLite checkpointer)")
    print("=" * 60)

    saver = make_saver(DB_PATH)
    graph = build_graph(saver)
    # 재실행 충돌 방지를 위해 thread_id에 실행 시각 포함(파일 db는 유지됨 = 체크포인트 증명)
    thread_id = f"issue-{issue_ref}-{int(time.time())}"
    cfg = {"configurable": {"thread_id": thread_id}}
    answer_fn = make_answer_fn(scripted)
    print(f"[graph] thread_id={thread_id}  db={DB_PATH}")

    state = graph.invoke({"issue_ref": str(issue_ref)}, cfg)
    print(f"[parse] #{state['issue'].number} {state['issue'].title!r}  intent={_intent(state)}")

    rounds = 0
    while state.get("__interrupt__"):
        suf = state["sufficiency"]
        print(f"[assess] sufficient={suf.sufficient} — {suf.reason_ko}")
        if rounds >= MAX_ROUNDS:
            print(f"[abort] {MAX_ROUNDS}라운드 후에도 정보 부족 — 중단(실운영은 계속 질문/타임아웃).")
            return 3
        answer = answer_fn(state["__interrupt__"][0].value)
        state = graph.invoke(Command(resume=answer), cfg)
        rounds += 1

    suf = state["sufficiency"]
    print(f"[assess] sufficient={suf.sufficient} — {suf.reason_ko}  (clarify {rounds}라운드)")
    print(f"[build] keyword={state.get('keyword') or '(raw)'}")
    print(f"[build] EN prompt: {state['en_prompt']}")

    if dry:
        print("\n[--dry] Manager 단계까지만. 워커 생략.")
        return 0

    # --- W1 척추 인서트 ---
    me = cs.identify()
    root = ws.prepare_workspace(SEED)
    print(f"\n[worker] {me['workspace']}/{me['surface']}  ws={root}")
    t = time.time()
    res = ws.run_worker(root, state["en_prompt"], window=me["window"], timeout=180)
    print(f"[worker] done exit={res.exit_code}, {time.time()-t:.1f}s")
    if not res.diff.strip():
        print("[!] 변경 없음. screen tail:")
        print(res.screen_tail)
        return 1
    print(f"[worker] diff {len(res.diff)}B")

    print("[summarize] qwen 한국어 요약 ...")
    summary = qs.summarize_diff(res.diff)
    print("\n" + "─" * 60)
    print(f"📋 이슈 #{state['issue'].number}: {state['issue'].title}")
    print("─" * 60)
    print(f"변경 요약: {summary.summary_ko}")
    print(f"변경 파일: {', '.join(summary.files_changed)}")
    print(f"리스크: {summary.risk_ko}")
    print("─" * 60)
    return 0


def _parse_args(argv: list[str]) -> tuple[str | None, bool, list[str]]:
    issue_ref: str | None = None
    dry = False
    answers: list[str] = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--dry":
            dry = True
        elif a == "--answer":
            i += 1
            answers.append(argv[i] if i < len(argv) else "")
        elif not a.startswith("--"):
            issue_ref = a
        i += 1
    return issue_ref, dry, answers


if __name__ == "__main__":
    ref, dry_flag, scripted_answers = _parse_args(sys.argv[1:])
    if not ref:
        print("사용: python3 spike/w3/e2e_w3.py <issue_number> [--answer TEXT]... [--dry]")
        raise SystemExit(64)
    raise SystemExit(run(ref, dry=dry_flag, scripted=scripted_answers))
