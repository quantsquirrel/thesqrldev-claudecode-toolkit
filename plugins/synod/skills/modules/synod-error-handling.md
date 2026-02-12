# Synod Module: Error Handling & Fallbacks

**Inputs:**
- Error context (timeout, format error, API error, etc.)
- Current round and phase information
- Available fallback models

**Outputs:**
- Retry commands or fallback model selection
- Error annotations in session state
- Continued execution or graceful degradation

**Cross-references:**
- Called by all phase modules when errors occur
- Integrates with all phases for error recovery

---

## Timeout Fallback Chain

### If Gemini times out (120s):
1. Retry: `$GEMINI_CLI --model flash --thinking medium` (downgrade)
2. Retry: `$GEMINI_CLI --model flash --thinking low`
3. Final: Continue without Gemini, note in synthesis: "[Gemini 사용 불가 - 시간 초과]"

### If OpenAI times out (120s):
1. Retry: `$OPENAI_CLI --model o3 --reasoning medium` (downgrade)
2. Retry: `$OPENAI_CLI --model gpt4o`
3. Final: Continue without OpenAI, note in synthesis: "[OpenAI 사용 불가 - 시간 초과]"

### Extended Provider Fallbacks:

| Provider | Fallback Chain |
|----------|---------------|
| DeepSeek | reasoner (high→medium→low) → chat |
| Groq | 70b → mixtral → 8b |
| Grok | grok4 → fast → mini |
| Mistral | large → medium → small |

## Format Enforcement Protocol

**If model response lacks required XML blocks:**

Send re-prompt:
```
Your previous response was missing the required XML format. Please add the following blocks AT THE END of your response:

<confidence score="[0-100]">
  <evidence>[What facts support your solution?]</evidence>
  <logic>[How sound is your reasoning?]</logic>
  <expertise>[Your domain confidence]</expertise>
  <can_exit>[true if confidence >= 90 and solution is complete]</can_exit>
</confidence>

<semantic_focus>
1. [Primary debate point]
2. [Secondary debate point]
3. [Tertiary debate point]
</semantic_focus>

Your original answer (keep this, just add XML at end):
---
{ORIGINAL_RESPONSE}
---
```

**Max retries:** 2 per model per round

**If still malformed after retries:**
```bash
# Apply defaults via parser
$SYNOD_PARSER_CLI "$(cat response.txt)"  # Returns defaults with format_warning
```

Default values:
- `confidence score="50"`
- `can_exit="false"`
- `semantic_focus` = extracted key sentences

## Low Trust Score Fallback

**If ALL models have Trust Score < 0.5:**
1. Do NOT exclude all agents
2. Keep the agent with highest Trust Score
3. Add warning to synthesis: "[낮은 신뢰도 상황: 모든 모델이 임계값 이하의 점수를 받았습니다. 결과를 주의 깊게 검토해야 합니다.]"
4. Set `final_confidence` cap at 60%

## API Error Handling

**If CLI returns error (non-zero exit):**
1. Check stderr for rate limit message → wait 30s, retry
2. Check for auth error → report to user, cannot continue
3. Other error → use fallback chain

**Error Categories:**

| Exit Code | Meaning | Action |
|-----------|---------|--------|
| 0 | Success | Proceed normally |
| 1 | General error | Check stderr, apply fallback |
| 124 | Timeout (from `timeout` command) | Trigger timeout fallback chain |
| 401 | Authentication error | Report to user, halt session |
| 429 | Rate limit | Wait 30s, retry once |
| Other | Unknown | Log error, apply fallback chain |

**Process Status Handling:**
- `"0"` = Success
- `"timeout"` = Killed by outer timeout
- `"missing"` = Process never started or crashed
- Any other = Subprocess error (check exit code)

**Graceful Degradation Strategy:**

1. **Single provider failure:** Continue with remaining 2 models
2. **Two provider failures:** Continue with Claude only, warn user
3. **All providers fail:** Save session state, report error, suggest retry

**Error Annotations:**

Add to `meta.json` when errors occur:
```json
{
  "errors": [
    {
      "round": 1,
      "provider": "gemini",
      "type": "timeout",
      "fallback_used": "flash-medium",
      "timestamp": "{ISO_TIMESTAMP}"
    }
  ]
}
```
