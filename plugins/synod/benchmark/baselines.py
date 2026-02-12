#!/usr/bin/env python3
"""Baseline implementations for Synod benchmark comparison"""

import json
import os
import time
from collections import Counter
from dataclasses import dataclass
from typing import Optional

import google.generativeai as genai
from anthropic import Anthropic
from openai import OpenAI


@dataclass
class BaselineResult:
    method: str
    response: str
    extracted_answer: Optional[str]
    elapsed_seconds: float
    tokens_used: int
    cost_usd: float
    error: Optional[str] = None


class BaselineRunner:
    """Run baseline methods for benchmark comparison"""

    def __init__(self):
        self.anthropic = Anthropic()
        self.openai = OpenAI()
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        self.gemini = genai.GenerativeModel("gemini-2.0-flash")

    def _extract_answer(self, response: str) -> Optional[str]:
        """Extract numeric answer from response"""
        import re

        patterns = [
            r"####\s*(-?\d+(?:,\d+)*(?:\.\d+)?)",
            r"(?:answer|답|정답)[:\s]*(-?\d+(?:,\d+)*(?:\.\d+)?)",
            r"(?:therefore|thus|따라서|그러므로)[,\s]*.*?(-?\d+(?:,\d+)*(?:\.\d+)?)",
            r"\*\*(-?\d+(?:,\d+)*(?:\.\d+)?)\*\*",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                return matches[-1].replace(",", "")

        numbers = re.findall(r"(?<!\d)(-?\d+(?:\.\d+)?)(?!\d)", response)
        return numbers[-1] if numbers else None

    def run_claude_only(self, question: str) -> BaselineResult:
        """Run Claude-only baseline"""
        start = time.time()
        try:
            response = self.anthropic.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": f"Solve this math problem step by step. End with #### followed by the numeric answer.\n\n{question}",
                    }
                ],
            )
            text = response.content[0].text
            tokens = response.usage.input_tokens + response.usage.output_tokens
            # Claude Sonnet pricing: $3/$15 per 1M tokens
            cost = (response.usage.input_tokens * 3 + response.usage.output_tokens * 15) / 1_000_000

            return BaselineResult(
                method="claude_only",
                response=text,
                extracted_answer=self._extract_answer(text),
                elapsed_seconds=time.time() - start,
                tokens_used=tokens,
                cost_usd=cost,
            )
        except Exception as e:
            return BaselineResult(
                method="claude_only",
                response="",
                extracted_answer=None,
                elapsed_seconds=time.time() - start,
                tokens_used=0,
                cost_usd=0,
                error=str(e),
            )

    def run_gpt4o_only(self, question: str) -> BaselineResult:
        """Run GPT-4o-only baseline"""
        start = time.time()
        try:
            response = self.openai.chat.completions.create(
                model="gpt-4o",
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": f"Solve this math problem step by step. End with #### followed by the numeric answer.\n\n{question}",
                    }
                ],
            )
            text = response.choices[0].message.content
            tokens = response.usage.total_tokens
            # GPT-4o pricing: $2.5/$10 per 1M tokens
            cost = (
                response.usage.prompt_tokens * 2.5 + response.usage.completion_tokens * 10
            ) / 1_000_000

            return BaselineResult(
                method="gpt4o_only",
                response=text,
                extracted_answer=self._extract_answer(text),
                elapsed_seconds=time.time() - start,
                tokens_used=tokens,
                cost_usd=cost,
            )
        except Exception as e:
            return BaselineResult(
                method="gpt4o_only",
                response="",
                extracted_answer=None,
                elapsed_seconds=time.time() - start,
                tokens_used=0,
                cost_usd=0,
                error=str(e),
            )

    def run_gemini_only(self, question: str) -> BaselineResult:
        """Run Gemini-only baseline"""
        start = time.time()
        try:
            response = self.gemini.generate_content(
                f"Solve this math problem step by step. End with #### followed by the numeric answer.\n\n{question}"
            )
            text = response.text
            # Gemini Flash pricing is very low
            tokens = len(text.split()) * 2  # Rough estimate
            cost = tokens * 0.0001 / 1000  # ~$0.0001 per 1K tokens

            return BaselineResult(
                method="gemini_only",
                response=text,
                extracted_answer=self._extract_answer(text),
                elapsed_seconds=time.time() - start,
                tokens_used=tokens,
                cost_usd=cost,
            )
        except Exception as e:
            return BaselineResult(
                method="gemini_only",
                response="",
                extracted_answer=None,
                elapsed_seconds=time.time() - start,
                tokens_used=0,
                cost_usd=0,
                error=str(e),
            )

    def run_majority_vote(self, question: str) -> BaselineResult:
        """Run 3-model majority vote baseline"""
        start = time.time()

        # Get answers from all three
        claude_result = self.run_claude_only(question)
        gpt4o_result = self.run_gpt4o_only(question)
        gemini_result = self.run_gemini_only(question)

        answers = [
            claude_result.extracted_answer,
            gpt4o_result.extracted_answer,
            gemini_result.extracted_answer,
        ]

        # Filter None values and find majority
        valid_answers = [a for a in answers if a is not None]
        if valid_answers:
            counter = Counter(valid_answers)
            majority_answer = counter.most_common(1)[0][0]
        else:
            majority_answer = None

        total_tokens = (
            claude_result.tokens_used + gpt4o_result.tokens_used + gemini_result.tokens_used
        )
        total_cost = claude_result.cost_usd + gpt4o_result.cost_usd + gemini_result.cost_usd

        response_summary = f"""
Claude: {claude_result.extracted_answer}
GPT-4o: {gpt4o_result.extracted_answer}
Gemini: {gemini_result.extracted_answer}
Majority: {majority_answer}
"""

        return BaselineResult(
            method="majority_vote",
            response=response_summary,
            extracted_answer=majority_answer,
            elapsed_seconds=time.time() - start,
            tokens_used=total_tokens,
            cost_usd=total_cost,
        )


def run_baselines(question: str) -> dict:
    """Run all baselines and return results"""
    runner = BaselineRunner()

    results = {
        "claude_only": runner.run_claude_only(question),
        "gpt4o_only": runner.run_gpt4o_only(question),
        "majority_vote": runner.run_majority_vote(question),
    }

    return {k: vars(v) for k, v in results.items()}


if __name__ == "__main__":
    # Test with a sample question
    test_question = "Janet's ducks lay 16 eggs per day. She eats three for breakfast every morning and bakes muffins for her friends every day with four. She sells the remainder at the farmers' market daily for $2 per fresh duck egg. How much in dollars does she make every day at the farmers' market?"

    results = run_baselines(test_question)
    print(json.dumps(results, indent=2))
