"""qwen3.5:9b 한국어 요약 (W1 piece 3).

W0.5 운영 규약을 코드로 고정:
  - think:false, temperature:0 (결정성)
  - JSON은 ollama `format` 강제 안 됨 → 프롬프트에 구조 명시 + 코드측 파싱/검증 + 재시도
  - keep_alive 단명(버스트 로드) → 유휴 시 모델 언로드로 ~7.4GB 회수
  - num_ctx 보수적 캡 (256K는 명목; 16GB에서 KV 캐시 폭증 방지)

이 스파이크의 요약 입력은 git diff(코드 변경). 출력은 한국어 요약 JSON.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen3.5:9b"
KEEP_ALIVE = "30s"   # 단명: 버스트 후 언로드
NUM_CTX = 8192       # 보수적 캡
TEMPERATURE = 0.0


class QwenError(RuntimeError):
    """ollama 호출 또는 응답 파싱 실패."""


@dataclass(frozen=True)
class DiffSummary:
    """diff 요약 결과(불변). 코드측에서 키 존재를 검증한 뒤 생성."""

    summary_ko: str          # 변경 핵심 1~3문장 한국어
    files_changed: list[str] # 변경 파일 경로
    risk_ko: str             # 리스크/주의 한 줄(없으면 "없음")


_PROMPT = """\
당신은 코드 변경(diff)을 한국어로 요약하는 어시스턴트입니다.
아래 git diff를 읽고 **반드시 아래 JSON 구조 그대로** 출력하세요. 다른 텍스트·설명·마크다운 코드펜스 없이 JSON만.

{{
  "summary_ko": "이 변경이 무엇을 하는지 한국어 1~3문장",
  "files_changed": ["변경된 파일 경로 목록"],
  "risk_ko": "주의할 리스크 한 줄. 없으면 \\"없음\\""
}}

규칙:
- 키 이름을 정확히 위 4개(summary_ko, files_changed, risk_ko)로만 사용.
- summary_ko, risk_ko는 한국어.
- files_changed는 diff의 +++/--- 헤더에서 추출한 경로 배열.

=== git diff 시작 ===
{diff}
=== git diff 끝 ===
"""


def _post(payload: dict, timeout: float = 120.0) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(OLLAMA_URL, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise QwenError(f"ollama 연결 실패 ({OLLAMA_URL}): {exc}") from exc


def _extract_json(text: str) -> dict:
    """모델 출력에서 첫 JSON 객체를 견고하게 추출(코드펜스/잡텍스트 방어)."""
    text = text.strip()
    # 코드펜스 제거
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    start = text.find("{")
    if start == -1:
        raise QwenError(f"JSON 객체 없음: {text[:200]!r}")
    # 중괄호 균형으로 끝 찾기
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])
    raise QwenError(f"JSON 닫힘 괄호 없음: {text[start:start+200]!r}")


def _validate(obj: dict) -> DiffSummary:
    """코드측 스키마 검증(ollama format에 의존하지 않음)."""
    for key in ("summary_ko", "files_changed", "risk_ko"):
        if key not in obj:
            raise QwenError(f"필수 키 누락: {key} (받은 키: {list(obj)})")
    if not isinstance(obj["files_changed"], list):
        raise QwenError(f"files_changed는 배열이어야 함: {obj['files_changed']!r}")
    return DiffSummary(
        summary_ko=str(obj["summary_ko"]).strip(),
        files_changed=[str(x) for x in obj["files_changed"]],
        risk_ko=str(obj["risk_ko"]).strip(),
    )


def summarize_diff(diff: str, retries: int = 2) -> DiffSummary:
    """git diff를 한국어로 요약. 파싱 실패 시 재시도(W0.5 규약)."""
    if not diff.strip():
        raise ValueError("빈 diff")

    payload = {
        "model": MODEL,
        "prompt": _PROMPT.format(diff=diff),
        "stream": False,
        "think": False,
        "keep_alive": KEEP_ALIVE,
        "options": {"temperature": TEMPERATURE, "num_ctx": NUM_CTX},
    }

    last_err: Exception | None = None
    for attempt in range(retries + 1):
        resp = _post(payload)
        text = resp.get("response", "")
        try:
            return _validate(_extract_json(text))
        except QwenError as exc:
            last_err = exc
            # 재시도 시 구조 준수를 한 번 더 강조
            payload["prompt"] = "출력은 JSON 객체 하나만. 코드펜스 금지.\n" + _PROMPT.format(diff=diff)
    raise QwenError(f"{retries+1}회 시도 후 파싱 실패: {last_err}")
