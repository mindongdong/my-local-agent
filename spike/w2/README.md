# W2 스파이크 — Manager 두뇌화

W1(하드코딩 영문 prompt → 워커)의 **앞단에 Manager 두뇌**를 붙인다. 입력이
"하드코딩 prompt"에서 "실제 GitHub 이슈 + Manager가 빌드한 영문 prompt"로 바뀐다.

```
GitHub 이슈(#n)
  → [parse_issue]        gh fetch + 한국어 의도 파싱 (qwen)        ┐
  → [assess_sufficiency] 정보 충분성 JSON 판단 (qwen, 코드측 검증) │ W2 신규
  → [build_prompt]       영문 작업 명세 + keyword 라우팅 (qwen)     ┘
  → [W1 척추] cmux claude 워커 → git diff → qwen 한국어 요약        (재사용)
  → stdout (Discord 자리)
```

## 파일

| 파일 | 역할 |
|---|---|
| `qwen.py` | qwen3.5:9b 범용 JSON 생성 (think:false/temp:0, 코드측 검증+재시도). W2 노드 3개 공용 |
| `manager_state.py` | `ManagerState`/`Issue`/`Intent`/`Sufficiency` — 모두 frozen(불변) |
| `parse_issue.py` | `gh issue view` fetch + 한국어 의도 파싱 → `Intent` |
| `assess_sufficiency.py` | 정보 충분성 판단 → `Sufficiency`(부족 시 한국어 질문 목록) |
| `build_prompt.py` | 영문 작업 명세 생성 + task_type → magic keyword 라우팅 |
| `manager_graph.py` | `run_manager(issue_ref)` — 3노드 순차 러너 |
| `e2e_w2.py` | 전체 E2E (Manager → W1 워커 → 한국어 요약) |
| `test_manager.py` | 순수 로직 단위 테스트 (네트워크 불필요) |

## 실행

```bash
# 전제: ollama + qwen3.5:9b 가동, gh 인증. 워커 단계는 cmux 터미널 안에서 실행.
python3 spike/w2/test_manager.py        # 순수 로직 7개 테스트
python3 spike/w2/e2e_w2.py 9 --dry      # Manager 단계만 (cmux 불필요)
python3 spike/w2/e2e_w2.py 9            # 전체 E2E (워커 포함)
```

## 검증 완료 (2026-06-01)

테스트 이슈 [#9](https://github.com/mindongdong/my-local-agent/issues/9)(영어 제목 +
한국어 본문)로 E2E 통과:

```
[parse_issue] #9 'Add an ocean haiku to NOTES.md'  의도(ko)=… task_type=feature 힌트=NOTES.md
[assess_sufficiency] sufficient=True — 대상/위치/형식 명확
[build_prompt] keyword=autopilot:  EN="Append a single English haiku about the ocean (exactly three lines) …"
[worker] exit=0, 18.0s, diff 211B   →  [summarize] "NOTES.md 파일에 시적인 문장 3 줄을 추가했습니다"
```

순수 로직 테스트 7/7 통과.

## 설계 메모 (의도적 스코프)

- **LangGraph는 W3로 연기**: W2 시점엔 분기·interrupt·checkpointer가 없어 LangGraph
  이점이 사실상 0. 노드를 `ManagerState -> ManagerState` 순수 함수로 쓰고 얇은 순차
  러너로 연결한다. 시그니처를 맞춰 둬, W3는 동일 함수를 LangGraph 노드로 등록하고
  `assess → interrupt#1 → build` 분기/체크포인트만 얹으면 된다. (의존성 추가 0)
- **keyword는 선택·기록만**: `build_prompt`가 task_type으로 magic keyword를 고르지만
  (system-design §3 라우팅 표), 실제 OMC keyword **호출**(`invoke_omc_autopilot` 노드)은
  W2 조각이 아니다. E2E는 W1에서 검증된 평문 `claude -p`에 en_prompt를 인서트하고,
  고른 keyword는 추적용으로 로깅만 한다.
- **정보 부족 분기**: `sufficient=false`면 `build_prompt`를 건너뛰고 한국어 질문 목록을
  출력 후 중단(exit 2). 사용자에게 되묻는 interrupt#1 + resume 루프는 W3.
- **워커 시드**: 격리 /tmp repo에 `NOTES.md` 시드(이슈가 그 파일을 다룸). 실운영은
  타겟 repo 클론 — W1과 동일한 스파이크 스탠드인.
- **qwen 규약 재확인**: ollama `format` 미사용, 프롬프트 키 명시 + 코드측 검증 + 재시도.
  W0.5/W1과 동일. `qwen.py`는 `spike/w1/qwen_summarize.py`의 원칙을 노드 공용으로 일반화.
