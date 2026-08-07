# DeepSeek (Reasonix) & Kimi Code CLI — Complete Installation, Configuration & Best Practices Guide

This tutorial provides step-by-step instructions for installing, configuring, and deploying **Reasonix** (optimized for DeepSeek v4/R1) and **Kimi Code CLI** (optimized for Moonshot Kimi K3) to build software applications autonomously from the terminal.

---

## 📋 Table of Contents

1. [Overview & Architectural Strengths](#1-overview--architectural-strengths)
2. [DeepSeek CLI — Reasonix Setup & Usage](#2-deepseek-cli--reasonix-setup--usage)
   - [Prerequisites & Installation](#21-prerequisites--installation)
   - [API Key & Environment Configuration](#22-api-key--environment-configuration)
   - [Command Options & App Creation Workflow](#23-command-options--app-creation-workflow)
3. [Moonshot AI — Kimi Code CLI Setup & Usage](#3-moonshot-ai--kimi-code-cli-setup--usage)
   - [Prerequisites & Installation](#31-prerequisites--installation-1)
   - [API Key & Environment Configuration](#32-api-key--environment-configuration-1)
   - [Command Options & Thinking Mode Controls](#33-command-options--thinking-mode-controls)
4. [Best Practices for Autonomous App Development](#4-best-practices-for-autonomous-app-development)
   - [Maximizing DeepSeek Prompt Caching](#41-maximizing-deepseek-prompt-caching)
   - [Leveraging Kimi's `preserve_thinking` Mode](#42-leveraging-kimis-preserve_thinking-mode)
   - [Structured Prompting & Iterative Execution](#43-structured-prompting--iterative-execution)
5. [Quick Reference Summary](#5-quick-reference-summary)

---

## 1. Overview & Architectural Strengths

| CLI Tool | Target Model Family | Core Strength | Key Feature |
| :--- | :--- | :--- | :--- |
| **Reasonix** | DeepSeek v4 / R1 | Prompt Cache Optimization & Low Token Latency | Static prefix layer caching, auto tool-repair loop |
| **Kimi Code CLI** | Moonshot Kimi K3 / K2.7 | Multi-Turn Reasoning & Ultra-Long Context | `preserve_thinking` mode, MCP tool support |

---

## 2. DeepSeek CLI — Reasonix Setup & Usage

**Reasonix** is a cache-first, terminal-native AI coding agent built specifically for the DeepSeek API architecture. It optimizes prompt prefix stability to achieve maximum prompt cache hit rates ($>90\%$).

### 2.1 Prerequisites & Installation

Reasonix requires **Node.js (>= 18.0.0)** or **npx**.

```bash
# Option A: Run directly via npx (no global install required)
npx reasonix code --help

# Option B: Global installation via npm or pnpm
npm install -g reasonix
# or
pnpm add -g reasonix
```

Verify the installation:
```bash
reasonix --version
```

### 2.2 API Key & Environment Configuration

Export your DeepSeek API key in your terminal shell or add it to your `.env` / shell profile (`~/.bashrc` or `~/.zshrc`):

#### On Linux / macOS:
```bash
export DEEPSEEK_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export DEEPSEEK_BASE_URL="https://api.deepseek.com/v1"  # Default API endpoint
```

#### On Windows (PowerShell):
```powershell
$env:DEEPSEEK_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
$env:DEEPSEEK_BASE_URL="https://api.deepseek.com/v1"
```

#### Configuration File (`~/.config/reasonix/config.json`):
You can also create a persistent config file:
```json
{
  "apiKey": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "baseURL": "https://api.deepseek.com/v1",
  "model": "deepseek-coder",
  "temperature": 0.2,
  "cacheOptimized": true,
  "autoApprove": false
}
```

### 2.3 Command Options & App Creation Workflow

#### Starting an Interactive Coding Session:
```bash
# Launch interactive terminal session in your project root
reasonix code
```

#### Generating a New Application from Scratch:
```bash
reasonix create --template react-ts --name my-app "Create a sleek dark-mode task dashboard with drag-and-drop support"
```

#### Executing a Specific Task Non-Interactively:
```bash
reasonix run "Refactor src/services/api.ts to add retry logic with exponential backoff and unit tests"
```

---

## 3. Moonshot AI — Kimi Code CLI Setup & Usage

**Kimi Code CLI** (`MoonshotAI/kimi-cli`) is Moonshot AI’s official terminal harness designed to maximize Kimi K3’s ultra-long context window and deep multi-turn reasoning capabilities.

### 3.1 Prerequisites & Installation

Kimi Code CLI requires **Python (>= 3.10)** and `pip` or `uv`.

```bash
# Option A: Install via pip
pip install kimi-cli

# Option B: Install via uv (Recommended for speed)
uv tool install kimi-cli

# Option C: Clone and install from repository
git clone https://github.com/MoonshotAI/kimi-cli.git
cd kimi-cli
pip install -e .
```

Verify installation:
```bash
kimi --version
```

### 3.2 API Key & Environment Configuration

Set your Moonshot AI API key:

#### On Linux / macOS:
```bash
export MOONSHOT_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export MOONSHOT_BASE_URL="https://api.moonshot.cn/v1"
```

#### On Windows (PowerShell):
```powershell
$env:MOONSHOT_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
$env:MOONSHOT_BASE_URL="https://api.moonshot.cn/v1"
```

#### Configuration File (`~/.kimi/config.toml`):
```toml
[default]
api_key = "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
base_url = "https://api.moonshot.cn/v1"
model = "kimi-k3-code"
temperature = 0.3
preserve_thinking = true
thinking_budget = 4096

[mcp]
enabled = true
```

### 3.3 Command Options & Thinking Mode Controls

#### Launching Interactive Kimi Shell with Thinking Mode:
```bash
kimi --model kimi-k3-code --thinking
```

#### Running a Multi-File Code Review & Repair:
```bash
kimi run --path ./src "Inspect all AST parsing models, run pytest, and repair failing unit tests"
```

#### Running with MCP Tools Enabled:
```bash
kimi run --mcp-config ./mcp.json "Scan PostgreSQL schema and generate Pydantic domain models"
```

---

## 4. Best Practices for Autonomous App Development

### 4.1 Maximizing DeepSeek Prompt Caching
* **Maintain Static System Prefixes**: Keep your project instructions and system rules unchanged across commands. DeepSeek caches identical prefix tokens automatically, reducing response latency by up to **80%**.
* **Batch Small Changes**: Instead of making dozens of tiny 1-line edits, ask Reasonix to implement complete modules or components in single turns.

### 4.2 Leveraging Kimi's `preserve_thinking` Mode
* **Enable `--thinking` for Complex Tasks**: When building complex algorithms, AST parsers, or multi-file refactors, enable `preserve_thinking = true`. This preserves Kimi K3's internal reasoning trace across turns.
* **Feed Complete File Trees**: Kimi handles long context windows natively. Pass entire module directory structures (`--path ./src`) so Kimi understands global cross-file dependencies.

### 4.3 Structured Prompting & Iterative Execution

Follow this **4-Step Execution Strategy** when using CLI agents:

```
+-------------------+     +-------------------+     +-------------------+     +-------------------+
| 1. PLAN FIRST     | --> | 2. GENERATE CODE  | --> | 3. TEST & VERIFY  | --> | 4. REPAIR LOOP    |
| Ask CLI agent for |     | Instruct agent to |     | Execute build or  |     | Pass error logs   |
| step-by-step plan |     | write files       |     | test suite        |     | for auto-repair   |
+-------------------+     +-------------------+     +-------------------+     +-------------------+
```

1. **Plan First**: Prompt the CLI agent to output an execution plan before modifying any files (`reasonix code --plan-only`).
2. **Atomic Commits**: Run `git commit` between major feature steps so you can roll back easily if an agent loop diverges.
3. **Log-Driven Debugging**: Never ask the model to guess why a build failed. Feed exact error stack traces directly into the CLI prompt:
   ```bash
   kimi run "Fix the following test failure traceback: $(pytest tests/unit/)"
   ```

---

## 5. Quick Reference Summary

| Task | Reasonix (DeepSeek) Command | Kimi Code CLI Command |
| :--- | :--- | :--- |
| **Interactive Session** | `reasonix code` | `kimi` |
| **With Reasoning Mode** | `reasonix code --reasoning` | `kimi --thinking` |
| **Single Task Execution** | `reasonix run "task description"` | `kimi run "task description"` |
| **Target Directory** | `reasonix code --cwd ./src` | `kimi --path ./src` |
| **Config Location** | `~/.config/reasonix/config.json` | `~/.kimi/config.toml` |
