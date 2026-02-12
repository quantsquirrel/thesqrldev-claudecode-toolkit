# Synod AI 서비스 통합 가이드

## 개요

이 가이드는 Synod debate 시스템에 새로운 AI 제공자(Cohere, AI21)를 통합하기 위한 단계별 지침입니다.

---

## Phase 1: 개발 환경 설정 (1-2주)

### 1.1 API 키 획득

#### Cohere
1. https://dashboard.cohere.com에 가입
2. API 키 생성
3. 환경변수 설정:
   ```bash
   export COHERE_API_KEY="your-api-key"
   ```

#### AI21 Labs
1. https://www.ai21.com/studio에 가입
2. API 키 생성
3. 환경변수 설정:
   ```bash
   export AI21_API_KEY="your-api-key"
   ```

#### Perplexity (선택)
1. https://www.perplexity.ai/pro에 가입
2. API 액세스 요청
3. 환경변수 설정:
   ```bash
   export PERPLEXITY_API_KEY="your-api-key"
   ```

### 1.2 라이브러리 설치

```bash
cd /Users/ahnjundaram_g/dev/tools/synod

# Cohere SDK
pip install cohere

# AI21 SDK
pip install ai21

# Perplexity (선택)
pip install perplexity-python

# 기존 라이브러리 (업데이트)
pip install -r requirements.txt --upgrade
```

### 1.3 프로젝트 구조

```
synod/
├── synod/
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py           # 추상 기본 클래스
│   │   ├── gemini.py         # 기존
│   │   ├── openai.py         # 기존
│   │   ├── cohere.py         # 신규
│   │   ├── ai21.py           # 신규
│   │   └── perplexity.py     # 신규 (선택)
│   ├── config.py             # 설정
│   ├── debate.py             # 토론 엔진
│   └── utils.py
├── tests/
│   ├── test_cohere.py
│   ├── test_ai21.py
│   └── test_integration.py
└── README.md
```

---

## Phase 2: Cohere 통합 (1-2주)

### 2.1 기본 제공자 클래스 작성

**파일**: `synod/providers/base.py`

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class BaseProvider(ABC):
    """모든 AI 제공자의 추상 기본 클래스"""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    @abstractmethod
    def generate(self, prompt: str, context: Optional[str] = None) -> str:
        """텍스트 생성"""
        pass

    @abstractmethod
    def get_model_info(self) -> Dict:
        """모델 정보 반환"""
        pass

    @abstractmethod
    def validate_api_key(self) -> bool:
        """API 키 검증"""
        pass

    @abstractmethod
    def estimate_tokens(self, text: str) -> int:
        """토큰 수 추정"""
        pass
```

### 2.2 Cohere 제공자 구현

**파일**: `synod/providers/cohere.py`

```python
import cohere
import os
from typing import Dict, List, Optional
from .base import BaseProvider

