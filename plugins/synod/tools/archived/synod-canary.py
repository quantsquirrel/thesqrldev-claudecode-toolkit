#!/usr/bin/env python3
"""
synod-canary - CLI for Canary Pre-Sampling health checks.

Usage:
    synod-canary --provider gemini
    synod-canary --provider gemini --model flash
    synod-canary --provider openai --model o3 --no-cache
    synod-canary --all

Implementation:
    Uses subprocess to call existing CLI tools (gemini-3.py, openai-cli.py, etc.)
    This avoids import path issues and API interface mismatches.
"""

import argparse
import json
import os
import sys

# Import path setup
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from canary import CANARY_MODEL_MAP, CLI_MAP, CanaryProbe
from model_stats import ModelStats


def probe_single(provider: str, model: str, no_cache: bool) -> dict:
    """Probe a single provider/model combination."""
    stats = ModelStats()
    probe = CanaryProbe(stats, use_cache=not no_cache)

    result = probe.probe(provider, model)
    result["provider"] = provider
    result["model"] = model or CANARY_MODEL_MAP.get(provider, "default")

    return result


def probe_all(no_cache: bool) -> list[dict]:
    """Probe all supported providers with their default canary models."""
    results = []
    for provider in CLI_MAP.keys():
        result = probe_single(provider, None, no_cache)
        results.append(result)
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Canary pre-sampling for model health checks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  synod-canary --provider gemini
  synod-canary --provider openai --model o3
  synod-canary --all
  synod-canary --provider gemini --no-cache
        """,
    )
    parser.add_argument(
        "--provider",
        "-p",
        choices=list(CLI_MAP.keys()),
        help="Model provider (required unless --all)",
    )
    parser.add_argument(
        "--model",
        "-m",
        help="Model name (e.g., flash, o3, gpt4o). Uses canary default if not specified.",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Bypass cache and force fresh probe",
    )
    parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="Probe all supported providers",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Only output JSON, no status messages",
    )

    args = parser.parse_args()

    # Validation
    if not args.all and not args.provider:
        parser.error("Either --provider or --all is required")

    try:
        if args.all:
            results = probe_all(args.no_cache)

            # Summary
            healthy_count = sum(1 for r in results if r.get("healthy", False))
            total_count = len(results)

            if not args.quiet:
                print(
                    f"[Canary] Probed {total_count} providers: {healthy_count} healthy",
                    file=sys.stderr,
                )

            print(json.dumps(results, indent=2))

            # Exit with error if any unhealthy
            sys.exit(0 if healthy_count == total_count else 1)
        else:
            result = probe_single(args.provider, args.model, args.no_cache)

            if not args.quiet:
                status = "healthy" if result.get("healthy") else "UNHEALTHY"
                latency = result.get("latency_ms", 0)
                cached = " (cached)" if result.get("cached") else ""
                print(
                    f"[Canary] {args.provider}: {status} ({latency:.0f}ms){cached}",
                    file=sys.stderr,
                )

                if result.get("fallback_recommended"):
                    print(
                        f"[Canary] Fallback recommended for {args.provider}",
                        file=sys.stderr,
                    )

            print(json.dumps(result, indent=2))
            sys.exit(0 if result.get("healthy", False) else 1)

    except Exception as e:
        error_result = {
            "healthy": False,
            "error": str(e),
            "fallback_recommended": True,
            "cached": False,
        }
        print(json.dumps(error_result, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
