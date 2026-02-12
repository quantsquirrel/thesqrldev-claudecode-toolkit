#!/usr/bin/env python3
"""
synod-setup - Synod 초기 설정 및 모델 가용성 테스트

Handles: dependency installation, CLI wrapper creation, API key validation, model testing.

Usage:
    synod-setup
    synod-setup --skip-deps
"""

import json
import os
import stat
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# Paths
TOOLS_DIR = Path(__file__).parent
SYNOD_DIR = Path("~/.synod").expanduser()
SYNOD_BIN = SYNOD_DIR / "bin"

# CLI wrapper targets: command_name -> script_filename
CLI_TOOLS = {
    "gemini-3": "gemini-3.py",
    "openai-cli": "openai-cli.py",
    "deepseek-cli": "deepseek-cli.py",
    "groq-cli": "groq-cli.py",
    "grok-cli": "grok-cli.py",
    "mistral-cli": "mistral-cli.py",
    "openrouter-cli": "openrouter-cli.py",
    "synod-parser": "synod-parser.py",
    "synod-classifier": "synod-classifier.py",
    "synod-canary": "synod-canary.py",
}

# Required Python packages: pip_name -> import_name
REQUIRED_PACKAGES = {
    "google-genai": "google.genai",
    "openai": "openai",
    "httpx": "httpx",
}

# Provider definitions for testing
MODELS_TO_TEST = {
    "gemini": {
        "cli": "gemini-3.py",
        "models": ["flash", "pro"],
        "env_key": "GEMINI_API_KEY",
        "env_key_compat": "GOOGLE_API_KEY",
    },
    "openai": {
        "cli": "openai-cli.py",
        "models": ["gpt4o", "o3"],
        "env_key": "OPENAI_API_KEY",
    },
    "deepseek": {
        "cli": "deepseek-cli.py",
        "models": ["chat", "reasoner"],
        "env_key": "DEEPSEEK_API_KEY",
    },
    "groq": {
        "cli": "groq-cli.py",
        "models": ["70b", "8b"],
        "env_key": "GROQ_API_KEY",
    },
    "grok": {
        "cli": "grok-cli.py",
        "models": ["fast", "grok4"],
        "env_key": "XAI_API_KEY",
    },
    "mistral": {
        "cli": "mistral-cli.py",
        "models": ["large", "small"],
        "env_key": "MISTRAL_API_KEY",
    },
    "openrouter": {
        "cli": "openrouter-cli.py",
        "models": ["claude", "llama", "qwen"],
        "env_key": "OPENROUTER_API_KEY",
    },
}

TEST_TARGETS = [
    ("gemini", "flash"),
    ("gemini", "pro"),
    ("openai", "gpt4o"),
    ("openai", "o3"),
    ("openrouter", "claude"),
]

TEST_PROMPT = "Explain the SOLID principles in software engineering in 3 sentences."
TIMEOUT_THRESHOLD = 120
SLOW_THRESHOLD = 60


@dataclass
class TestResult:
    provider: str
    model: str
    success: bool
    latency_sec: float
    status: str  # "recommended" | "usable" | "slow" | "timeout" | "failed"
    error: str | None = None


# ---------------------------------------------------------------------------
# Step 0: Dependency Installation
# ---------------------------------------------------------------------------