class CohereProvider(BaseProvider):
    """Cohere Command API 제공자"""

    def __init__(self, api_key: Optional[str] = None):
        api_key = api_key or os.getenv("COHERE_API_KEY")
        if not api_key:
            raise ValueError("COHERE_API_KEY 환경변수가 설정되지 않았습니다")

        super().__init__(api_key, "command-a-reasoning-08-2025")
        self.client = cohere.ClientV2(api_key=api_key)

    def generate(
        self,
        prompt: str,
        context: Optional[str] = None,
        temperature: float = 0.5,
        max_tokens: int = 2048,
    ) -> str:
        """
        Cohere API를 사용해 텍스트 생성

        Args:
            prompt: 사용자 프롬프트
            context: 추가 컨텍스트 (256K 토큰까지 지원)
            temperature: 창의성 수준 (0-2, 기본 0.5)
            max_tokens: 최대 출력 토큰

        Returns:
            생성된 텍스트
        """

        # 컨텍스트와 프롬프트 결합
        if context:
            full_prompt = f"{context}\n\n{prompt}"
        else:
            full_prompt = prompt

        try:
            response = self.client.chat(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": full_prompt
                    }
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )

            return response.message.content[0].text

        except Exception as e:
            raise RuntimeError(f"Cohere API 오류: {str(e)}")

    def debate(
        self,
        position: str,
        opposition: str,
        topic: str,
        act: int = 1,
    ) -> Dict:
        """
        토론 응답 생성

        Args:
            position: 자신의 입장
            opposition: 상대방 입장
            topic: 토론 주제
            act: ACT 단계 (1: 솔루션, 2: 비판, 3: 판정)

        Returns:
            토론 응답 딕셔너리
        """

        if act == 1:
            prompt = self._make_act1_prompt(topic)
        elif act == 2:
            prompt = self._make_act2_prompt(topic, opposition)
        elif act == 3:
            prompt = self._make_act3_prompt(topic, position, opposition)
        else:
            raise ValueError(f"유효하지 않은 ACT: {act}")

        response_text = self.generate(prompt)

        return {
            "provider": "cohere",
            "model": self.model,
            "act": act,
            "response": response_text,
            "tokens_used": self.estimate_tokens(response_text),
        }

    def _make_act1_prompt(self, topic: str) -> str:
        """ACT I: 솔루션 생성 프롬프트"""
        return f"""
당신은 전문가 토론자입니다. 다음 주제에 대해 명확하고 논리적인 솔루션을 제시하세요.

주제: {topic}

요구사항:
1. 핵심 주장을 명확하게 정의하세요
2. 3-5개의 근거를 제시하세요
3. 예상되는 반박에 대비하세요
4. 결론을 명확하게 작성하세요

솔루션:
"""

    def _make_act2_prompt(self, topic: str, opposition: str) -> str:
        """ACT II: 비판 프롬프트"""
        return f"""
당신은 비판적 사고를 가진 전문가입니다. 다음 주제와 상대방의 입장에 대해 논리적 허점을 지적하세요.

주제: {topic}

상대방 입장:
{opposition}

요구사항:
1. 주요 허점 3-5개를 찾으세요
2. 각 허점에 대해 구체적인 반박을 제시하세요
3. 대안적 관점을 제시하세요
4. 증거나 사례를 들어 설명하세요

비판:
"""

    def _make_act3_prompt(
        self,
        topic: str,
        position: str,
        opposition: str
    ) -> str:
        """ACT III: 최종 판정 프롬프트 (Claude용)"""
        return f"""
주제: {topic}

Position A:
{position}

Position B:
{opposition}

당신은 중립적 판정자입니다. 다음을 분석하세요:
1. 각 입장의 강점
2. 각 입장의 약점
3. 더 강력한 논증은?
4. 왜?

판정:
"""

    def get_model_info(self) -> Dict:
        """모델 정보 반환"""
        return {
            "provider": "Cohere",
            "model": self.model,
            "context_window": 256000,
            "max_tokens_per_call": 4096,
            "input_cost_per_mtok": 2.50,
            "output_cost_per_mtok": 10.00,
            "capabilities": {
                "text_generation": True,
                "tool_use": True,
                "images": True,
                "web_search": False,
                "reasoning": True,
            },
            "supported_languages": 23,
        }

    def validate_api_key(self) -> bool:
        """API 키 검증"""
        try:
            response = self.client.models.get(self.model)
            return response is not None
        except Exception:
            return False

    def estimate_tokens(self, text: str) -> int:
        """Cohere 토큰화"""
        # 대략적 추정: 1 토큰 ≈ 4자
        return len(text) // 4

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """비용 계산"""
        input_cost = (input_tokens / 1_000_000) * self.get_model_info()["input_cost_per_mtok"]
        output_cost = (output_tokens / 1_000_000) * self.get_model_info()["output_cost_per_mtok"]
        return input_cost + output_cost
```

### 2.3 테스트 코드

**파일**: `tests/test_cohere.py`

```python
import pytest
import os
from synod.providers.cohere import CohereProvider

