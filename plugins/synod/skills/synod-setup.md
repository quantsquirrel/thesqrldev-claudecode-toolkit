# Synod Setup - 초기 설정 및 모델 가용성 테스트

## 설명

Synod를 처음 사용하기 전에 실행하는 초기 설정 도구입니다. Python 의존성 설치, CLI 도구 구성, API 키 검증, 모델 테스트를 한 번에 처리합니다.

## 사용법

```bash
/synod-setup
```

옵션 없이 실행합니다.

## 동작 과정

### Step 0: Python 의존성 확인 및 설치
- `google-genai`, `openai`, `httpx` 패키지 설치 여부 확인
- 미설치 시 `pip install --user`로 자동 설치

### Step 1: CLI 도구 설치
- `~/.synod/bin/` 디렉토리에 CLI 래퍼 스크립트 생성
- 대상: `gemini-3`, `openai-cli`, `synod-parser`, `synod-classifier` 등
- 기존에 `~/.local/bin/`에 설치된 경우에도 정상 작동 (하위 호환)

### Step 2: API 키 확인
- `GEMINI_API_KEY` 환경 변수 설정 여부 확인 (`GOOGLE_API_KEY`도 fallback으로 인식)
- `OPENAI_API_KEY` 환경 변수 설정 여부 확인

### Step 3: MCP 라우팅 호환성 확인
- 사용자의 `~/.claude/CLAUDE.md`에 `CODEX-ROUTING` 또는 `ask_codex`/`ask_gemini` MCP 라우팅 규칙이 포함되어 있는지 확인
- 감지 시 안내 메시지 표시:
  - "⚠ MCP 라우팅 감지: Synod는 CLI 실행만 사용합니다. MCP 라우팅이 활성화된 환경에서도 allowed-tools 및 내장 guard 지시문으로 보호됩니다."
- 결과를 `setup-result.json`의 `mcp_routing_detected` 필드에 저장

### Step 4: 모델 응답 시간 테스트
간단한 테스트 프롬프트를 각 모델에 전송하여 응답 시간을 측정합니다.
- 타임아웃: 120초
- 테스트 프롬프트: "Explain the SOLID principles in 3 sentences."

## 출력 형식

테스트 결과는 테이블 형태로 표시되며, 각 모델의 상태를 다음과 같이 분류합니다:

| 상태 | 설명 | 응답 시간 |
|------|------|-----------|
| **recommended** | 권장 사용 | < 10초 |
| **usable** | 사용 가능 | 10초 ~ 60초 |
| **slow** | 느림 (비권장) | 60초 ~ 120초 |
| **timeout** | 타임아웃 | > 120초 |
| **failed** | 실패 (API 키/권한 오류) | - |

## 결과 파일

테스트 결과는 다음 위치에 JSON 형식으로 저장됩니다:

```
~/.synod/setup-result.json
```

이 파일은 Synod가 모델 선택 시 참조하여 사용 불가능한 모델을 자동으로 제외합니다. CLI 도구 경로(`tools_dir`, `synod_bin`)도 포함되어 `/synod` 실행 시 올바른 경로를 찾을 수 있습니다.

## 권장 사항

- `/synod` 명령을 처음 사용하기 전에 반드시 실행하세요
- API 키를 새로 설정하거나 변경한 경우 다시 실행하세요
- 플러그인 업데이트 후 다시 실행하세요 (CLI 래퍼 경로 갱신)
- 모델 응답이 비정상적으로 느려진 경우 재테스트하세요

## 예시

```bash
$ /synod-setup

[Synod Setup] 초기 설정을 시작합니다...

Step 0/4: Python 의존성 확인
  ✓ google-genai 설치됨
  ✓ openai 설치됨
  ✓ httpx 설치됨

Step 1/4: CLI 도구 설치 (~/.synod/bin/)
  ✓ gemini-3 설치됨
  ✓ openai-cli 설치됨
  ✓ synod-parser 설치됨
  ✓ synod-classifier 설치됨

Step 2/4: API 키 확인
  ✓ GEMINI_API_KEY (설정됨)
  ✓ OPENAI_API_KEY (설정됨)

Step 3/4: MCP 라우팅 호환성 확인
  ✓ MCP 라우팅 미감지

Step 4/4: 모델 응답 시간 측정 (타임아웃: 120초)

Provider    Model              Latency    Status
───────────────────────────────────────────────────
gemini      flash              3.2초      ✓ 권장
gemini      pro                12.4초     ✓ 사용 가능
openai      gpt4o              2.8초      ✓ 권장
openai      o3                 45.2초     ⚠ 느림

[저장됨] ~/.synod/setup-result.json
[완료] 4/4 모델 사용 가능
Synod를 사용할 준비가 되었습니다!
```
