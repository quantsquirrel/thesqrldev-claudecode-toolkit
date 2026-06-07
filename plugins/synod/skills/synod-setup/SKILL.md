---
name: synod-setup
description: "Synod Setup - 초기 설정 및 모델 가용성 테스트"
allowed-tools: Read, Write, Bash, Glob, Grep
user-invocable: true
---

# Synod Setup - 초기 설정 및 모델 가용성 테스트

## 설명

Synod를 처음 사용하기 전에 실행하는 초기 설정 도구입니다. Python 의존성 설치, CLI 도구 구성, 로컬 세션/프록시 검증, 모델 테스트를 한 번에 처리합니다.

## 사용법

```bash
/synod-setup
```

옵션 없이 실행합니다.

## 동작 과정

### Step 0: Python 의존성 확인 및 설치
- `openai`, `httpx` 패키지 설치 여부 확인
- 미설치 시 `pip install --user`로 자동 설치

### Step 1: CLI 도구 설치
- `~/.synod/bin/` 디렉토리에 CLI 래퍼 스크립트 생성
- 대상: `agy-cli`, `cliproxy-cli`, legacy fallback `gemini-3`/`openai-cli`, `synod-parser`, `synod-classifier` 등
- 기존에 `~/.local/bin/`에 설치된 경우에도 정상 작동 (하위 호환)

### Step 2: 로컬 세션/프록시 확인
- `agy` Antigravity CLI 로그인/설치 상태 확인 (Gemini 3.5 Flash 호출)
- CLIProxyAPI(`http://127.0.0.1:8317/v1`) 접근 상태 확인
- `CLIPROXY_API_KEY`는 선택 사항이며, 미설정 시 로컬 기본 토큰을 사용

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
- agy 로그인 상태나 CLIProxyAPI 포트/토큰을 변경한 경우 다시 실행하세요
- 플러그인 업데이트 후 다시 실행하세요 (CLI 래퍼 경로 갱신)
- 모델 응답이 비정상적으로 느려진 경우 재테스트하세요

## 예시

```bash
$ /synod-setup

[Synod Setup] 초기 설정을 시작합니다...

Step 0/3: Python 의존성 확인
  ✓ openai 설치됨
  ✓ httpx 설치됨

Step 1/3: CLI 도구 설치 (~/.synod/bin/)
  ✓ agy-cli 설치됨
  ✓ cliproxy-cli 설치됨
  ✓ gemini-3 설치됨 (legacy fallback)
  ✓ openai-cli 설치됨 (legacy fallback)
  ✓ synod-parser 설치됨
  ✓ synod-classifier 설치됨

Step 2/3: 로컬 세션/프록시 확인
  ✓ agy Antigravity 세션 사용 가능
  ✓ CLIProxyAPI localhost:8317 사용 가능

Step 3/3: 모델 응답 시간 측정 (타임아웃: 120초)

Provider    Model              Latency    Status
───────────────────────────────────────────────────
gemini      3.5-flash          3.2초      ✓ 권장
openai      gpt55fast          2.8초      ✓ 권장

[저장됨] ~/.synod/setup-result.json
[완료] 2/2 모델 사용 가능
Synod를 사용할 준비가 되었습니다!
```