class TestCohereProvider:
    """Cohere 제공자 테스트"""

    @pytest.fixture
    def provider(self):
        """테스트용 제공자 생성"""
        api_key = os.getenv("COHERE_API_KEY")
        if not api_key:
            pytest.skip("COHERE_API_KEY 환경변수가 설정되지 않았습니다")
        return CohereProvider(api_key)

    def test_api_key_validation(self, provider):
        """API 키 검증 테스트"""
        assert provider.validate_api_key() is True

    def test_model_info(self, provider):
        """모델 정보 반환 테스트"""
        info = provider.get_model_info()
        assert info["context_window"] == 256000
        assert info["model"] == "command-a-reasoning-08-2025"

    def test_generate(self, provider):
        """텍스트 생성 테스트"""
        prompt = "AI의 장점 3가지를 한 문장으로 설명하세요"
        response = provider.generate(prompt)
        assert isinstance(response, str)
        assert len(response) > 0

    def test_debate_act1(self, provider):
        """ACT I 토론 테스트"""
        result = provider.debate(
            position="",
            opposition="",
            topic="AI는 인류에게 더 이로운가?",
            act=1
        )
        assert result["act"] == 1
        assert len(result["response"]) > 0

    def test_estimate_tokens(self, provider):
        """토큰 추정 테스트"""
        text = "Hello world" * 100
        tokens = provider.estimate_tokens(text)
        assert tokens > 0

    def test_calculate_cost(self, provider):
        """비용 계산 테스트"""
        cost = provider.calculate_cost(1000, 500)
        assert cost > 0
        # $2.50/$10.00 가격 기반 검증
        expected = (1000 / 1_000_000) * 2.50 + (500 / 1_000_000) * 10.00
        assert abs(cost - expected) < 0.0001
```

---

## Phase 3: AI21 Jamba 통합 (1-2주)

### 3.1 AI21 제공자 구현

**파일**: `synod/providers/ai21.py`

```python
import ai21
import os
from typing import Dict, Optional
from .base import BaseProvider

class AI21Provider(BaseProvider):
    """AI21 Labs Jamba 제공자"""

    def __init__(self, api_key: Optional[str] = None, model: str = "jamba-1-large"):
        api_key = api_key or os.getenv("AI21_API_KEY")
        if not api_key:
            raise ValueError("AI21_API_KEY 환경변수가 설정되지 않았습니다")

        super().__init__(api_key, model)
        self.client = ai21.AI21Client(api_key=api_key)

    def generate(
        self,
        prompt: str,
        context: Optional[str] = None,
        temperature: float = 0.5,
        max_tokens: int = 2048,
    ) -> str:
        """
        AI21 Jamba API를 사용해 텍스트 생성

        Args:
            prompt: 사용자 프롬프트
            context: 추가 컨텍스트 (256K 토큰까지 지원)
            temperature: 창의성 수준
            max_tokens: 최대 출력 토큰

        Returns:
            생성된 텍스트
        """

        if context:
            full_prompt = f"{context}\n\n{prompt}"
        else:
            full_prompt = prompt

        try:
            response = self.client.completion.create(
                model=self.model,
                prompt=full_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=0.95,
            )

            return response.choices[0].text

        except Exception as e:
            raise RuntimeError(f"AI21 API 오류: {str(e)}")

    def debate(
        self,
        position: str,
        opposition: str,
        topic: str,
        act: int = 1,
    ) -> Dict:
        """토론 응답 생성 (Cohere와 동일 인터페이스)"""

        if act == 1:
            prompt = self._make_act1_prompt(topic)
        elif act == 2:
            prompt = self._make_act2_prompt(topic, opposition)
        elif act == 3:
            prompt = self._make_act3_prompt(topic, position, opposition)
        else:
            raise ValueError(f"유효하지 않은 ACT: {act}")

        response_text = self.generate(prompt)

        return {
            "provider": "ai21",
            "model": self.model,
            "act": act,
            "response": response_text,
            "tokens_used": self.estimate_tokens(response_text),
        }

    def _make_act1_prompt(self, topic: str) -> str:
        """ACT I 프롬프트"""
        return f"주제: {topic}\n\n명확한 솔루션을 제시하세요:\n"

    def _make_act2_prompt(self, topic: str, opposition: str) -> str:
        """ACT II 프롬프트"""
        return f"주제: {topic}\n\n상대방 입장: {opposition}\n\n논리적 허점을 지적하세요:\n"

    def _make_act3_prompt(self, topic: str, position: str, opposition: str) -> str:
        """ACT III 프롬프트"""
        return f"Position A: {position}\n\nPosition B: {opposition}\n\n판정하세요:\n"

    def get_model_info(self) -> Dict:
        """모델 정보"""
        pricing = {
            "jamba-1-mini": {"input": 0.20, "output": 0.40},
            "jamba-1-large": {"input": 2.00, "output": 8.00},
            "jamba-reasoning": {"input": 2.00, "output": 8.00},
        }

        price = pricing.get(self.model, pricing["jamba-1-large"])

        return {
            "provider": "AI21 Labs",
            "model": self.model,
            "context_window": 256000,
            "max_tokens_per_call": 4096,
            "input_cost_per_mtok": price["input"],
            "output_cost_per_mtok": price["output"],
            "capabilities": {
                "text_generation": True,
                "function_calling": True,
                "images": False,
                "web_search": False,
                "reasoning": True,
            },
        }

    def validate_api_key(self) -> bool:
        """API 키 검증"""
        try:
            # 간단한 API 호출로 검증
            response = self.generate("test", max_tokens=10)
            return len(response) > 0
        except Exception:
            return False

    def estimate_tokens(self, text: str) -> int:
        """토큰 추정"""
        return len(text) // 4

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """비용 계산"""
        info = self.get_model_info()
        input_cost = (input_tokens / 1_000_000) * info["input_cost_per_mtok"]
        output_cost = (output_tokens / 1_000_000) * info["output_cost_per_mtok"]
        return input_cost + output_cost
