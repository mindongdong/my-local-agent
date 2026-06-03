# W3 스파이크 — interrupt#1 (정보 부족 시 되묻기)

W2가 연기했던 **LangGraph 전환**을 수행하고, 그 위에 **interrupt#1 + SQLite
checkpointer**를 얹는다. 이슈 정보가 부족하면 일시정지하고 한국어로 되물어,
답을 받아 재개한다.

```
START → parse → assess ─┬─ sufficient ──→ build → END
                        └─ insufficient → clarify(interrupt#1)
                               ↑________________ 답변 → assess (재판단)
```

**PR-a (이 디렉터리, `feat/w3-interrupt`)**: interrupt/resume/checkpointer 기계장치를
**CLI로 결정적 증명**. Discord thread reply↔resume 어댑터는 **PR-b**.

## 파일

| 파일 | 역할 |
|---|---|
| `manager_graph_lg.py` | LangGraph 그래프(W2 3노드 재사용 래퍼 + `clarify` interrupt 노드 + 조건부 엣지) + `make_saver`(allowlist serde) |
| `e2e_w3.py` | CLI 하니스 — interrupt 루프(stdin/`--answer`) → 충분해지면 build → W1 워커 → 한국어 요약 |
| `test_w3.py` | 순수 로직 단위 테스트(라우팅·clarification append·그래프 구성·serde allowlist) |
| `requirements.txt` | `langgraph`, `langgraph-checkpoint-sqlite` |

## W2 노드 재사용 (수정 0)

`parse_issue`/`assess_sufficiency`/`build_prompt`(`spike/w2/`)를 **그대로** LangGraph
노드로 등록한다. 정보 부족 답변은 **이슈 본문에 Q&A로 append**(`append_clarification`)해서
assess를 재실행 — assess/build가 더 풍부한 본문을 그대로 읽으므로 상태에 새 필드를
추가하거나 W2 노드를 고칠 필요가 없다. (W2가 약속한 "노드 등록만 + 분기/체크포인트 추가" 이행)

## 실행

```bash
pip install -r spike/w3/requirements.txt   # langgraph + checkpoint-sqlite
python3 spike/w3/test_w3.py                 # 순수 로직 5개 테스트
# 대화형(질문 시 stdin) — cmux 터미널 안에서(워커용)
python3 spike/w3/e2e_w3.py 11
# 비대화형(답변 스크립트) — Manager 단계만
python3 spike/w3/e2e_w3.py 11 --answer "중복 줄 제거, 제목만 남겨" --dry
```

## 검증 (2026-06-03)

모호한 테스트 이슈 [#11](https://github.com/mindongdong/my-local-agent/issues/11)
("NOTES.md 좀 정리해줘" — 일부러 불명확)로 interrupt 루프 통과(`--dry`):

```
[parse] #11  intent=refactor
[assess] sufficient=False — 정리 기준/대상 누락
  ⏸ interrupt#1: 1. 어떤 기준으로 정리? 2. 유지/삭제 대상?
  [answer] 중복된 줄을 제거하고 제목 '# Notes'만 남겨주세요. 다른 파일은 건드리지 마세요.
[assess] sufficient=True  (clarify 1라운드)
[build] keyword=ralph:  EN="In NOTES.md, remove all duplicate lines and keep only the heading '# Notes'. …"
```

- **interrupt/resume/checkpointer 동작 확인**: SQLite 체크포인트 경계에서 상태
  직렬화/복원 정상, **serde 경고 없음**(allowlist 등록으로 future-proof).
- 순수 로직 단위 테스트 **5/5 통과**.
- **워커 포함 전체 E2E는 미실행**: 테스트 시점 cmux 소켓이 broken-pipe 상태(`cmux ping`
  실패 — 다일 세션 드리프트, cmux 앱 재시작 필요). 워커 단계는 **W1-검증 경로**(이번
  세션 W2 E2E에서 정상 동작)이며 W3 신규 코드가 아니다. cmux 소켓 정상화 후 재실행.

## 설계 메모

- **serde allowlist**: 커스텀 dataclass(`ManagerState` 등)는 현재 msgpack으로 round-trip
  되지만 미등록 시 향후 버전에서 차단 경고. `JsonPlusSerializer(allowed_msgpack_modules=[…])`에
  `manager_state` 모듈 타입을 등록해 회피(probe로 확인 후 적용).
- **라운드 캡**: `clarify`는 항상 일시정지하므로 그래프 자체는 무한루프 불가(매 라운드
  = 호출측 1 resume). 하니스가 `MAX_ROUNDS=3`으로 캡(실운영은 계속 질문/타임아웃).
- **keyword는 선택·기록만**(W2와 동일): 실제 OMC keyword 호출은 차기 노드.
- **thread_id ↔ checkpointer**: CLI는 실행마다 고유 thread_id. PR-b에서 **Discord
  thread.id = checkpointer thread_id**로 매핑해, thread reply가 정확히 그 그래프를 resume.
