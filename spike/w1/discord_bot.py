"""W1 Discord 양끝 어댑터 (piece 1: 멘션 수신, piece 5: thread 포스팅).

기존 척추(e2e_local.py)의 입출력 어댑터만 Discord로 교체. 파이프라인은 동일:
  @멘션 메시지 → 프롬프트 추출 → cmux claude 워커 → diff → qwen 한국어 요약 → thread 포스팅

실행: cmux 터미널 surface 안에서 (cmux identify가 caller window를 잡아야 함)
  python3 spike/w1/discord_bot.py

전제:
  - spike/w1/.env 에 DISCORD_BOT_TOKEN / DISCORD_CHANNEL_ID (gitignore)
  - Discord Developer Portal에서 MESSAGE CONTENT INTENT 켜짐
  - 봇이 채널에 Send Messages / Create Public Threads / Send Messages in Threads 권한 보유
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import discord

import cmux_session as cs
import qwen_summarize as qs
import worker_spawn as ws

SEED = {"NOTES.md": "# Notes\n\n"}
DISCORD_MSG_LIMIT = 1900  # 2000자 한계에 여유


def load_env(path: Path) -> dict[str, str]:
    """.env 직접 파싱(의존성 최소화). KEY=VALUE, # 주석 무시."""
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    return env


_env = load_env(Path(__file__).parent / ".env")
TOKEN = _env.get("DISCORD_BOT_TOKEN") or os.environ.get("DISCORD_BOT_TOKEN", "")
CHANNEL_ID = int(_env.get("DISCORD_CHANNEL_ID") or os.environ.get("DISCORD_CHANNEL_ID") or 0)

intents = discord.Intents.default()
intents.message_content = True  # 멘션 본문 읽기 (Privileged Intent)
client = discord.Client(intents=intents)


def _strip_mentions(content: str, mention_ids: list[int]) -> str:
    """멘션 토큰(<@id>, <@!id>)을 제거해 순수 프롬프트만 남김."""
    out = content
    for mid in mention_ids:
        out = out.replace(f"<@{mid}>", "").replace(f"<@!{mid}>", "")
    return out.strip()


def run_pipeline(prompt: str, window: str):
    """blocking 척추: 워커 구동 → diff → 한국어 요약. (executor에서 호출)"""
    root = ws.prepare_workspace(SEED)
    res = ws.run_worker(root, prompt, window=window, timeout=180)
    if not res.diff.strip():
        return None, res
    summary = qs.summarize_diff(res.diff)
    return summary, res


@client.event
async def on_ready() -> None:
    ch = f"channel:{CHANNEL_ID}" if CHANNEL_ID else "(any channel)"
    print(f"[ready] logged in as {client.user} | listening on {ch}", flush=True)
    # 진단: 봇이 실제로 어느 서버에 있고, 대상 채널을 보는지
    print(f"[guilds] {[(g.name, g.id) for g in client.guilds] or '(없음 — 봇이 어떤 서버에도 없음!)'}", flush=True)
    if CHANNEL_ID:
        target = client.get_channel(CHANNEL_ID)
        if target is None:
            print(f"[channel] {CHANNEL_ID} -> 못 봄 (봇이 이 채널에 접근 불가/초대 안 됨/ID 오류)", flush=True)
        else:
            print(f"[channel] {CHANNEL_ID} -> #{getattr(target, 'name', '?')} in '{getattr(target.guild, 'name', '?')}'", flush=True)


@client.event
async def on_message(msg: discord.Message) -> None:
    # 자기 메시지 / 다른 채널 / 멘션 아님 → 무시
    if msg.author == client.user:
        return
    # 진단: 받은 메시지를 무조건 기록 (어디서 걸러지는지 가시화)
    print(
        f"[recv] ch={msg.channel.id} from={msg.author} "
        f"self_mentioned={client.user in msg.mentions} "
        f"mentions={[m.name for m in msg.mentions]} content={msg.content[:80]!r}",
        flush=True,
    )
    if CHANNEL_ID and msg.channel.id != CHANNEL_ID:
        print(f"[skip] 다른 채널 ({msg.channel.id} != {CHANNEL_ID})", flush=True)
        return
    if client.user not in msg.mentions:
        print("[skip] 봇이 멘션되지 않음 (실제 @멘션인지 확인 — 텍스트만으론 안 됨)", flush=True)
        return

    prompt = _strip_mentions(msg.content, [m.id for m in msg.mentions])
    print(f"[msg] {msg.author} in channel:{msg.channel.id}: {prompt[:80]!r}", flush=True)
    if not prompt:
        await msg.reply("프롬프트를 함께 적어 멘션해 주세요. 예: `@bot Append a TODO line to NOTES.md`")
        return

    # piece 5: 결과를 담을 thread 생성
    try:
        thread = await msg.create_thread(name=f"agent: {prompt[:40]}")
    except discord.Forbidden:
        print("[error] create_thread Forbidden", flush=True)
        await msg.reply("스레드 생성 권한이 없습니다 (Create Public Threads 권한 확인).")
        return
    print(f"[thread] created thread:{thread.id}", flush=True)
    await thread.send(f"🔧 작업 시작\n프롬프트: `{prompt[:200]}`\ncmux 워커 구동 중...")

    # cmux caller window (봇이 cmux 터미널 안에서 실행돼야 함)
    try:
        me = cs.identify()
    except cs.CmuxError as exc:
        print(f"[error] identify: {exc}", flush=True)
        await thread.send(f"❌ cmux identify 실패 (봇을 cmux 터미널에서 실행했나요?): {exc}")
        return

    # blocking 파이프라인 → executor (이벤트 루프 비차단)
    print(f"[worker] spawning (window={me['window']}) ...", flush=True)
    loop = asyncio.get_running_loop()
    try:
        summary, res = await loop.run_in_executor(None, run_pipeline, prompt, me["window"])
    except Exception as exc:  # noqa: BLE001 - 사용자에게 명확히 보고
        print(f"[error] pipeline: {type(exc).__name__}: {exc}", flush=True)
        await thread.send(f"❌ 파이프라인 실패: {type(exc).__name__}: {exc}")
        return

    if summary is None:
        print(f"[done] no-change exit={res.exit_code}", flush=True)
        await thread.send(f"⚠️ 워커가 변경을 만들지 않았습니다 (exit={res.exit_code}).")
        return

    print(f"[done] exit={res.exit_code} diff={len(res.diff)}B summary={summary.summary_ko[:50]!r}", flush=True)
    body = (
        f"✅ 완료 (exit={res.exit_code})\n\n"
        f"**요약**: {summary.summary_ko}\n"
        f"**변경 파일**: {', '.join(summary.files_changed) or '(없음)'}\n"
        f"**리스크**: {summary.risk_ko}"
    )
    await thread.send(body[:DISCORD_MSG_LIMIT])

    diff = res.diff[:DISCORD_MSG_LIMIT - 20]
    await thread.send(f"```diff\n{diff}\n```")
    print("[posted] result sent to thread", flush=True)


def main() -> int:
    if not TOKEN:
        print("[error] DISCORD_BOT_TOKEN 없음 — spike/w1/.env 확인")
        return 1
    if not CHANNEL_ID:
        print("[warn] DISCORD_CHANNEL_ID 없음 — 모든 채널에서 멘션 수신")
    client.run(TOKEN)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