```

---

## Phase 4: 통합 및 라우팅 (2-4주)

### 4.1 설정 파일

**파일**: `synod/config.py`

```python
import os
from enum import Enum

class ProviderType(Enum):
    GEMINI = "gemini"
    OPENAI = "openai"
    COHERE = "cohere"
    AI21 = "ai21"
    PERPLEXITY = "perplexity"
    CLAUDE = "claude"

class DebateConfig:
    """토론 설정"""

    # 각 ACT 단계별 제공자
    PROVIDERS = {
        "act1_solver": ProviderType.AI21,      # 솔루션 생성 (비용 최적)
        "act2_critic": ProviderType.COHERE,    # 비판 (추론 능력)
        "act3_judge": ProviderType.CLAUDE,     # 최종 판정 (기존)
        "fallback": ProviderType.AI21,         # 백업
    }

    # 제공자별 설정
    PROVIDER_CONFIG = {
        ProviderType.COHERE: {
            "api_key": os.getenv("COHERE_API_KEY"),
            "model": "command-a-reasoning-08-2025",
            "temperature": 0.5,
            "max_tokens": 2048,
        },
        ProviderType.AI21: {
            "api_key": os.getenv("AI21_API_KEY"),
            "model": "jamba-1-large",
            "temperature": 0.5,
            "max_tokens": 2048,
        },
        ProviderType.PERPLEXITY: {
            "api_key": os.getenv("PERPLEXITY_API_KEY"),
            "model": "sonar-pro",
            "search_mode": "high",
        },
    }

    # 토론 설정
    NUM_ROUNDS = 3
    TIMEOUT_SECONDS = 120
    MAX_CONTEXT_TOKENS = 250000
    ENABLE_COST_TRACKING = True
    ENABLE_LOGGING = True
```

### 4.2 라우터 구현

**파일**: `synod/router.py`

```python
from typing import Dict, Optional
from synod.config import DebateConfig, ProviderType
from synod.providers.cohere import CohereProvider
from synod.providers.ai21 import AI21Provider

class ProviderRouter:
    """제공자 라우팅"""

    def __init__(self):
        self.providers = {}
        self.config = DebateConfig()

    def get_provider(self, provider_type: ProviderType):
        """제공자 인스턴스 반환"""

        if provider_type in self.providers:
            return self.providers[provider_type]

        config = self.config.PROVIDER_CONFIG.get(provider_type)

        if provider_type == ProviderType.COHERE:
            provider = CohereProvider(config["api_key"])
        elif provider_type == ProviderType.AI21:
            provider = AI21Provider(
                api_key=config["api_key"],
                model=config["model"]
            )
        else:
            raise ValueError(f"미지원 제공자: {provider_type}")

        self.providers[provider_type] = provider
        return provider

    def route_debate(self, topic: str, act: int) -> Dict:
        """ACT 단계에 따라 적절한 제공자로 라우팅"""

        act_name = f"act{act}_solver" if act == 1 else f"act{act}_critic"
        provider_type = self.config.PROVIDERS.get(act_name)

        if not provider_type:
            raise ValueError(f"라우팅 정책 없음: {act_name}")

        provider = self.get_provider(provider_type)
        return provider.debate(topic=topic, act=act, position="", opposition="")
