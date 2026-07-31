---
status: rationale
retrieval: excluded
updated: 2026-07-29
---
# **Ollama & Qwen2.5-Coder Setup Guide for Linux**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

This guide sets up the reference **Tier 4 (Local)** environment named in
[Model Tiering](../05-tech-stack/llm-providers-and-economics.md#2-model-tiering) — Ollama plus
Qwen2.5-Coder, for offline and air-gapped operation at zero marginal cost. It installs **Ollama** on
Linux (Fedora, Ubuntu, Debian, Arch, RHEL), pulls **Qwen2.5-Coder**, and verifies a chat session before
wiring it into `config.toml`.

---

## ⚡ **Quick Reference Commands**

```bash
# 1. Install Ollama on Linux
curl -fsSL https://ollama.com/install.sh | sh

# 2. Download and run Qwen2.5-Coder 7B interactively
ollama run qwen2.5-coder:7b

# 3. Quick one-shot prompt from terminal
ollama run qwen2.5-coder:7b "Write a Python script to fetch JSON data from an API."
```

---

## 📋 **Prerequisites**

* **OS**: Linux (Fedora, Ubuntu, Debian, Arch, RHEL).
* **RAM / VRAM**:
  * **Qwen2.5-Coder 7B**: Requires ~5 GB RAM/VRAM. Runs smoothly on 8GB+ RAM or GPUs with 6GB+ VRAM.
  * **Qwen2.5-Coder 14B**: Requires ~10 GB RAM/VRAM. Recommended for 16GB VRAM GPUs or 32GB system RAM.
* **Hardware Acceleration**:
  * **NVIDIA GPU**: CUDA drivers installed.
  * **AMD GPU**: ROCm drivers installed (supported natively by Ollama on Linux).

---

## 🚀 **Step 1: Install Ollama on Linux**

Run the official Linux installation script:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### **Manage Systemd Service**
Ollama runs in the background as a systemd service (`ollama.service`).

```bash
# Check service status
sudo systemctl status ollama

# Start service (if stopped)
sudo systemctl start ollama

# Enable on system boot
sudo systemctl enable ollama
```

---

## 📦 **Step 2: Download & Launch Qwen2.5-Coder 7B**

Run the following command to download model weights and open an interactive chat session:

```bash
ollama run qwen2.5-coder:7b
```

> [!TIP]
> If your system has **16GB VRAM** or **32GB RAM**, you can run the higher-intelligence 14B version:
> ```bash
> ollama run qwen2.5-coder:14b
> ```

---

## 💬 **Step 3: Chatting with the AI in Terminal**

### **Interactive Mode**
Type your prompt directly when the `>>>` prompt appears:

```text
>>> Write a Python function using asyncio to process tasks concurrently.
```

### **Useful Interactive Commands**

| Command | Action |
| :--- | :--- |
| `/help` | Show interactive help and command menu |
| `/clear` | Clear active conversation context |
| `/set system "..."` | Customize system prompt (e.g., `/set system "You are a Rust expert."`) |
| `"""` | Enter multi-line input mode |
| `/bye` or `Ctrl+D` | Exit chat session |

### **One-Shot Terminal Commands (CLI Pipe Integration)**

```bash
# Ask a direct question
ollama run qwen2.5-coder:7b "Explain Python context managers with an example."

# Pipe code into model for code review
cat main.py | ollama run qwen2.5-coder:7b "Audit this Python code for bugs and security issues."
```

---

## 🔌 **Step 4: IDE & API Integration**

### **1. VS Code / VSCodium (via Continue.dev)**
1. Install the **Continue** extension in VS Code.
2. Open `~/.continue/config.json`.
3. Add Ollama configuration:

```json
{
  "models": [
    {
      "title": "Qwen 2.5 Coder 7B (Local)",
      "provider": "ollama",
      "model": "qwen2.5-coder:7b"
    }
  ],
  "tabAutocompleteModel": {
    "title": "Qwen 2.5 Coder 1.5B (Fast)",
    "provider": "ollama",
    "model": "qwen2.5-coder:1.5b"
  }
}
```

### **2. Local REST API Endpoint**
Ollama exposes a REST API at `http://localhost:11434`.

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "qwen2.5-coder:7b",
  "prompt": "Write a Hello World program in C++",
  "stream": false
}'
```

---

## 🛠️ **Step 5: Ollama Management Cheat Sheet**

| Command | Description |
| :--- | :--- |
| `ollama list` | List all downloaded models on your machine |
| `ollama ps` | Show currently active models loaded in VRAM/RAM |
| `ollama show qwen2.5-coder:7b` | Show parameters, template, and system prompt |
| `ollama stop qwen2.5-coder:7b` | Unload model from VRAM/RAM memory |
| `ollama rm qwen2.5-coder:7b` | Delete model weights from disk |

---

## 🔍 **Troubleshooting (AMD / NVIDIA Linux)**

* **AMD ROCm Override (if GPU is not automatically detected)**:
  ```bash
  echo 'export HSA_OVERRIDE_GFX_VERSION=10.3.0' >> ~/.bashrc
  source ~/.bashrc
  ```
* **Check Memory Consumption**:
  * NVIDIA: `nvidia-smi`
  * AMD: `rocm-smi` or `radeontop`

---

## 🔗 **Wiring Into SAGIHA**

Once `ollama run qwen2.5-coder:7b` answers, bind it as the `local` tier in `config.toml`
([Configuration Reference](../05-tech-stack/configuration-reference.md)) — no other file changes,
since routing is [composition, not a port method](../05-tech-stack/llm-providers-and-economics.md#roles-bind-tiers-to-call-sites):

```toml
[model.tiers.local]
provider = "openai-compatible"   # Ollama speaks the OpenAI-compatible API
model    = "qwen2.5-coder:7b"
base_url = "http://localhost:11434/v1"
max_tokens = 8192
```

Point any role at it directly (`[model.roles] execution = "local"`), or bind it as `fallback` so the
harness degrades to local inference when the primary tier's breaker opens
([Error Taxonomy](../03-contracts-and-models/error-taxonomy.md)). For a fully air-gapped run, point
every role in `[model.roles]` at `local` — no other config changes, since role resolution is a lookup,
not a code path.

Read [Local GPU Target](../05-tech-stack/llm-providers-and-economics.md#3-local-gpu-target-16gb-vram)
before treating this as a drop-in replacement for a frontier tier: zero marginal cost is not zero
cost, and slower inference lengthens every DMARTIC cycle even as it lowers dollars-per-task.
