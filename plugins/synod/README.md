<div align="center">

<!-- Hero Banner -->
<img src="assets/synod-banner.jpeg" alt="SYNOD - Multi-Agent Deliberation System" width="100%"/>

<br/>

<!-- Tagline -->
### *When one AI isn't enough, convene the council.*

<br/>

<!-- Status Badges -->
<p>
<a href="#-60-second-setup"><img src="https://img.shields.io/badge/⚡_Quick_Start-60s-F97316?style=flat-square" alt="Quick Start"/></a>
<a href="https://arxiv.org/abs/2309.13007"><img src="https://img.shields.io/badge/📚_Research-5_Papers-8B5CF6?style=flat-square" alt="Research"/></a>
<a href="LICENSE"><img src="https://img.shields.io/badge/📜_License-MIT-22C55E?style=flat-square" alt="License"/></a>
<a href="https://github.com/quantsquirrel/claude-synod-debate"><img src="https://img.shields.io/github/stars/quantsquirrel/claude-synod-debate?style=flat-square&logo=github" alt="Stars"/></a>
</p>

<!-- Language Toggle -->
**[English](README.md)** · **[한국어](README.ko.md)**

</div>

<br/>

<div align="center">

**😵‍💫 Single LLMs are overconfident** &nbsp;→&nbsp; **⚔️ Make them debate** &nbsp;→&nbsp; **✅ Better decisions**

</div>

<br/>

---

<div align="center">

## 🎭 THE THREE ACTS

*Every deliberation follows the same dramatic structure*

</div>

<br/>

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': { 'primaryColor': '#1e3a5f', 'secondaryColor': '#4a1d1d', 'tertiaryColor': '#1a3d1a'}}}%%
flowchart TB
    subgraph ACT1["🎬 ACT I · SOLVE"]
        G1["🔵 Gemini → Solution A"]
        O1["🟢 OpenAI → Solution B"]
    end

    subgraph ACT2["⚔️ ACT II · CRITIQUE"]
        G2["🔵 Gemini attacks B"]
        O2["🟢 OpenAI attacks A"]
    end

    subgraph ACT3["⚖️ ACT III · VERDICT"]
        C["🟠 Claude → Final Answer"]
    end

    ACT1 --> ACT2 --> ACT3

    style ACT1 fill:#1e3a5f,stroke:#3b82f6,stroke-width:2px,color:#fff
    style ACT2 fill:#4a1d1d,stroke:#ef4444,stroke-width:2px,color:#fff
    style ACT3 fill:#1a3d1a,stroke:#22c55e,stroke-width:2px,color:#fff
```

<div align="center">

| Act | What Happens | Why It Matters |
|:---:|:-------------|:---------------|
| **I** | Independent solutions emerge | No groupthink — maximum diversity |
| **II** | Cross-examination begins | Weaknesses exposed — biases challenged |
| **III** | Adversarial refinement | Best ideas survive scrutiny |

</div>

<br/>

---

<div align="center">

## ⚡ 60-SECOND SETUP

</div>

```bash
# 1️⃣ Install the plugin
/plugin install quantsquirrel/claude-synod-debate

# 2️⃣ Set your API keys (one-time)
export GEMINI_API_KEY="your-gemini-key"
export OPENAI_API_KEY="your-openai-key"

# 3️⃣ Run setup (installs deps, configures CLI tools, tests models)
/synod-setup

# 4️⃣ Summon the council
/synod review Is this authentication flow secure?
```

<div align="center">

**That's it.** The council convenes automatically.

<br/>

<img src="https://capsule-render.vercel.app/api?type=rect&color=gradient&customColorList=12,14,25&height=2" width="50%"/>

</div>

<br/>

---

<div align="center">

## 🔧 INITIAL SETUP TEST

*Verify your models work before deliberating*

</div>

<br/>

```bash
/synod-setup
```

<div align="center">

| Check | What It Does |
|:-----:|:-------------|
| **CLI** | Verifies all 7 provider CLIs exist |
| **API Keys** | Checks all provider API keys |
| **Response Time** | Tests each model with 120s timeout |
| **Classification** | Labels models: ✓ Recommended / ✓ Usable / ⚠ Slow / ✗ Failed |

</div>

<br/>

<details>
<summary><b>📋 Sample Output</b></summary>

<br/>

```
[Synod Setup] 초기 설정을 시작합니다...