```

---

## Phase 5: 테스트 및 검증 (1-2주)

### 5.1 통합 테스트

**파일**: `tests/test_integration.py`

```python
import pytest
from synod.router import ProviderRouter
from synod.config import DebateConfig, ProviderType

class TestIntegration:
    """통합 테스트"""

    @pytest.fixture
    def router(self):
        return ProviderRouter()

    def test_full_debate_cohere(self, router):
        """Cohere 전체 토론"""
        topic = "AI는 인류에게 이로운가?"

        # ACT I: 솔루션
        result1 = router.route_debate(topic, act=1)
        assert result1["provider"] in ["cohere", "ai21"]
        assert len(result1["response"]) > 0

        # ACT II: 비판
        result2 = router.route_debate(topic, act=2)
        assert len(result2["response"]) > 0

        # ACT III: 판정
        result3 = router.route_debate(topic, act=3)
        assert len(result3["response"]) > 0

    def test_provider_switching(self, router):
        """제공자 전환 테스트"""
        provider1 = router.get_provider(ProviderType.COHERE)
        provider2 = router.get_provider(ProviderType.AI21)

        assert provider1 is not provider2

    def test_cost_calculation(self, router):
        """비용 계산 테스트"""
        cohere = router.get_provider(ProviderType.COHERE)
        ai21 = router.get_provider(ProviderType.AI21)

        cost_cohere = cohere.calculate_cost(1000, 500)
        cost_ai21 = ai21.calculate_cost(1000, 500)

        assert cost_cohere > 0
        assert cost_ai21 > 0
        # AI21이 더 저렴해야 함
        assert cost_ai21 <= cost_cohere
```

---

## 배포 체크리스트

### ✅ 개발
- [ ] API 키 설정
- [ ] 라이브러리 설치
- [ ] 기본 제공자 클래스 구현
- [ ] Cohere 제공자 구현
- [ ] AI21 제공자 구현
- [ ] 단위 테스트 작성 및 통과

### ✅ 테스트
- [ ] 통합 테스트
- [ ] 전체 토론 flow 테스트
- [ ] 비용 계산 검증
- [ ] 성능 벤치마크

### ✅ 배포
- [ ] 문서 작성
- [ ] 환경변수 설정
- [ ] 모니터링 세팅
- [ ] 성능 모니터링

### ✅ 선택사항
- [ ] Perplexity 웹 검색 통합
- [ ] 사실 검증 파이프라인
- [ ] 비용 대시보드

---

## 모니터링 및 최적화

### 비용 추적

```python
# synod/monitoring.py
from datetime import datetime

class CostTracker:
    """비용 추적"""

    def __init__(self):
        self.logs = []

    def log_usage(self, provider: str, input_tokens: int, output_tokens: int, cost: float):
        """사용량 기록"""
        self.logs.append({
            "timestamp": datetime.now(),
            "provider": provider,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost,
        })

    def get_daily_cost(self):
        """일일 비용"""
        return sum(log["cost"] for log in self.logs)

    def get_monthly_estimate(self):
        """월간 예상 비용"""
        daily_cost = self.get_daily_cost()
        # 30일 기준
        return daily_cost * 30
```

---

## 문제 해결

### Cohere 연결 오류
```bash
# API 키 확인
echo $COHERE_API_KEY

# SDK 버전 확인
pip show cohere

# 다시 설치
pip install --upgrade cohere
```

### AI21 API 오류
```bash
# API 키 확인
echo $AI21_API_KEY

# 시도 횟수 제한 확인
# API 대시보드에서 rate limit 확인
```

### 토큰 초과
```python
# 컨텍스트 길이 확인
max_context = provider.get_model_info()["context_window"]
current_tokens = len(context) // 4  # 대략적

if current_tokens > max_context:
    # 오래된 대화 제거
    context = context[-max_context:]
```

---

## 다음 단계

1. ✅ **API 통합** 완료
2. → **성능 테스트** (응답 시간, 비용)
3. → **사용자 테스트** (토론 품질)
4. → **프로덕션 배포**
5. → **모니터링 및 최적화**

---

**최종 업데이트**: 2026년 2월 5일
