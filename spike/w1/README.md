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
| 1+5 | Discord 양끝 (멘션 수신 → thread 포스팅) | `discord_bot.py` | ✅ 실 Discord 검증 |

**W1 E2E 전체 검증 완료** (2026-05-31): Discord #일반 채널에서 봇 @멘션 → cmux claude 워커 → diff → qwen3.5:9b 한국어 요약 → thread 포스팅이 실제로 끝까지 동작. 로그: `[recv]→[thread]→[worker]→[done] exit=0→[posted]`.

## 실행

```bash
# 전제: ollama + qwen3.5:9b 가동, cmux 0.64.10, cmux.app 터미널 안에서 실행
pip install -r spike/w1/requirements.txt   # discord.py

python3 spike/w1/smoke_shell.py 10         # cmux 래퍼 round-trip
python3 spike/w1/e2e_local.py              # 로컬 CLI E2E (Discord 없이)

# Discord 봇: spike/w1/.env 에 DISCORD_BOT_TOKEN / DISCORD_CHANNEL_ID 채운 뒤
#   - Developer Portal에서 MESSAGE CONTENT INTENT 켜기 필수
#   - 봇 권한: Send Messages / Create Public Threads / Send Messages in Threads
#   - cmux 터미널 안에서 실행해야 cmux identify가 caller window를 잡음
python3 -u spike/w1/discord_bot.py         # @멘션 대기 → 워커 → 한국어 요약 thread 포스팅
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
