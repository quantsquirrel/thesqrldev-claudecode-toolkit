# Contributing to Claude Blueprint Helix

Thank you for your interest in contributing to **claude-blueprint-helix**! This guide will help you get started with development, understand our conventions, and successfully contribute to the project.

**[English](#english)** · **[한국어](#한국어)**

---

## English

### Table of Contents

1. [Getting Started](#getting-started)
2. [Development Setup](#development-setup)
3. [Project Structure](#project-structure)
4. [Code Style and Conventions](#code-style-and-conventions)
5. [Testing](#testing)
6. [Submitting Changes](#submitting-changes)
7. [Issue Reporting](#issue-reporting)
8. [Community Guidelines](#community-guidelines)

---

### Getting Started

Before contributing, please:

1. Read the [README.md](README.md) to understand what this project does
2. Check [existing issues](https://github.com/quantsquirrel/claude-blueprint-helix/issues) to avoid duplicates
3. Review this contributing guide thoroughly

### Development Setup

#### Prerequisites

- **Node.js** >= 20.0.0
- **Claude Code** installed and configured
- Basic understanding of Claude Code plugins and hooks

#### Installation

1. Clone the repository:

```bash
git clone https://github.com/quantsquirrel/claude-blueprint-helix.git
cd claude-blueprint-helix
```

2. No external dependencies to install - this project uses only Node.js built-ins!

3. Run tests to ensure everything works:

```bash
npm test
```

#### Local Development

To test the plugin locally in Claude Code:

```bash
# Link the plugin to Claude Code's plugin directory
claude plugin add /path/to/claude-blueprint-helix

# Or use the development mode
claude plugin dev /path/to/claude-blueprint-helix
```

### Project Structure

```
claude-blueprint-helix/
├── agents/              # 9 custom agents (analyst, architect, executor, etc.)
│   └── [agent-name].md  # Agent definitions with frontmatter
├── config/              # Configuration files
│   ├── pdca-defaults.json
│   └── pipeline-phases.json
├── hooks/               # 6 lifecycle hooks
│   ├── blueprint-detect.mjs      # UserPromptSubmit: keyword detection
│   ├── phase-tracker.mjs         # PostToolUse: progress tracking
│   ├── session-loader.mjs        # SessionStart: state restoration
│   ├── compact-preserver.mjs     # PreCompact: state preservation
│   ├── cycle-finalize.cjs        # Stop: graceful shutdown
│   ├── session-cleanup.mjs       # SessionEnd: cleanup
│   └── lib/                      # Shared utilities
│       ├── constants.mjs
│       ├── state-manager.mjs
│       ├── io.mjs
│       ├── logger.mjs
│       └── complexity-analyzer.mjs
├── skills/              # 4 user-invocable skills
│   ├── pdca/
│   ├── gap/
│   ├── pipeline/
│   └── cancel/
├── mcp/                 # MCP server for external tool access
│   └── blueprint-server.cjs
├── tests/
│   └── unit/            # Unit tests using Node.js test runner
├── plugin.json          # Plugin manifest
└── .mcp.json           # MCP server configuration
```

### Code Style and Conventions

#### General Principles

- **Zero Dependencies**: Use only Node.js built-ins (`node:*` imports)
- **ES Modules**: All code uses `.mjs` extension and ESM syntax
- **Explicit Imports**: Always use full paths, avoid barrel files
- **Atomic Operations**: State changes use atomic write patterns (tmp file + rename)

#### Naming Conventions

- **Files**: kebab-case (e.g., `state-manager.mjs`, `blueprint-detect.mjs`)
- **Functions**: camelCase (e.g., `generateId`, `loadState`)
- **Constants**: SCREAMING_SNAKE_CASE (e.g., `BLUEPRINT_KEYWORDS`, `STATE_DIR`)
- **Classes**: PascalCase (minimal usage, prefer functional style)

#### Code Structure

**Hooks** follow this pattern:

```javascript
#!/usr/bin/env node

/**
 * Hook Description
 * Brief explanation of what this hook does
 */

import { readStdin } from './lib/io.mjs';
import { error, info } from './lib/logger.mjs';

async function main() {
  info('hook-name', 'Hook started');
  try {
    const input = await readStdin();
    // Process input
    process.stdout.write(JSON.stringify({ continue: true }));
  } catch (err) {
    error('hook-name', `Error: ${err?.message}`, { stack: err?.stack });
    process.stdout.write(JSON.stringify({ continue: true }));
  }
}

main();
```

**State Management**:

- Always use locking when reading/writing state
- State files stored in `.blueprint/` (project-local)
- Use atomic writes via `saveState()`
- Include `sessionId`, `createdAt`, `updatedAt` in all state objects

**Error Handling**:

- Never throw in hook scripts (catch and log instead)
- Always output `{ continue: true }` on error to prevent blocking
- Use descriptive error messages with context

#### Comments and Documentation

- **Code comments** in English
- **Commit messages** in English
- **User-facing messages** support bilingual (English/Korean) where appropriate
- Document complex logic inline
- Keep comments concise and relevant

### Testing

#### Running Tests

```bash
# Run all unit tests
npm test

# Run specific test file
node --test tests/unit/state-manager.test.mjs
```

#### Writing Tests

We use Node.js built-in test runner:

```javascript
import { describe, it, before, after } from 'node:test';
import assert from 'node:assert/strict';

describe('feature-name', () => {
  before(async () => {
    // Setup
  });

  after(async () => {
    // Cleanup
  });

  it('should do something specific', () => {
    assert.equal(actual, expected);
  });
});
```

#### Test Coverage Requirements

- **All new features** must include tests
- **State management** changes require comprehensive tests
- **Hook scripts** should be tested for error handling
- **Utility functions** require 80%+ coverage

#### Testing Checklist

Before submitting:

- [ ] All tests pass (`npm test`)
- [ ] New features have corresponding tests
- [ ] Edge cases are covered
- [ ] Error conditions are tested
- [ ] No console errors or warnings

### Submitting Changes

#### Pull Request Process

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/your-feature-name`
3. **Make** your changes following code conventions
4. **Test** thoroughly: `npm test`
5. **Commit** with clear messages (see commit guidelines below)
6. **Push** to your fork: `git push origin feature/your-feature-name`
7. **Open** a Pull Request with a clear description

#### Commit Message Format

Follow conventional commits:

```
type(scope): brief description

Detailed explanation if needed.

- Bullet points for multiple changes
- Reference issues: Fixes #123
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Adding/updating tests
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `chore`: Build/tooling changes

**Examples**:

```
feat(pdca): add auto-act mode for automatic iteration

fix(state): prevent race condition in lock acquisition

docs(readme): clarify pipeline preset usage

test(hooks): add tests for session-loader error handling
```

#### Pull Request Guidelines

- **Title**: Clear and descriptive (follows commit message format)
- **Description**: Explain what, why, and how
- **Changes**: List all significant changes
- **Testing**: Describe how you tested
- **Screenshots**: Include for UI/output changes
- **Breaking Changes**: Clearly mark and explain
- **Issue References**: Link related issues

**PR Template**:

```markdown
## What
Brief description of changes

## Why
Motivation and context

## How
Implementation approach

## Testing
- [ ] Unit tests added/updated
- [ ] Manual testing performed
- [ ] No regressions

## Checklist
- [ ] Code follows style guidelines
- [ ] Tests pass locally
- [ ] Documentation updated
- [ ] No breaking changes (or marked clearly)
```

### Issue Reporting

#### Before Creating an Issue

1. Search existing issues to avoid duplicates
2. Ensure you're using the latest version
3. Check if it's a Claude Code issue vs. plugin issue

#### Bug Reports

Use the bug report template:

```markdown
**Description**
Clear description of the bug

**Steps to Reproduce**
1. Step one
2. Step two
3. Step three

**Expected Behavior**
What should happen

**Actual Behavior**
What actually happens

**Environment**
- Node.js version:
- Claude Code version:
- OS:
- Plugin version:

**Logs**
```
Paste relevant logs from .blueprint/logs/
```

**Additional Context**
Any other relevant information
```

#### Feature Requests

```markdown
**Problem Statement**
What problem does this solve?

**Proposed Solution**
Describe your proposed solution

**Alternatives Considered**
Other approaches you've thought about

**Additional Context**
Use cases, examples, mockups
```

### Community Guidelines

#### Code of Conduct

- **Be respectful** and inclusive
- **Be collaborative** and constructive
- **Focus on** what is best for the community
- **Show empathy** towards other community members

#### Communication

- Use **clear, concise** language
- Provide **context** and examples
- Be **patient** with responses
- **Help others** when you can

#### Recognition

Contributors are recognized in:
- Git commit history
- Release notes
- Special mentions for significant contributions

---

## 한국어

### 목차

1. [시작하기](#시작하기)
2. [개발 환경 설정](#개발-환경-설정)
3. [프로젝트 구조](#프로젝트-구조-1)
4. [코드 스타일 및 규칙](#코드-스타일-및-규칙)
5. [테스트](#테스트-1)
6. [변경사항 제출](#변경사항-제출)
7. [이슈 리포팅](#이슈-리포팅)
8. [커뮤니티 가이드라인](#커뮤니티-가이드라인-1)

---

### 시작하기

기여하기 전에:

1. [README.ko.md](README.ko.md)를 읽고 프로젝트를 이해하세요
2. [기존 이슈](https://github.com/quantsquirrel/claude-blueprint-helix/issues)를 확인하여 중복을 피하세요
3. 이 기여 가이드를 꼼꼼히 검토하세요

### 개발 환경 설정

#### 필수 요구사항

- **Node.js** >= 20.0.0
- **Claude Code** 설치 및 설정 완료
- Claude Code 플러그인 및 훅에 대한 기본 이해

#### 설치

1. 저장소 클론:

```bash
git clone https://github.com/quantsquirrel/claude-blueprint-helix.git
cd claude-blueprint-helix
```

2. 외부 의존성 설치 불필요 - Node.js 내장 기능만 사용합니다!

3. 테스트 실행으로 정상 작동 확인:

```bash
npm test
```

#### 로컬 개발

Claude Code에서 플러그인을 로컬로 테스트하려면:

```bash
# Claude Code 플러그인 디렉토리에 링크
claude plugin add /path/to/claude-blueprint-helix

# 또는 개발 모드 사용
claude plugin dev /path/to/claude-blueprint-helix
```

### 프로젝트 구조

```
claude-blueprint-helix/
├── agents/              # 9개 커스텀 에이전트
│   └── [agent-name].md  # frontmatter가 포함된 에이전트 정의
├── config/              # 설정 파일
│   ├── pdca-defaults.json
│   └── pipeline-phases.json
├── hooks/               # 6개 라이프사이클 훅
│   ├── blueprint-detect.mjs      # UserPromptSubmit: 키워드 감지
│   ├── phase-tracker.mjs         # PostToolUse: 진행상황 추적
│   ├── session-loader.mjs        # SessionStart: 상태 복원
│   ├── compact-preserver.mjs     # PreCompact: 상태 보존
│   ├── cycle-finalize.cjs        # Stop: 우아한 종료
│   ├── session-cleanup.mjs       # SessionEnd: 정리
│   └── lib/                      # 공유 유틸리티
│       ├── constants.mjs
│       ├── state-manager.mjs
│       ├── io.mjs
│       ├── logger.mjs
│       └── complexity-analyzer.mjs
├── skills/              # 4개 사용자 호출 가능 스킬
│   ├── pdca/
│   ├── gap/
│   ├── pipeline/
│   └── cancel/
├── mcp/                 # 외부 도구 접근을 위한 MCP 서버
│   └── blueprint-server.cjs
├── tests/
│   └── unit/            # Node.js 테스트 러너 사용 단위 테스트
├── plugin.json          # 플러그인 매니페스트
└── .mcp.json           # MCP 서버 설정
```

### 코드 스타일 및 규칙

#### 일반 원칙

- **제로 의존성**: Node.js 내장 기능만 사용 (`node:*` 임포트)
- **ES 모듈**: 모든 코드는 `.mjs` 확장자와 ESM 문법 사용
- **명시적 임포트**: 항상 전체 경로 사용, 배럴 파일 지양
- **원자적 작업**: 상태 변경은 원자적 쓰기 패턴 사용 (임시 파일 + 이름 변경)

#### 명명 규칙

- **파일**: kebab-case (예: `state-manager.mjs`, `blueprint-detect.mjs`)
- **함수**: camelCase (예: `generateId`, `loadState`)
- **상수**: SCREAMING_SNAKE_CASE (예: `BLUEPRINT_KEYWORDS`, `STATE_DIR`)
- **클래스**: PascalCase (최소한 사용, 함수형 스타일 선호)

#### 코드 구조

**훅**은 다음 패턴을 따릅니다:

```javascript
#!/usr/bin/env node

/**
 * 훅 설명
 * 이 훅이 수행하는 작업에 대한 간단한 설명
 */

import { readStdin } from './lib/io.mjs';
import { error, info } from './lib/logger.mjs';

async function main() {
  info('hook-name', 'Hook started');
  try {
    const input = await readStdin();
    // 입력 처리
    process.stdout.write(JSON.stringify({ continue: true }));
  } catch (err) {
    error('hook-name', `Error: ${err?.message}`, { stack: err?.stack });
    process.stdout.write(JSON.stringify({ continue: true }));
  }
}

main();
```

**상태 관리**:

- 상태 읽기/쓰기 시 항상 잠금 사용
- 상태 파일은 `.blueprint/`에 저장 (프로젝트 로컬)
- `saveState()`를 통한 원자적 쓰기 사용
- 모든 상태 객체에 `sessionId`, `createdAt`, `updatedAt` 포함

**에러 처리**:

- 훅 스크립트에서 throw 금지 (대신 catch하고 로깅)
- 에러 발생 시 항상 `{ continue: true }` 출력하여 블로킹 방지
- 컨텍스트가 포함된 명확한 에러 메시지 사용

#### 주석 및 문서화

- **코드 주석**은 영어로 작성
- **커밋 메시지**는 영어로 작성
- **사용자 대면 메시지**는 적절한 경우 이중 언어(영어/한국어) 지원
- 복잡한 로직은 인라인으로 문서화
- 주석은 간결하고 관련성 있게 유지

### 테스트

#### 테스트 실행

```bash
# 모든 단위 테스트 실행
npm test

# 특정 테스트 파일 실행
node --test tests/unit/state-manager.test.mjs
```

#### 테스트 작성

Node.js 내장 테스트 러너를 사용합니다:

```javascript
import { describe, it, before, after } from 'node:test';
import assert from 'node:assert/strict';

describe('feature-name', () => {
  before(async () => {
    // 설정
  });

  after(async () => {
    // 정리
  });

  it('should do something specific', () => {
    assert.equal(actual, expected);
  });
});
```

#### 테스트 커버리지 요구사항

- **모든 새 기능**은 테스트 포함 필수
- **상태 관리** 변경 시 포괄적 테스트 필요
- **훅 스크립트**는 에러 처리 테스트 필요
- **유틸리티 함수**는 80% 이상 커버리지 필요

#### 테스트 체크리스트

제출 전:

- [ ] 모든 테스트 통과 (`npm test`)
- [ ] 새 기능에 대응하는 테스트 존재
- [ ] 엣지 케이스 커버
- [ ] 에러 조건 테스트됨
- [ ] 콘솔 에러나 경고 없음

### 변경사항 제출

#### Pull Request 프로세스

1. 저장소 **Fork**
2. 기능 브랜치 **생성**: `git checkout -b feature/your-feature-name`
3. 코드 규칙을 따라 **변경사항 작성**
4. 철저히 **테스트**: `npm test`
5. 명확한 메시지로 **커밋** (아래 커밋 가이드라인 참조)
6. 포크에 **푸시**: `git push origin feature/your-feature-name`
7. 명확한 설명과 함께 Pull Request **생성**

#### 커밋 메시지 형식

Conventional commits 준수:

```
type(scope): 간단한 설명

필요시 상세 설명.

- 여러 변경사항은 불릿 포인트로
- 이슈 참조: Fixes #123
```

**타입**:
- `feat`: 새 기능
- `fix`: 버그 수정
- `docs`: 문서 변경
- `test`: 테스트 추가/업데이트
- `refactor`: 코드 리팩토링
- `perf`: 성능 개선
- `chore`: 빌드/도구 변경

**예시**:

```
feat(pdca): add auto-act mode for automatic iteration

fix(state): prevent race condition in lock acquisition

docs(readme): clarify pipeline preset usage

test(hooks): add tests for session-loader error handling
```

#### Pull Request 가이드라인

- **제목**: 명확하고 설명적 (커밋 메시지 형식 준수)
- **설명**: 무엇을, 왜, 어떻게 설명
- **변경사항**: 모든 주요 변경사항 나열
- **테스트**: 테스트 방법 설명
- **스크린샷**: UI/출력 변경 시 포함
- **Breaking Changes**: 명확히 표시하고 설명
- **이슈 참조**: 관련 이슈 링크

### 이슈 리포팅

#### 이슈 생성 전

1. 기존 이슈 검색하여 중복 방지
2. 최신 버전 사용 확인
3. Claude Code 이슈 vs. 플러그인 이슈 구분

#### 버그 리포트

버그 리포트 템플릿 사용:

```markdown
**설명**
버그에 대한 명확한 설명

**재현 단계**
1. 첫 번째 단계
2. 두 번째 단계
3. 세 번째 단계

**예상 동작**
발생해야 하는 동작

**실제 동작**
실제 발생한 동작

**환경**
- Node.js 버전:
- Claude Code 버전:
- OS:
- 플러그인 버전:

**로그**
```
.blueprint/logs/의 관련 로그 붙여넣기
```

**추가 컨텍스트**
기타 관련 정보
```

#### 기능 요청

```markdown
**문제 진술**
이것이 해결하는 문제는?

**제안하는 솔루션**
제안하는 솔루션 설명

**고려한 대안**
생각해본 다른 접근 방식

**추가 컨텍스트**
사용 사례, 예시, 목업
```

### 커뮤니티 가이드라인

#### 행동 강령

- **존중하고** 포용적으로 대하기
- **협력적이고** 건설적으로 행동
- 커뮤니티에 **최선**이 무엇인지 집중
- 다른 커뮤니티 구성원에게 **공감** 표시

#### 의사소통

- **명확하고 간결한** 언어 사용
- **컨텍스트**와 예시 제공
- 응답에 **인내심** 갖기
- 가능할 때 **다른 사람 돕기**

#### 인정

기여자는 다음에서 인정받습니다:
- Git 커밋 히스토리
- 릴리스 노트
- 중요한 기여에 대한 특별 언급

---

## License

By contributing to claude-blueprint-helix, you agree that your contributions will be licensed under the MIT License.

## Questions?

- Open an issue for general questions
- Check existing discussions
- Read the documentation in [README.md](README.md)

Thank you for contributing to claude-blueprint-helix! 🎉

---

**Built with ❤️ for systematic software development**