Step 1/3: CLI 도구 확인
  ✓ gemini-3.py
  ✓ openai-cli.py

Step 2/3: API 키 확인
  ✓ GOOGLE_API_KEY (설정됨)
  ✓ OPENAI_API_KEY (설정됨)

Step 3/3: 모델 응답 시간 측정 (타임아웃: 120초)

Provider    Model              Latency    Status
───────────────────────────────────────────────
gemini      flash              3.2초      ✓ 권장
gemini      pro                12.4초     ✓ 사용 가능
openai      gpt4o              2.8초      ✓ 권장
openai      o3                 45.2초     ⚠ 느림

[완료] 4/4 모델 사용 가능
Synod를 사용할 준비가 되었습니다!
```

</details>

<br/>

---

<div align="center">

## 🤖 SUPPORTED PROVIDERS

*v3.0: Now supporting 7 AI providers*

</div>

<br/>

<div align="center">

| Provider | CLI | Best For | Status |
|:--------:|:---:|:---------|:------:|
| 🔵 **Gemini** | `gemini-3` | Default debater, thinking modes | Required |
| 🟢 **OpenAI** | `openai-cli` | Default debater, o3 reasoning | Required |
| 🟣 **DeepSeek** | `deepseek-cli` | Math, reasoning (R1) | Optional |
| ⚡ **Groq** | `groq-cli` | Ultra-fast inference (LPU) | Optional |
| 🌐 **OpenRouter** | `openrouter-cli` | Multi-model fallback | Recommended |
| 🔶 **Grok** | `grok-cli` | 2M context window | Opt-in |
| 🟠 **Mistral** | `mistral-cli` | Code, European deployment | Opt-in |

</div>

<br/>

<details>
<summary><b>🔑 Extended Provider Setup</b></summary>

<br/>

```bash
# Optional: Add more providers to your council
export DEEPSEEK_API_KEY="your-deepseek-key"   # DeepSeek R1
export GROQ_API_KEY="your-groq-key"           # Groq LPU
export OPENROUTER_API_KEY="your-openrouter-key" # OpenRouter (Recommended)

# Opt-in Providers (requires explicit activation)
# Grok (2M context window)
export SYNOD_ENABLE_GROK=1
export XAI_API_KEY="your-xai-key"

# Mistral (code specialization)
export SYNOD_ENABLE_MISTRAL=1
export MISTRAL_API_KEY="your-mistral-key"
```

</details>

<br/>

---

<div align="center">

## 🎯 FIVE MODES OF DELIBERATION

*Choose your council configuration*

</div>

<br/>

<div align="center">

| | Mode | Summon When... | Configuration |
|:---:|:---:|:---------------|:--------------|
| 🔍 | **`review`** | Analyzing code, security, PRs | `Gemini Flash` ⚔️ `GPT-4o` |
| 🏗️ | **`design`** | Architecting systems | `Gemini Pro` ⚔️ `GPT-4o` |
| 🐛 | **`debug`** | Hunting elusive bugs | `Gemini Flash` ⚔️ `GPT-4o` |
| 💡 | **`idea`** | Brainstorming solutions | `Gemini Pro` ⚔️ `GPT-4o` |
| 🌐 | **`general`** | Everything else | `Gemini Flash` ⚔️ `GPT-4o` |

</div>

<br/>

<details>
<summary><b>📝 Example Commands</b></summary>

<br/>

```bash
# Code review
/synod review "Is this recursive function O(n) or O(n²)?"

# System design
/synod design "Design a rate limiter for 10M requests/day"

# Debugging
/synod debug "Why does this only fail on Tuesdays?"

