<!-- Parent: ../../AGENTS.md -->
<!-- Generated: 2026-02-12T00:00:00Z | Updated: 2026-02-12T00:00:00Z -->

# .github/workflows/

## Purpose

GitHub Actions CI/CD workflows for automated testing, PR validation, and release publishing. Ensures code quality, runs tests across multiple Node versions, validates conventional commits, and automates npm publishing.

## Key Files

| File | Description |
|------|-------------|
| `ci.yml` | Main CI pipeline - runs tests on Node 20/22/25, lint, build checks, integration tests (4.5 KB) |
| `pr.yml` | PR validation - size check, title format, test coverage, security audit (7.3 KB) |
| `release.yml` | Release automation - version validation, npm publish, GitHub release creation (5.2 KB) |
| `README.md` | Workflow documentation in Korean with setup instructions and troubleshooting (5.2 KB) |

## For AI Agents

### Working In This Directory

- **YAML format**: GitHub Actions workflow syntax (strict indentation, two spaces)
- **Triggers**: `on:` section defines when workflows run (push, pull_request, workflow_dispatch, tags)
- **Jobs**: Each workflow has multiple jobs that can run in parallel or sequentially
- **Matrix strategy**: CI tests on multiple Node versions (20.x, 22.x, 25.x) with `fail-fast: false`
- **Secrets**: Release workflow requires `NPM_TOKEN` secret for publishing

### Testing Requirements

- Test workflows locally with `act` tool: `act -W .github/workflows/ci.yml`
- Verify YAML syntax: `yamllint .github/workflows/*.yml`
- Check workflow runs in GitHub Actions tab after pushing
- Ensure all status checks pass before merging PRs

**CI Workflow Jobs**:
1. **test**: Matrix test on Node 20/22/25 → `npm ci` → `npm test`
2. **lint**: File structure validation, JSON validation, code quality
3. **build-check**: package.json validation, MCP server checks
4. **integration**: Integration tests + `npm pack --dry-run`
5. **status-check**: Aggregate job status (all must pass)

**PR Workflow Checks**:
1. **pr-info**: Display PR metadata
2. **size-check**: Warn on large PRs (>50 files or >1000 lines)
3. **validate-title**: Enforce conventional commits (feat:, fix:, docs:, etc.)
4. **changes-detection**: Detect changed file types (code, tests, docs, config)
5. **test-coverage**: Warn if code changed without test updates
6. **security-check**: Run `npm audit` for vulnerabilities

**Release Workflow Steps**:
1. **validate**: Run tests, check version matches tag, verify CHANGELOG entry
2. **build**: Create tarball with `npm pack`, upload artifact
3. **publish**: Publish to npm with `NPM_TOKEN`
4. **github-release**: Create GitHub release with CHANGELOG notes
5. **notify**: Generate release summary

### Common Patterns

- **Caching**: `cache: 'npm'` in setup-node for faster installs
- **Fail-fast control**: `fail-fast: false` in matrix to test all versions
- **Conditional jobs**: Use `if:` to skip jobs based on context
- **Status checks**: Final aggregation job required for branch protection
- **Artifact upload**: Save build outputs between jobs

**Workflow syntax**:
```yaml
name: Workflow Name
on:
  push:
    branches: [main]
jobs:
  job-name:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20.x'
          cache: 'npm'
      - run: npm ci
      - run: npm test
```

## Dependencies

### Internal

- Validates: `../../package.json`, `../../plugin.json`, `../../hooks/`, `../../tests/`
- Publishes: Package tarball to npm registry

### External

- **GitHub Actions**: actions/checkout@v4, actions/setup-node@v4
- **npm registry**: Requires `NPM_TOKEN` secret for publishing
- **Node.js**: Tests on versions 20.x, 22.x, 25.x

## Secrets Configuration

### Required for Release Workflow

**`NPM_TOKEN`**:
1. Login to npmjs.com
2. Access Tokens → Generate New Token → Classic Token (Automation type)
3. GitHub repo → Settings → Secrets and variables → Actions → New repository secret
4. Name: `NPM_TOKEN`, Value: your token

## Troubleshooting

**Workflow not running**:
- Check YAML syntax (indentation, colons)
- Verify trigger conditions match (branch names, event types)
- Check branch protection rules

**Test failures**:
- Run `npm test` locally to reproduce
- Check Node version compatibility
- Review job logs in Actions tab

**Publish failures**:
- Verify `NPM_TOKEN` is set correctly
- Check for version conflicts (can't republish same version)
- Ensure `package.json` `name` field is correct and available

<!-- MANUAL: -->
