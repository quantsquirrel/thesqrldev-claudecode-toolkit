#!/usr/bin/env python3
"""Synod Classifier - Keyword-based prompt classifier for Synod execution modes

Determines mode (review, design, debug, idea, general) from user prompts.
"""

import argparse
import json
import os
import re
import sys


def _load_keyword_patterns():
    """Load keyword patterns from YAML config with hardcoded fallback."""
    try:
        import os
        tools_dir = os.path.dirname(os.path.abspath(__file__))
        if tools_dir not in sys.path:
            sys.path.insert(0, tools_dir)
        from synod_config import get_all_keywords
        yaml_keywords = get_all_keywords()
        if yaml_keywords:
            return yaml_keywords
    except (ImportError, FileNotFoundError, Exception):
        pass

    # Hardcoded fallback patterns
    return {
        'review': [
            r'리뷰', r'review', r'검토', r'코드\s*확인', r'PR\s*리뷰',
            r'버그\s*찾', r'문제\s*찾', r'개선\s*점', r'피드백'
        ],
        'design': [
            r'설계', r'design', r'아키텍처', r'architecture', r'구조',
            r'시스템\s*설계', r'API\s*설계', r'DB\s*설계', r'스키마'
        ],
        'debug': [
            r'디버그', r'debug', r'에러', r'error', r'버그', r'bug',
            r'안\s*됨', r'작동.*않', r'실패', r'fail', r'오류', r'exception'
        ],
        'idea': [
            r'아이디어', r'idea', r'브레인스토밍', r'brainstorm',
            r'제안', r'suggest', r'어떻게\s*하면', r'방법', r'대안'
        ]
    }


def classify_prompt(prompt):
    """
    Classify prompt into Synod execution mode using regex keyword patterns.

    Args:
        prompt: User's prompt text

    Returns:
        tuple: (mode, confidence)
    """
    # Load patterns from YAML config (with hardcoded fallback)
    patterns = _load_keyword_patterns()

    # Score each mode by counting matched patterns (absolute count)
    scores = {}
    for mode, pattern_list in patterns.items():
        matches = sum(1 for pattern in pattern_list
                      if re.search(pattern, prompt, re.IGNORECASE))
        scores[mode] = matches

    # Find best mode by absolute match count
    best_mode = max(scores, key=scores.get)
    best_count = scores[best_mode]

    # Default to "general" if no patterns matched at all
    if best_count == 0:
        return "general", 0.5

    # Calculate confidence: 1 match = 0.4, 2 = 0.6, 3+ = 0.8-1.0
    max_patterns = len(patterns[best_mode])
    confidence = min((best_count / max_patterns) * 3.0, 1.0)
    confidence = max(confidence, 0.3)  # minimum 0.3 if any match

    return best_mode, round(confidence, 2)


def classify_problem_type(prompt):
    """
    Classify the problem type from prompt.

    Args:
        prompt: User's prompt text

    Returns:
        str: coding|math|creative|general
    """
    # Check for coding indicators
    if re.search(r'```', prompt):  # code blocks
        return "coding"
    if re.search(r'\b(def|class|function|import|const|let|var)\b', prompt, re.IGNORECASE):
        return "coding"

    # Check for math indicators
    if re.search(r'\d+\s*[\+\-\*\/\=]\s*\d+', prompt):
        return "math"
    if re.search(r'수학|계산|algorithm', prompt, re.IGNORECASE):
        return "math"

    # Check for creative indicators
    if re.search(r'아이디어|브레인스토밍|창의|이름.*지어|naming', prompt, re.IGNORECASE):
        return "creative"

    return "general"


def determine_complexity(prompt):
    """
    Determine complexity level and recommended rounds.

    Args:
        prompt: User's prompt text

    Returns:
        tuple: (complexity_level, rounds)
    """
    # Count words
    word_count = len(prompt.split())

    # Count code blocks
    code_blocks = len(re.findall(r'```', prompt)) // 2

    # Count file mentions
    file_mentions = len(re.findall(r'\.\w{2,4}\b', prompt))

    # Calculate complexity score
    score = word_count / 100 + code_blocks * 0.5 + file_mentions * 0.3

    # Load complexity thresholds from config (with fallback defaults)
    try:
        tools_dir = os.path.dirname(os.path.abspath(__file__))
        if tools_dir not in sys.path:
            sys.path.insert(0, tools_dir)
        from synod_config import load_config
        cfg = load_config()
        complexity_cfg = cfg.get("complexity", {})
        simple_max = complexity_cfg.get("simple", {}).get("max_score", 0.5)
        medium_max = complexity_cfg.get("medium", {}).get("max_score", 2.0)
        simple_rounds = complexity_cfg.get("simple", {}).get("rounds", 2)
        medium_rounds = complexity_cfg.get("medium", {}).get("rounds", 3)
        complex_rounds = complexity_cfg.get("complex", {}).get("rounds", 4)
    except (ImportError, FileNotFoundError, Exception):
        simple_max, medium_max = 0.5, 2.0
        simple_rounds, medium_rounds, complex_rounds = 2, 3, 4

    if score < simple_max:
        return "simple", simple_rounds
    elif score < medium_max:
        return "medium", medium_rounds
    else:
        return "complex", complex_rounds


def main():
    parser = argparse.ArgumentParser(
        description='Classify prompts for Synod execution modes'
    )
    parser.add_argument(
        'prompt',
        nargs='?',
        help='Prompt text to classify (or read from stdin)'
    )
    parser.add_argument(
        '--mode-only',
        action='store_true',
        help='Output only the mode as plain text'
    )
    parser.add_argument(
        '--complexity',
        action='store_true',
        help='Include complexity analysis'
    )

    args = parser.parse_args()

    # Get prompt from args or stdin
    if args.prompt:
        prompt = args.prompt
    else:
        prompt = sys.stdin.read().strip()

    if not prompt:
        print("Error: No prompt provided", file=sys.stderr)
        sys.exit(1)

    # Classify mode
    mode, confidence = classify_prompt(prompt)

    # Mode-only output
    if args.mode_only:
        print(mode)
        return

    # Always include all fields (synod.md references them)
    problem_type = classify_problem_type(prompt)
    complexity_level, rounds = determine_complexity(prompt)

    # Determine tier from complexity (v3.1)
    try:
        from synod_config import get_tier
        tier = get_tier(complexity_level)
    except (ImportError, Exception):
        tier = "standard"

    result = {
        "mode": mode,
        "confidence": round(confidence, 2),
        "problem_type": problem_type,
        "complexity": complexity_level,
        "rounds": rounds,
        "tier": tier
    }

    # Output JSON
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