# Brainstorming
/synod idea "How do we reduce checkout abandonment?"
```

</details>

<br/>

---

<div align="center">

## 📜 ACADEMIC FOUNDATION

*Not just another wrapper — peer-reviewed deliberation protocols*

</div>

<br/>

<div align="center">

| Protocol | Source | What Synod Implements |
|:--------:|:-------|:----------------------|
| **ReConcile** | [ACL 2024](https://arxiv.org/abs/2309.13007) | 3-round convergence (>95% quality gains) |
| **AgentsCourt** | [arXiv 2024](https://arxiv.org/abs/2408.08089) | Judge/Defense/Prosecutor structure |
| **ConfMAD** | [arXiv 2025](https://arxiv.org/abs/2502.06233) | Confidence-aware soft defer |
| **Free-MAD** | Research | Anti-conformity instructions |
| **SID** | Research | Self-signals driven confidence |

</div>

<br/>

<details>
<summary><b>📊 The Trust Equation</b></summary>

<br/>

Synod calculates trust using the **CortexDebate** formula:

```
                Credibility × Reliability × Intimacy
Trust Score = ────────────────────────────────────────
                      Self-Orientation
```

| Factor | Measures | Range |
|:------:|:---------|:-----:|
| **C** | Evidence quality | 0–1 |
| **R** | Logical consistency | 0–1 |
| **I** | Problem relevance | 0–1 |
| **S** | Bias level (lower = better) | 0.1–1 |

**Interpretation:**
- `T ≥ 1.5` → Primary source (high trust)
- `T ≥ 1.0` → Reliable input
- `T ≥ 0.5` → Consider with caution
- `T < 0.5` → Excluded from synthesis

</details>

<br/>

---

<div align="center">

## 📦 INSTALLATION

</div>

<details>
<summary><b>🚀 Plugin Installation (Recommended)</b></summary>

<br/>

```bash
# Install plugin
/plugin install quantsquirrel/claude-synod-debate

# Set API keys
export GEMINI_API_KEY="your-gemini-key"
export OPENAI_API_KEY="your-openai-key"

# Run setup (auto-installs Python deps, creates CLI wrappers, tests models)
/synod-setup
```

`/synod-setup` handles everything: Python dependencies (`google-genai`, `openai`, `httpx`), CLI tool wrappers in `~/.synod/bin/`, API key validation, and model connectivity testing.

</details>

<details>
<summary><b>🔧 Manual Installation</b></summary>

<br/>

```bash
git clone https://github.com/quantsquirrel/claude-synod-debate.git
cd claude-synod-debate
pip install google-genai openai httpx
cp skills/*.md ~/.claude/commands/

# Run setup to create CLI wrappers and test models
python3 tools/synod-setup.py
```

</details>

<details>
<summary><b>⚙️ Configuration</b></summary>

<br/>

```bash
# Required
export GEMINI_API_KEY="your-gemini-key"
export OPENAI_API_KEY="your-openai-key"

# Optional
export SYNOD_SESSION_DIR="~/.synod/sessions"
export SYNOD_RETENTION_DAYS=30
```

</details>

<br/>

---

<div align="center">

## 🗺️ ROADMAP

</div>

- [ ] **MCP Server** — Native Claude Code integration
- [ ] **VS Code Extension** — GUI for debate visualization
- [ ] **Knowledge Base** — Learning from debate history
- [ ] **Web Dashboard** — Real-time debate monitoring
- [x] **More LLMs** — ~~Llama, Mistral, Claude variants~~ **v3.0: 7 providers supported!**

<br/>

---

<div align="center">

## 🤝 JOIN THE COUNCIL

**[Issues](https://github.com/quantsquirrel/claude-synod-debate/issues)** · **[Discussions](https://github.com/quantsquirrel/claude-synod-debate/discussions)** · **[Contributing](CONTRIBUTING.md)**

<br/>

<details>
<summary><b>📖 Citation</b></summary>

```bibtex
@software{synod2026,
  title   = {Synod: Multi-Agent Deliberation for Claude Code},
  author  = {quantsquirrel},
  year    = {2026},
  url     = {https://github.com/quantsquirrel/claude-synod-debate}
}
```

</details>

<br/>

**MIT License** · Copyright © 2026 quantsquirrel

*Built on the shoulders of*<br/>
**ReConcile** · **AgentsCourt** · **ConfMAD** · **Free-MAD** · **SID**

<br/>

> *"In the multitude of counselors there is safety."* — Proverbs 11:14

</div>
