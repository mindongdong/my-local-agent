"""cmux_session 래퍼 셸 스모크 (W1 piece 2).

실제 cmux 워크스페이스를 spawn → 산술 echo 명령 N회 → 출력 검증 → close.
"실제 실행"만 카운트하기 위해 출력 토큰을 i*7 산술 결과로 설계
(셸이 계산해야만 나오는 값 → "타이핑됨"이 아니라 "실행됨" 증명).

사용: python3 spike/w1/smoke_shell.py [N]
"""

from __future__ import annotations

import sys

import cmux_session as cs


def main(n: int = 10) -> int:
    me = cs.identify()
    print(f"[identify] caller = {me}")

    ref = cs.spawn_terminal(name="w1-smoke", window=me["window"], command="zsh")
    print(f"[spawn] {ref}")

    passed = 0
    try:
        for i in range(1, n + 1):
            expected = i * 7
            marker = f"Z{i}_{expected}Z"
            # 출력 라인만 매칭 (^Z...): echo가 친 명령 라인은 프롬프트로 시작하므로 제외
            try:
                cs.run_command(ref, f"echo {marker}", expect=rf"^{marker}\s*$", timeout=8.0)
                passed += 1
            except TimeoutError as exc:
                print(f"  trial {i} FAIL: {exc}")
    finally:
        cs.close(ref)
        print(f"[close] {ref.workspace} 종료")

    rate = passed / n * 100
    print(f"\nRESULT: {passed}/{n} ({rate:.1f}%)")
    return 0 if passed == n else 1


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    raise SystemExit(main(count))
