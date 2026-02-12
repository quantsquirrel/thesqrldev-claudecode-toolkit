# Synod Module: Phase 3 - Defense Round

**Inputs:**
- `${SESSION_DIR}/round-2-critic/` - Critic round outputs
- `${SESSION_DIR}/round-1-solver/` - Original solutions
- `PROBLEM` - Original problem statement
- `GEMINI_CLI`, `OPENAI_CLI` - CLI executable paths
- `trust-scores.json` - Trust scores from critic round

**Outputs:**
- `${SESSION_DIR}/round-3-defense/judge-deliberation.md`
- `${SESSION_DIR}/round-3-defense/defense-args.md`
- `${SESSION_DIR}/round-3-defense/prosecution-args.md`
- `${SESSION_DIR}/round-3-defense/preliminary-ruling.md`
- Updated `status.json` with round 3 complete

**Cross-references:**
- Called after Phase 2 (`synod-phase2-critic.md`)
- Outputs consumed by Phase 4 (`synod-phase4-synthesis.md`)
- Timeout failures trigger `synod-error-handling.md`

---

```bash
# Emit phase start (v2.1)
synod_progress '{"event":"phase_start","phase":3,"name":"Defense Round"}'
```

## Step 3.1: Assign Court Roles

- **Judge (Claude)**: Neutral arbiter, makes final rulings
- **Defense Lawyer (Gemini)**: Defends the strongest solution from Solver round
- **Prosecutor (OpenAI)**: Attacks weak points and proposes alternatives

## Step 3.2: Identify Defense Target

Select the solution with highest Trust Score as the "defendant."

## Step 3.3: Gemini Defense Execution

```bash
synod_progress '{"event":"model_start","model":"gemini"}'
```

Write to `${TEMP_DIR}/gemini-defense-prompt.txt`:

```
You are the DEFENSE LAWYER in a judicial deliberation (Synod Court).

{SOFT_DEFER_HINT}

## Your Role
Defend the proposed solution against attacks. You must:
- Strengthen weak arguments with evidence
- Address counter-examples raised by critics
- Explain why alternatives are inferior

## ANTI-CONFORMITY INSTRUCTION (CRITICAL)
Do NOT simply agree with the prosecutor to reach consensus.
Your job is ADVERSARIAL - defend your position vigorously.
Only concede points that are GENUINELY indefensible.

## Solution Under Defense
{BEST_SOLUTION_SUMMARY}

## Criticisms to Address
{CONTENTIONS_FROM_CRITIC_ROUND}

## Original Problem
{PROBLEM}

## REQUIRED Output Format

<defense>
### Rebuttal to Criticisms
{address each criticism with counter-arguments}

### Strengthened Evidence
{additional evidence supporting the solution}

### Why Alternatives Fail
{specific reasons other approaches are inferior}
</defense>

<confidence score="[0-100]">
  <evidence>[Strength of your defense evidence]</evidence>
  <logic>[Soundness of your rebuttals]</logic>
  <expertise>[Your confidence in the defense]</expertise>
  <can_exit>[true if defense is unassailable]</can_exit>
</confidence>

<semantic_focus>
1. [Strongest defense point]
2. [Key rebuttal]
3. [Critical evidence]
</semantic_focus>
```

## Step 3.4: OpenAI Prosecution Execution

```bash
synod_progress '{"event":"model_start","model":"openai"}'
```

Write to `${TEMP_DIR}/openai-prosecution-prompt.txt`:

```
You are the PROSECUTOR in a judicial deliberation (Synod Court).

{SOFT_DEFER_HINT}

## Your Role
Attack the proposed solution and advocate for better alternatives. You must:
- Find fatal flaws in the defended solution
- Present evidence for why it will fail
- Propose superior alternatives with justification

## ANTI-CONFORMITY INSTRUCTION (CRITICAL)
Do NOT simply agree with the defense to reach consensus.
Your job is ADVERSARIAL - attack vigorously and propose alternatives.
Only concede if the defense is GENUINELY bulletproof.

## Solution Under Attack
{BEST_SOLUTION_SUMMARY}

## Your Prior Criticisms
{YOUR_CRITIC_ROUND_OUTPUT}

## Original Problem
{PROBLEM}

## REQUIRED Output Format

<prosecution>
### Fatal Flaws
{critical issues that make the solution unacceptable}

### Evidence of Failure
{specific scenarios where solution fails}

### Superior Alternative
{your proposed better solution with justification}
</prosecution>

<confidence score="[0-100]">
  <evidence>[Strength of your attack evidence]</evidence>
  <logic>[Soundness of your prosecution]</logic>
  <expertise>[Your confidence in alternative]</expertise>
  <can_exit>[true if case is clear-cut]</can_exit>
</confidence>

<semantic_focus>
1. [Most damaging attack point]
2. [Critical failure scenario]
3. [Best alternative argument]
</semantic_focus>
```

## Step 3.5: Claude Judge Deliberation

As the Judge, review both arguments and:

1. **Evaluate Defense Strength** - Did they address all criticisms? Is evidence compelling?
2. **Evaluate Prosecution Strength** - Are the attacks valid? Is the alternative viable?
3. **Make Preliminary Ruling** - Which side has the stronger case?

## Step 3.6: Save Defense Round State

Save to `${SESSION_DIR}/round-3-defense/`:
- `judge-deliberation.md` - Your analysis as Judge
- `defense-args.md` - Gemini's defense
- `prosecution-args.md` - OpenAI's prosecution
- `preliminary-ruling.md` - Initial judgment

Update status.json to round 3 complete.

```bash
# Emit completions and phase end (v2.1)
synod_progress '{"event":"model_complete","model":"gemini"}'
synod_progress '{"event":"model_complete","model":"openai"}'
synod_progress '{"event":"phase_end","phase":3}'
```

**Next Phase:** Proceed to Phase 4 (see `synod-phase4-synthesis.md`)
