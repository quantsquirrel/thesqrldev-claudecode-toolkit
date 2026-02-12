# GitHub Actions Workflows

이 디렉토리에는 claude-blueprint-helix 프로젝트의 CI/CD 파이프라인 워크플로우가 포함되어 있습니다.

## 워크플로우 개요

### 1. CI Workflow (`ci.yml`)

메인 브랜치와 PR에 대한 지속적 통합을 수행합니다.

**트리거:**
- `main` 브랜치에 push
- PR 생성/업데이트
- 수동 트리거 (workflow_dispatch)

**작업:**

#### Test Job
- Node.js 20.x, 22.x, 25.x에서 테스트 실행
- Matrix 전략으로 여러 버전 병렬 테스트
- fail-fast: false로 모든 버전 테스트 완료

#### Lint Job
- 파일 구조 검증 (package.json, plugin.json, 필수 디렉토리)
- JSON 파일 유효성 검사
- 코드 품질 검사

#### Build Check Job
- package.json 필수 필드 확인
- MCP 서버 실행 파일 검증
- 서버 구문 검사

#### Integration Job
- 통합 테스트 실행
- 패키지 생성 가능 여부 확인 (npm pack --dry-run)

#### Status Check Job
- 모든 작업 통과 여부 확인
- 전체 파이프라인 상태 집계

### 2. PR Validation Workflow (`pr.yml`)

Pull Request에 대한 상세한 검증을 수행합니다.

**트리거:**
- PR 열기, 동기화, 재열기, ready_for_review

**작업:**

#### PR Info
- PR 메타데이터 표시 (제목, 작성자, 브랜치, 커밋 수, 변경 파일 수)

#### Size Check
- PR 크기 분석 및 경고
  - Large PR: 50개 이상 파일 또는 1000줄 이상 변경
  - Medium PR: 20개 이상 파일 또는 500줄 이상 변경
  - Small PR: 그 외

#### Validate PR Title
- Conventional Commits 형식 검증
  - `feat:`, `fix:`, `docs:`, `style:`, `refactor:`, `perf:`, `test:`, `build:`, `ci:`, `chore:`, `revert:`
- Action verb 시작 검증
  - `Add`, `Update`, `Fix`, `Remove`, `Improve`, `Refactor`, `Move`, `Rename`

#### Changes Detection
- 변경된 파일 타입 감지
  - code: hooks, skills, agents, mcp
  - tests: 테스트 파일
  - docs: 문서
  - config: 설정 파일

#### Test Coverage Check
- 코드 변경 시 테스트 업데이트 여부 확인
- 테스트 없이 코드만 변경된 경우 경고

#### Security Check
- npm audit 실행 (moderate 레벨)
- 보안 취약점 리포트

### 3. Release Workflow (`release.yml`)

새 버전 릴리스를 자동화합니다.

**트리거:**
- `v*.*.*` 형식의 태그 push
- 수동 트리거 (버전 입력)

**작업:**

#### Validate
- 테스트 실행
- 태그 버전과 package.json 버전 일치 확인
- CHANGELOG.md 항목 존재 여부 확인

#### Build
- 릴리스 패키지 생성 (npm pack)
- 아티팩트 업로드

#### Publish
- npm 레지스트리에 퍼블리시
- `NPM_TOKEN` 시크릿 필요

#### GitHub Release
- GitHub Release 생성
- CHANGELOG에서 릴리스 노트 추출
- 패키지 파일 첨부
- Prerelease 자동 감지 (버전에 `-` 포함 시)

#### Notify
- 릴리스 요약 생성

## 시크릿 설정

릴리스 워크플로우가 작동하려면 다음 시크릿이 필요합니다:

### `NPM_TOKEN`
1. npmjs.com에 로그인
2. Access Tokens → Generate New Token → Classic Token
3. "Automation" 타입 선택
4. GitHub Settings → Secrets and variables → Actions → New repository secret
5. 이름: `NPM_TOKEN`, 값: 생성한 토큰

## 로컬 테스트

워크플로우를 로컬에서 테스트하려면:

```bash
# act 도구 설치 (https://github.com/nektos/act)
brew install act  # macOS
# or
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# CI 워크플로우 실행
act -W .github/workflows/ci.yml

# PR 워크플로우 실행
act pull_request -W .github/workflows/pr.yml
```

## 워크플로우 상태 뱃지

README.md에 다음 뱃지를 추가할 수 있습니다:

```markdown
[![CI](https://github.com/quantsquirrel/claude-blueprint-helix/actions/workflows/ci.yml/badge.svg)](https://github.com/quantsquirrel/claude-blueprint-helix/actions/workflows/ci.yml)
[![Release](https://github.com/quantsquirrel/claude-blueprint-helix/actions/workflows/release.yml/badge.svg)](https://github.com/quantsquirrel/claude-blueprint-helix/actions/workflows/release.yml)
```

## 워크플로우 최적화

### 캐싱
- Node.js setup에서 npm 캐시 자동 활용
- `cache: 'npm'` 옵션으로 의존성 설치 속도 향상

### 병렬 실행
- Test job: 3개 Node 버전 동시 테스트
- Changes detection으로 불필요한 작업 건너뛰기

### Fail Fast 비활성화
- Matrix 전략에서 fail-fast: false
- 한 버전 실패해도 다른 버전 테스트 계속 진행

## 문제 해결

### 워크플로우가 실행되지 않음
- `.github/workflows/` 디렉토리 위치 확인
- YAML 구문 오류 확인
- 브랜치 보호 규칙 확인

### 테스트 실패
- 로컬에서 `npm test` 실행하여 재현
- 실패한 작업의 로그 확인
- Node 버전 호환성 확인

### npm publish 실패
- NPM_TOKEN 시크릿 설정 확인
- 버전 중복 확인 (이미 배포된 버전은 재배포 불가)
- package.json의 `name` 필드 확인

## 참고 자료

- [GitHub Actions 문서](https://docs.github.com/en/actions)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [npm Publishing](https://docs.npmjs.com/cli/v10/commands/npm-publish)
