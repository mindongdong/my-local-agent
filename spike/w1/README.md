# W1 E2E 스파이크 (tracer-bullet)

**목표** (wiki/phases/w1-handoff.md §7): Discord 메시지 → 하드코딩 영문 prompt → cmux OMC 실행 → **diff 한국어 출력**. PR·승인·가드레일 없이 통신 척추부터.

## 조각 현황

| # | 조각 | 파일 | 상태 |
|---|---|---|---|
| 2+3 | cmux 세션 spawn + send/read 래퍼 | `cmux_session.py` | ✅ 10/10 스모크 |
| 3 | cmux 안 claude headless 워커 구동 + diff 캡처 | `worker_spawn.py` | ✅ 격리 작업 18s |
| 4 | Qwen 한국어 요약 (diff→한국어 JSON) | `qwen_summarize.py` | ✅ 실 diff 검증 |
| — | 전체 E2E (Discord 제외, CLI) | `e2e_local.py` | ✅ |
| — | (cmux 래퍼 스모크) | `smoke_shell.py` | ✅ |
| 1+5 | Discord 양끝 (수신/포스팅) | _미구현_ | ⏳ 토큰 준비 후 |

Discord 양끝은 `e2e_local.py`의 입력(stdin)·출력(stdout) 어댑터만 교체하면 됨 — 척추는 검증 완료. 토큰은 `.env`(gitignore)로 분리, `.env.example` 참조.

## 실행

```bash
# 전제: ollama + qwen3.5:9b 가동, cmux 0.64.10, cmux.app 안에서 실행
python3 spike/w1/smoke_shell.py 10      # cmux 래퍼 round-trip
python3 spike/w1/e2e_local.py           # 전체 E2E: 하드코딩 prompt → cmux 워커 → diff → 한국어 요약
```

## 흐름

```
[입력: stdin/하드코딩 영문 prompt]
  → cmux 터미널 surface spawn (격리 임시 repo, cwd 분리)
  → claude --permission-mode acceptEdits -p (sentinel __W1_DONE__<exit>__로 완료 감지)
  → git diff 캡처
  → qwen3.5:9b 한국어 요약 (think:false/temp:0, 코드측 검증)
  → [출력: stdout/(Discord thread)]
```

## W0.5에서 확정한 운영 규약 (코드에 고정)

- **cmux API 교정**: `send`/`read-screen`은 `--surface`에 **`--window` 컨텍스트 필수**. 기본 `new-workspace`는 비-터미널 → **`--layout` 터미널 surface 명시**.
- **Qwen**: `think:false` + `temperature:0`, **ollama `format` 미사용**(프롬프트 구조 명시 + 코드측 검증 + 재시도), `keep_alive` 단명(유휴 시 모델 언로드로 ~7.4GB 회수), `num_ctx` 보수적 캡.
