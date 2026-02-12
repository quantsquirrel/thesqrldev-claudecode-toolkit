# thesqrldev-claudecode-toolkit

[quantsquirrel](https://github.com/quantsquirrel)의 Claude Code 플러그인 툴킷 — 4개 플러그인을 한 번에 설치하는 팀 온보딩 키트.

## 플러그인

| 플러그인 | 설명 | 레포 |
|---------|------|------|
| **handoff** | 세션 컨텍스트 핸드오프 — autocompact 전 저장, 클립보드로 복원 | [claude-handoff-baton](https://github.com/quantsquirrel/claude-handoff-baton) |
| **synod** | 멀티 에이전트 토론 시스템 (Claude + Gemini + OpenAI) | [claude-synod-debate](https://github.com/quantsquirrel/claude-synod-debate) |
| **blueprint** | PDCA 사이클, Gap 분석, 개발 파이프라인 | [claude-blueprint-helix](https://github.com/quantsquirrel/claude-blueprint-helix) |
| **forge** | TDD 기반 스킬 자동 진화 + 통계적 검증 | [claude-forge-smith](https://github.com/quantsquirrel/claude-forge-smith) |

## 설치

```bash
claude plugin install gh:quantsquirrel/thesqrldev-claudecode-toolkit
```

4개 플러그인 + 관리 스킬이 한 번에 설치됩니다.

## 관리 스킬

| 스킬 | 설명 |
|------|------|
| `/toolkit:update` | 최신 플러그인 풀 |
| `/toolkit:list` | 플러그인 상태 테이블 |
| `/toolkit:doctor` | 설치 무결성 검사 |

## 동작 원리

Git 서브모듈이 **아닙니다**. 매일 CI 워크플로우([sync-plugins.yml](.github/workflows/sync-plugins.yml))가 각 원본 레포를 `plugins/`에 미러링합니다.

- **플러그인 추가**: `config/registry.json`에 1줄 추가하면 CI가 자동 처리
- **업데이트**: 원본 레포에 push → 24시간 내 CI 자동 동기화 (수동 트리거 가능)
- **로컬 클론 불필요**: GitHub Actions가 모든 것을 관리

```
원본 레포에 push
  → CI가 plugins/ 디렉토리에 동기화
    → 팀원 세션 시작 시 update-checker가 알림
      → /toolkit:update로 최신화
```

## 수동 동기화

```bash
gh workflow run sync-plugins.yml -R quantsquirrel/thesqrldev-claudecode-toolkit
```

## 라이선스

[MIT](LICENSE)
