<div id="top"></div>

<div align="center">

<img src="assets/handoff.jpeg" alt="Handoff Baton - 원시 기록이 아닌 바톤을 넘기세요">

**원시 기록을 넘기지 마세요. 바톤을 넘기세요 — 증류되고, 구조화되고, 바로 달릴 준비가 된.**

**[English](README.md)** | **한국어**

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-compatible-success?style=flat-square)](https://github.com/anthropics/claude-code)
[![Version](https://img.shields.io/badge/version-2.3.0-blue?style=flat-square)](https://github.com/quantsquirrel/claude-handoff-baton)
[![Task Size Detection](https://img.shields.io/badge/Task%20Size-Dynamic-orange?style=flat-square)](https://github.com/quantsquirrel/claude-handoff-baton)

</div>

---

## 빠른 시작

```bash
# 1. 설치
/plugin install quantsquirrel/claude-handoff-baton

# 2. 사용
/handoff
```

**끝.** 다음 세션을 위해 컨텍스트가 보존됩니다.

---

## 목차

- [빠른 시작](#빠른-시작)
- [Handoff Baton이란?](#handoff-baton이란)
- [`--continue`만으로 충분하지 않은 이유](#--continue만으로-충분하지-않은-이유)
- [주요 특징](#주요-특징)
- [설치](#설치)
- [사용법](#사용법)
- [실행 결과](#실행-결과)
- [자동 핸드오프 훅](#자동-핸드오프-훅)
- [Compact 복구](#compact-복구)
- [설정](#설정)
- [문제 해결](#문제-해결)
- [기여하기](#기여하기)

---

## Handoff Baton이란?

**`--continue`가 대화를 복원한다면, Handoff는 바톤을 넘깁니다 — 증류되고, 구조화되고, 바로 달릴 준비가 된.**

| `--continue` (원시 히스토리) | Handoff Baton (증류된 지식) |
|---------------------------|-------------------------------|
| 전체 메시지 히스토리 로드 (100K+ 토큰) | 핵심만 추출 (100-500 토큰) |
| 도구 호출, 파일 읽기, 에러 모두 재생 | 결정, 실패, 다음 단계만 캡처 |
| 같은 세션, 같은 기기에서만 작동 | 클립보드: 어떤 세션, 어떤 기기, 어떤 AI에서든 |
| 실패한 접근법이 노이즈에 묻힘 | 실패한 접근법을 명시적으로 추적 |
| 정보 우선순위 없음 | 세션 복잡도에 따른 스마트 자동 스케일링 |

**하나의 명령. 하나의 바톤. 500배 압축.**

---

## `--continue`만으로 충분하지 않은 이유

`claude --continue`는 짧은 휴식에 적합합니다. 하지만 한계가 있습니다:

- **토큰 낭비**: 도구 출력, 파일 내용, 막다른 골목까지 *모든 것*을 복원. 200K 컨텍스트가 빠르게 소진됩니다.
- **지식 추출 없음**: 원시 히스토리는 중요한 것을 강조하지 않습니다. 실패한 접근법이 노이즈에 묻힙니다.
- **단일 도구 종속**: Claude Code 안에서만 작동. Claude.ai, 팀원, 다른 AI와 컨텍스트 공유 불가.
- **신뢰성 문제**: [세션 복원 버그](https://github.com/anthropics/claude-code/issues/22107)로 컨텍스트가 조용히 사라질 수 있습니다.

**Handoff는 `--continue`를 보완합니다:**

| 상황 | 최적 도구 |
|------|-----------|
| 짧은 휴식 (30분 이내) | `claude --continue` |
| 긴 휴식 (2시간+) | `/handoff` → Cmd+V |
| 기기 전환 | `/handoff` → Cmd+V |
| 팀원에게 컨텍스트 공유 | `/handoff` |
| 컨텍스트 70%+ 도달 | `/handoff` |

---

## 주요 특징

| 기능 | 설명 |
|------|------|
| **실패 접근 추적** | 무엇이 작동하지 않았고 왜인지 — 같은 실수 반복 방지 |
| **500배 압축** | 200K 토큰 세션을 100-500 토큰으로 증류 |
| **클립보드 자동 복사** | 한 줄의 명령으로 Cmd+V 붙여넣기 준비 완료 |
| **크로스 플랫폼** | Claude Code, Claude.ai, 다른 AI, 팀원 누구에게든 전달 |
| **의사결정 근거** | 왜 그 선택을 했는지, 무엇을 거부했는지 기록 |
| **시크릿 검출** | API 키, 자격증명 자동 감지 및 마스킹 |
| **동적 작업 크기** | 대형 작업일수록 더 일찍 핸드오프 권장 |
| **Git 통합** | 커밋 히스토리, 브랜치, 스테이지된 변경사항 포함 |

---

## 설치

### 옵션 1: 단일 파일 (권장)

```bash
curl -o ~/.claude/commands/handoff.md \
  https://raw.githubusercontent.com/quantsquirrel/claude-handoff-baton/main/SKILL.md
```

**끝.** 이제 `/handoff`를 사용할 수 있습니다.

### 옵션 2: 전체 플러그인 (고급)

컨텍스트 70% 도달 시 자동 알림을 원하면:

```bash
/plugin marketplace add quantsquirrel/claude-handoff-baton
/plugin install handoff@quantsquirrel
```

포함 기능:
- 70% 컨텍스트 도달 시 자동 알림
- 작업 크기 추정
- `/handoff` CLI 자동완성

---

## 업데이트

### Marketplace 사용자

```bash
/plugin update handoff
```

### Git Clone 사용자

```bash
cd ~/.claude/skills/handoff && git pull
```

### 수동 설치 사용자

빠른 시작의 curl 명령어를 다시 실행하여 최신 버전을 다운로드하세요.

---

## 사용법

### 워크플로우

```
1. /handoff          → 컨텍스트가 클립보드에 저장됨
2. /clear            → 새 세션 시작
3. Cmd+V (붙여넣기)  → 전체 컨텍스트로 재개
```

### 명령어

```bash
/handoff [주제]             # 스마트 핸드오프 (세션 복잡도에 따라 자동 스케일링)
```

<sub>예시: `/handoff` · `/handoff "auth 구현"` · `/handoff "JWT migration"`</sub>

| 상황 | 명령어 |
|------|--------|
| 컨텍스트 70%+ 도달 | `/handoff` |
| 세션 체크포인트 | `/handoff` |
| 세션 종료 | `/handoff` |
| 긴 휴식 (2시간+) | `/handoff` |

---

## 스마트 자동 스케일링 (v2.2)

세션 복잡도에 따라 출력 깊이가 자동 조절됩니다:

| 세션 크기 | 출력 |
|-----------|------|
| 10개 미만 메시지 | 요약 + 다음 단계 |
| 10-50개 메시지 | 요약 + 주요 결정 + 수정 파일 + 다음 단계 |
| 50개 초과 메시지 | 전체 상세 (모든 섹션) |

수동 레벨 선택 없이 `/handoff`만 실행하면 됩니다.

---

## 컨텍스트 충실도 (v2.3)

v2.3은 원본 컨텍스트를 더 충실하게 보존합니다:

| 기능 | 설명 |
|------|------|
| **Phase 0 검증** | 의미 있는 작업이 없는 세션에서는 핸드오프 생략 |
| **사용자 요청** | 원본 사용자 요청을 그대로 캡처 (10개+ 메시지) |
| **제약 조건** | 사용자가 명시한 제약 조건을 원문 그대로 기록 (50개+ 메시지) |
| **관점 가이드** | 완료 작업은 1인칭, 미완료 작업은 객관적 서술 |

### Phase 0: 빈 세션 검사

핸드오프 생성 전, 다음 중 하나 이상이 참인지 검증합니다:
- 도구가 사용되었거나
- 파일이 수정되었거나
- 실질적인 사용자 메시지가 존재하거나

해당 사항 없음: `"No significant work in this session. Handoff skipped."`

### 사용자 요청 섹션

원본 사용자 요청을 의역 없이 그대로 캡처합니다:

```markdown
## User Requests
- "JWT 인증 시스템을 구현해줘. refresh token rotation이랑 RBAC 포함해서."
- "bcrypt는 async로 해줘, 동기는 너무 느려."
```

### 제약 조건 섹션

사용자가 명시한 제약 조건을 원문 그대로 보존합니다 (전체 상세 세션만):

```markdown
## Constraints
- "bcrypt는 async로 해줘, 동기는 너무 느려."
- "토큰은 httpOnly 쿠키에 저장해. localStorage는 보안 문제 있으니까."
```

---

## 실행 결과

`/handoff` 실행 후:

- **문서 생성** — `.claude/handoffs/handoff-YYYYMMDD-HHMMSS-XXXX.md`
- **클립보드 복사** — 압축된 프롬프트 붙여넣기 준비 완료
- **확인 메시지** — `Handoff saved: [path] | Clipboard: copied (N KB)`
- **보안 검사** — 시크릿 감지 시 자동 마스킹

### 세션 재개 방법 (중요!)

핸드오프 생성 후, **새 세션**에서 다음 단계를 따르세요:

```bash
# Step 1: 현재 세션 초기화
/clear

# Step 2: 핸드오프 프롬프트 붙여넣기 (Cmd+V 또는 Ctrl+V)
# 압축된 컨텍스트가 이미 클립보드에 있습니다!
```

> **왜 `/clear`를 먼저?** 초기화 없이 붙여넣으면 컨텍스트가 잘리거나 기존 대화와 섞일 수 있습니다. 항상 새로 시작하세요!

---

## 저장되는 내용

세션 복잡도에 맞게 핵심 정보를 캡처합니다:

- **요약** — 1-3문장으로 무엇이 일어났는지
- **사용자 요청** — 원본 요청을 그대로 기록 (v2.3)
- **완료/미완료 작업** — 진행 상황 추적
- **실패한 접근법** — 같은 실수 반복 방지
- **주요 결정** — 왜 그 선택을 했는지
- **수정 파일** — 무엇이 변경되었는지
- **제약 조건** — 사용자가 명시한 제약 조건 원문 (v2.3)
- **다음 단계** — 구체적인 다음 액션

내용이 없는 섹션은 자동으로 생략됩니다.

---

## 자동 핸드오프 훅

컨텍스트 사용량을 모니터링하고 70%에 도달하면 핸드오프 생성을 권유합니다.

```bash
# 설치
cd ~/.claude/skills/handoff
bash hooks/install.sh
```

| 사용량 | 동작 |
|--------|------|
| 70-79% | 제안 표시 |
| 80-89% | 경고 - 권장 |
| 90%+ | 긴급 - 즉시 생성 |

---

## Compact 복구

핸드오프 생성 중 컨텍스트가 압축되면 복구 메커니즘이 작업을 보존합니다.

### 자동 초안 (Auto-Draft)

70% 사용량 도달 시 자동으로 초안 저장:

| 항목 | 설명 |
|------|------|
| 위치 | `.claude/handoffs/.draft-{timestamp}.json` |
| 내용 | 세션 ID, 토큰 수, git 브랜치, 작업 디렉토리 |
| 정리 | 동일 세션의 이전 초안 자동 교체 |

### 복구 스크립트

복구 가능한 데이터 확인:

```bash
node ~/.claude/skills/handoff/hooks/recover.mjs
```

**출력:**
- 타임스탬프별 초안 파일 목록
- 중단된 생성 작업 (lock 파일)
- 복구 방법 안내

### Lock 파일

핸드오프 생성 중:
- Lock 파일 생성: `.claude/handoffs/.generating.lock`
- 내용: 세션 ID, 주제, 시작 시간
- 완료 시 자동 삭제
- 중단 시 복구 스크립트에서 감지

<div align="right"><a href="#top">Back to Top</a></div>

---

## 보안

민감한 데이터는 자동으로 감지되어 삭제됩니다:

```
API_KEY=sk-1234...  → API_KEY=***REDACTED***
PASSWORD=secret     → PASSWORD=***REDACTED***
Authorization: Bearer eyJ...  → Authorization: Bearer ***REDACTED***
```

**감지 항목:**
- API 키 및 시크릿
- JWT 토큰 및 Base64 인코딩된 자격증명
- Authorization 헤더의 Bearer 토큰
- 민감한 패턴을 가진 환경 변수

**GDPR 고려사항:** 핸드오프 문서에는 개인 데이터가 포함될 수 있습니다. 제3자와 공유하기 전에 핸드오프를 검토하고 오래된 핸드오프는 정기적으로 삭제하세요.

---

## 문제 해결

### 클립보드에 복사되지 않음

```bash
# macOS 확인
which pbcopy

# Linux 확인 및 설치
which xclip || sudo apt-get install xclip
```

### 품질 점수가 낮음

- ✓ Git 저장소 초기화: `git init`
- ✓ 실패한 접근법 문서화
- ✓ 모든 필수 섹션 작성

---

## 기여하기

한국어 관련 이슈나 기여를 환영합니다!

### 개발 설정

```bash
git clone https://github.com/quantsquirrel/claude-handoff-baton.git
cd handoff
npm install
npm run dev
```

### 이슈 제출

[GitHub Issues에서 제출하기](https://github.com/quantsquirrel/claude-handoff-baton/issues)

---

## 라이선스

**MIT License**

Copyright © 2026 Handoff Contributors

자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

---

## 지원

**리소스**
- 문서: [docs](./docs) 디렉토리 확인
- 예시: [examples](./examples) 디렉토리 참조

**커뮤니티**
- 이슈: [GitHub Issues](https://github.com/quantsquirrel/claude-handoff-baton/issues)
- 토론: [GitHub Discussions](https://github.com/quantsquirrel/claude-handoff-baton/discussions)

---

**바톤을 넘길 준비가 되셨나요?** `/handoff` — 원시 기록이 아닌 증류된 지식을 전달하세요.

Made by [QuantSquirrel](https://github.com/quantsquirrel) | [이슈 제출](https://github.com/quantsquirrel/claude-handoff-baton/issues)

**GitHub에서 스타를 눌러주세요:** [claude-handoff-baton](https://github.com/quantsquirrel/claude-handoff-baton)

<div align="right"><a href="#top">Back to Top</a></div>
