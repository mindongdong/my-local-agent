"""qwen3.5:9b 범용 JSON 생성 (W2 Manager 노드 공용).

W0.5/W1 운영 규약을 코드로 고정 (`spike/w1/qwen_summarize.py`와 동일 원칙을
W2 노드용으로 일반화 — diff 요약 한 곳이 아니라 parse/assess/build 셋이 쓴다):
  - think:false, temperature:0 (결정성)
  - ollama `format` 미사용 → 프롬프트에 키 명시 + 코드측 파싱/검증 + 재시도
  - keep_alive 단명(버스트 로드) → 유휴 시 모델 언로드로 ~7.4GB 회수
  - num_ctx 보수적 캡 (256K는 명목; 16GB에서 KV 캐시 폭증 방지)

호출측은 `validate(dict) -> T`를 넘긴다 — ollama format에 의존하지 않고
코드가 스키마를 강제한다. validate가 QwenError를 raise하면 재시도한다.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Callable, TypeVar

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen3.5:9b"
KEEP_ALIVE = "30s"   # 단명: 버스트 후 언로드
NUM_CTX = 8192       # 보수적 캡
TEMPERATURE = 0.0

T = TypeVar("T")


class QwenError(RuntimeError):
    """ollama 호출 또는 응답 파싱/검증 실패."""


def _post(payload: dict, timeout: float = 120.0) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL, data=data, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise QwenError(f"ollama 연결 실패 ({OLLAMA_URL}): {exc}") from exc


def extract_json(text: str) -> dict:
    """모델 출력에서 첫 JSON 객체를 견고하게 추출(코드펜스/잡텍스트 방어)."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    start = text.find("{")
    if start == -1:
        raise QwenError(f"JSON 객체 없음: {text[:200]!r}")
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])
    raise QwenError(f"JSON 닫힘 괄호 없음: {text[start:start+200]!r}")


def generate_json(
    prompt: str,
    validate: Callable[[dict], T],
    *,
    retries: int = 2,
    num_ctx: int = NUM_CTX,
    timeout: float = 120.0,
) -> T:
    """프롬프트로 qwen 호출 → 첫 JSON 추출 → validate로 검증한 결과 반환.

    파싱/검증 실패 시 구조 준수를 한 번 더 강조하며 재시도(W0.5 규약).
    """
    base_payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "keep_alive": KEEP_ALIVE,
        "options": {"temperature": TEMPERATURE, "num_ctx": num_ctx},
    }

    last_err: Exception | None = None
    for attempt in range(retries + 1):
        payload = dict(base_payload)
        if attempt > 0:
            payload["prompt"] = "출력은 JSON 객체 하나만. 코드펜스 금지.\n" + prompt
        resp = _post(payload, timeout=timeout)
        text = resp.get("response", "")
        try:
            return validate(extract_json(text))
        except QwenError as exc:
            last_err = exc
    raise QwenError(f"{retries+1}회 시도 후 실패: {last_err}")
