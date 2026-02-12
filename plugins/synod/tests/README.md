# Synod Plugin Test Suite

이 디렉토리에는 synod-plugin의 종합 테스트 스위트가 포함되어 있습니다.

## 테스트 구조

```
tests/
├── __init__.py              # 테스트 패키지 초기화
├── conftest.py              # 공통 pytest fixtures (mock API keys, 샘플 데이터)
├── test_synod_parser.py     # synod-parser.py 테스트 (36개 테스트)
├── test_gemini.py           # gemini-3.py 테스트 (14개 테스트)
└── test_openai_cli.py       # openai-cli.py 테스트 (13개 테스트)
```

## 테스트 실행

### 전체 테스트 실행
```bash
pytest tests/
```

### 상세 출력과 함께 실행
```bash
pytest tests/ -v
```

### 커버리지 리포트와 함께 실행
```bash
pytest tests/ --cov=tools --cov-report=html
```

### 특정 테스트 파일만 실행
```bash
pytest tests/test_synod_parser.py -v
pytest tests/test_gemini.py -v
pytest tests/test_openai_cli.py -v
```

### 특정 테스트 클래스 실행
```bash
pytest tests/test_synod_parser.py::TestCalculateTrustScore -v
```

### 특정 테스트 케이스 실행
```bash
pytest tests/test_synod_parser.py::TestCalculateTrustScore::test_perfect_trust -v
```

## 테스트 커버리지

현재 테스트 커버리지:
- **synod-parser.py**: 70% (핵심 파싱 로직)
- **gemini-3.py**: 21% (구성 및 에러 처리 로직)
- **openai-cli.py**: 16% (구성 및 에러 처리 로직)

**참고**: API 클라이언트 파일들은 실제 API 호출 부분을 제외하고 구성, 검증, 에러 감지 로직을 테스트합니다.

## 테스트 카테고리

### synod-parser.py 테스트
- ✓ XML 포맷 검증 (`validate_format`)
- ✓ Confidence 추출 (`extract_confidence`)
- ✓ Semantic focus 추출 (`extract_semantic_focus`)
- ✓ Trust Score 계산 (`calculate_trust_score`)
- ✓ 전체 응답 파싱 (`parse_response`)
- ✓ 기본값 적용 (`apply_defaults`)
- ✓ 키 문장 추출 (`extract_key_sentences`)

### gemini-3.py 테스트
- ✓ 모델 매핑 검증
- ✓ Thinking budget 매핑 검증
- ✓ API 키 검증
- ✓ Retry 레벨 구성
- ✓ 에러 감지 로직 (timeout, rate limit, overload)
- ✓ 모듈 통합 테스트

### openai-cli.py 테스트
- ✓ 모델 매핑 검증
- ✓ O-series 모델 식별
- ✓ 타임아웃 구성 검증
- ✓ Reasoning 레벨 검증
- ✓ 에러 감지 로직
- ✓ 타임아웃 전략 검증

## API 키 없이 테스트 실행

모든 테스트는 **실제 API 키 없이 실행 가능**합니다:
- `conftest.py`의 fixtures가 mock API keys를 제공
- 실제 API 호출은 수행하지 않음
- 구성, 로직, 검증에 집중

## CI/CD 통합

GitHub Actions에서 자동으로 실행됩니다:
```yaml
- name: Run tests
  run: pytest tests/ -v --cov=tools
```

## 문제 해결

### ImportError 발생 시
```bash
# tools 디렉토리가 Python path에 있는지 확인
export PYTHONPATH="${PYTHONPATH}:$(pwd)/tools"
pytest tests/
```

### pytest를 찾을 수 없을 때
```bash
pip install -r requirements-dev.txt
```

## 기여하기

새 기능을 추가할 때:
1. 해당 기능에 대한 테스트를 먼저 작성 (TDD)
2. 모든 테스트가 통과하는지 확인
3. 커버리지가 감소하지 않도록 주의

테스트 작성 가이드라인:
- 함수당 최소 2-3개의 테스트 케이스
- Happy path와 edge cases 모두 테스트
- Mock을 사용하여 외부 의존성 격리
- 명확하고 설명적인 테스트 이름 사용