def check_and_install_dependencies(skip: bool = False) -> bool:
    """Check and install required Python packages."""
    print("Step 0/3: Python 의존성 확인")

    missing = []
    for pip_name, import_name in REQUIRED_PACKAGES.items():
        module = import_name.split(".")[0]
        try:
            __import__(module)
            print(f"  ✓ {pip_name} 설치됨")
        except ImportError:
            print(f"  ✗ {pip_name} 미설치")
            missing.append(pip_name)

    if not missing:
        return True

    if skip:
        print(f"\n  [건너뜀] --skip-deps 플래그로 의존성 설치를 건너뜁니다.")
        print(f"  수동 설치: pip install {' '.join(missing)}")
        return False

    print(f"\n  {len(missing)}개 패키지 설치 중: {', '.join(missing)}")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--user"] + missing,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            print("  ✓ 의존성 설치 완료")
            return True
        else:
            stderr = result.stderr or ""
            if "externally-managed-environment" in stderr:
                print("  ✗ 시스템 Python이 외부 관리 모드입니다 (PEP 668).")
                print(f"  수동 설치: pip install --break-system-packages {' '.join(missing)}")
                print("  또는 venv 사용을 권장합니다.")
            else:
                print(f"  ✗ 설치 실패: {stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        print("  ✗ 설치 타임아웃 (120초)")
        return False
    except Exception as e:
        print(f"  ✗ 설치 오류: {e}")
        return False


# ---------------------------------------------------------------------------
# Step 1: CLI Wrapper Installation
# ---------------------------------------------------------------------------


def install_cli_wrappers() -> dict[str, str]:
    """Create wrapper scripts in ~/.synod/bin/ for all available CLI tools."""
    print(f"\nStep 1/3: CLI 도구 설치 ({SYNOD_BIN})")
    SYNOD_BIN.mkdir(parents=True, exist_ok=True)

    results = {}
    for cmd_name, filename in CLI_TOOLS.items():
        source = TOOLS_DIR / filename
        if not source.exists():
            results[cmd_name] = "not_found"
            continue

        target = SYNOD_BIN / cmd_name
        wrapper_content = f"#!/bin/sh\nexec python3 \"{source}\" \"$@\"\n"

        # Write wrapper script
        target.write_text(wrapper_content)
        target.chmod(target.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        results[cmd_name] = "installed"
        print(f"  ✓ {cmd_name} 설치됨")

    not_found = [k for k, v in results.items() if v == "not_found"]
    if not_found:
        print(f"  [참고] {len(not_found)}개 도구 원본 없음: {', '.join(not_found)}")

    return results


# ---------------------------------------------------------------------------
# Step 2: API Key Validation
# ---------------------------------------------------------------------------


def check_api_key(provider: str) -> tuple[bool, str]:
    """API key check with backward compatibility for Gemini."""
    config = MODELS_TO_TEST[provider]
    env_key = config["env_key"]
    has_key = os.environ.get(env_key) is not None

    # Backward compat: check alternate key name for Gemini
    if not has_key and "env_key_compat" in config:
        compat_key = config["env_key_compat"]
        if os.environ.get(compat_key):
            has_key = True
            env_key = f"{compat_key} (호환 - {config['env_key']} 권장)"

    return has_key, env_key


def check_all_api_keys() -> list[str]:
    """Check API keys for all providers with available CLI tools."""
    print("\nStep 2/3: API 키 확인")
    providers_with_keys = []

    for provider in MODELS_TO_TEST:
        cli_path = TOOLS_DIR / MODELS_TO_TEST[provider]["cli"]
        if not cli_path.exists():
            continue

        has_key, env_key = check_api_key(provider)
        icon = "✓" if has_key else "✗"
        status = "설정됨" if has_key else "설정 안됨"
        print(f"  {icon} {env_key} ({status})")
        if has_key:
            providers_with_keys.append(provider)

    return providers_with_keys


# ---------------------------------------------------------------------------
# Step 3: Model Testing
# ---------------------------------------------------------------------------


def test_model(provider: str, model: str, timeout: int = TIMEOUT_THRESHOLD) -> TestResult:
    """Send test prompt to a model and measure response time."""
    cli_name = MODELS_TO_TEST[provider]["cli"]
    cli_path = TOOLS_DIR / cli_name

    start_time = time.time()
    try:
        result = subprocess.run(
            ["python3", str(cli_path), "--model", model, TEST_PROMPT],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        latency = time.time() - start_time

        if result.returncode == 0:
            if latency < 10:
                status = "recommended"
            elif latency < SLOW_THRESHOLD:
                status = "usable"
            else:
                status = "slow"

            return TestResult(
                provider=provider,
                model=model,
                success=True,
                latency_sec=latency,
                status=status,
            )
        else:
            return TestResult(
                provider=provider,
                model=model,
                success=False,
                latency_sec=latency,
                status="failed",
                error=result.stderr[:200] if result.stderr else f"Exit code: {result.returncode}",
            )

    except subprocess.TimeoutExpired:
        return TestResult(
            provider=provider,
            model=model,
            success=False,
            latency_sec=timeout,
            status="timeout",
            error=f"Timeout after {timeout}s",
        )
    except Exception as e:
        return TestResult(
            provider=provider,
            model=model,
            success=False,
            latency_sec=0,
            status="failed",
            error=str(e),
        )


def print_results(results: list[TestResult]) -> None:
    """Print test results table."""
    print("\nProvider    Model              Latency    Status")
    print("─" * 55)

    for r in results:
        latency_str = f"{r.latency_sec:.1f}초" if r.success else "─"
        status_icon = {
            "recommended": "✓ 권장",
            "usable": "✓ 사용 가능",
            "slow": "⚠ 느림",
            "timeout": "✗ 타임아웃",
            "failed": "✗ 실패",
        }.get(r.status, "?")

        print(f"{r.provider:<12}{r.model:<19}{latency_str:<11}{status_icon}")

        if r.error:
            print(f"            └─ {r.error[:50]}")


def generate_recommendations(results: list[TestResult]) -> dict:
    """Generate recommended model settings per provider."""
    recommendations = {}
    for provider in ["gemini", "openai"]:
        provider_results = [r for r in results if r.provider == provider and r.success]
        if provider_results:
            status_order = {"recommended": 0, "usable": 1, "slow": 2}
            best = min(
                provider_results,
                key=lambda r: (status_order.get(r.status, 99), r.latency_sec),
            )
            recommendations[provider] = best.model
    return recommendations


# ---------------------------------------------------------------------------
# Save Results
# ---------------------------------------------------------------------------


def save_results(results: list[TestResult], recommendations: dict) -> None:
    """Save results to JSON file with path information for synod.md."""
    output_path = SYNOD_DIR / "setup-result.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tools_dir": str(TOOLS_DIR),
        "synod_bin": str(SYNOD_BIN),
        "results": [
            {
                "provider": r.provider,
                "model": r.model,
                "success": r.success,
                "latency_sec": r.latency_sec,
                "status": r.status,
                "error": r.error,
            }
            for r in results
        ],
        "recommendations": recommendations,
    }

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\n[저장됨] {output_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    print("[Synod Setup] 초기 설정을 시작합니다...\n")

    skip_deps = "--skip-deps" in sys.argv

    # Step 0: Dependencies
    deps_ok = check_and_install_dependencies(skip=skip_deps)

    # Step 1: CLI wrappers
    cli_results = install_cli_wrappers()

    # Step 2: API keys
    providers_with_keys = check_all_api_keys()

    # Step 3: Model testing
    print(f"\nStep 3/3: 모델 응답 시간 측정 (타임아웃: {TIMEOUT_THRESHOLD}초)")

    targets = [
        (provider, model)
        for provider, model in TEST_TARGETS
        if provider in providers_with_keys
    ]

    if not targets:
        print("\n[오류] 테스트 가능한 모델이 없습니다. API 키를 확인하세요.")
        print("  export GEMINI_API_KEY='your-key'")
        print("  export OPENAI_API_KEY='your-key'")
        # Still save partial results (path info is useful even without model tests)
        save_results([], {})
        sys.exit(1)

    results = []
    for provider, model in targets:
        print(f"  테스트 중: {provider}/{model}...", end="", flush=True)
        result = test_model(provider, model)
        results.append(result)
        icon = "✓" if result.success else "✗"
        print(f" {icon} ({result.latency_sec:.1f}s)")

    print_results(results)

    recommendations = generate_recommendations(results)
    if recommendations:
        print("\n[권장 환경변수 설정]")
        if "gemini" in recommendations:
            print(f"  export SYNOD_GEMINI_MODEL={recommendations['gemini']}")
        if "openai" in recommendations:
            print(f"  export SYNOD_OPENAI_MODEL={recommendations['openai']}")

    save_results(results, recommendations)

    success_count = sum(1 for r in results if r.success)
    total_count = len(results)
    print(f"\n[완료] {success_count}/{total_count} 모델 사용 가능")

    if success_count >= 2:
        print("Synod를 사용할 준비가 되었습니다!")
        sys.exit(0)
    elif success_count >= 1:
        print("1개 모델만 사용 가능합니다. Claude + 1 모델로 동작합니다.")
        sys.exit(0)
    else:
        print("사용 가능한 외부 모델이 없습니다. API 키와 네트워크를 확인하세요.")
        sys.exit(1)


if __name__ == "__main__":
    main()
