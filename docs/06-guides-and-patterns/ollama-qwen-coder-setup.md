---
status: rationale
updated: 2026-07-29
retrieval: excluded
---
# **Ollama & Qwen2.5-Coder Setup Guide for Linux**

> [!NOTE]
> **Working Proposal Disclaimer**: A working architectural proposal, refined iteratively as practical evaluation progresses.

Sets up Tier 4 (Local) inference per [Model Tiering](../05-tech-stack/llm-providers-and-economics.md#2-model-tiering) using Ollama and Qwen2.5-Coder for offline, zero-marginal-cost operation.

## ⚡ **Quick Reference**

```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Launch Qwen2.5-Coder 7B interactively
ollama run qwen2.5-coder:7b

# 3. One-shot execution
ollama run qwen2.5-coder:7b "Write a Python script to fetch JSON from an API."
```

## 📋 **Prerequisites**

* **OS**: Linux (Fedora, Ubuntu, Debian, Arch, RHEL).
* **RAM / VRAM Requirements**:
  * **Qwen2.5-Coder 7B**: ~5 GB RAM/VRAM (runs on 8GB+ RAM or 6GB+ VRAM).
  * **Qwen2.5-Coder 14B**: ~10 GB RAM/VRAM (requires 16GB VRAM GPU or 32GB RAM).
* **Hardware Acceleration**: NVIDIA (CUDA) or AMD (ROCm).

## 🚀 **Installation & Service Management**

```bash
# Install
curl -fsSL https://ollama.com/install.sh | sh

# Systemd Service Controls
sudo systemctl status ollama
sudo systemctl start ollama
sudo systemctl enable ollama
```

## 📦 **Model Execution**

```bash
# 7B Model (Default)
ollama run qwen2.5-coder:7b

# 14B Model (Higher intelligence, requires 16GB VRAM / 32GB RAM)
ollama run qwen2.5-coder:14b
```

### **Interactive Session Controls**

| Command | Action |
| :--- | :--- |
| `/help` | Show interactive help menu |
| `/clear` | Clear conversation context |
| `/set system "..."` | Override system prompt |
| `"""` | Enter multi-line input mode |
| `/bye` or `Ctrl+D` | Exit chat session |

### **CLI Pipeline & Pipe Integration**

```bash
# Direct prompt query
ollama run qwen2.5-coder:7b "Explain Python context managers with an example."

# Pipe code into model for auditing
cat main.py | ollama run qwen2.5-coder:7b "Audit this Python code for bugs and security issues."
```

## 🔌 **IDE & API Integration**

### **VS Code / VSCodium (`~/.continue/config.json`)**

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

### **REST API Endpoint (`http://localhost:11434`)**

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "qwen2.5-coder:7b",
  "prompt": "Write a Hello World program in C++",
  "stream": false
}'
```

## 🛠️ **Management Commands**

| Command | Description |
| :--- | :--- |
| `ollama list` | List downloaded models |
| `ollama ps` | Show currently loaded active models |
| `ollama show qwen2.5-coder:7b` | Inspect model configuration, parameters, and system prompt |
| `ollama stop qwen2.5-coder:7b` | Unload model from VRAM/RAM |
| `ollama rm qwen2.5-coder:7b` | Delete model from disk |

## 🔍 **Troubleshooting**

* **AMD ROCm Override**: If GPU is unrecognized, set `export HSA_OVERRIDE_GFX_VERSION=10.3.0` in `~/.bashrc`.
* **VRAM Monitoring**: `nvidia-smi` (NVIDIA) or `rocm-smi` / `radeontop` (AMD).

## 🔗 **SAGIHA Integration**

Configure in `config.toml` (see [Configuration Reference](../05-tech-stack/configuration-reference.md) and [Roles Bind Tiers](../05-tech-stack/llm-providers-and-economics.md#roles-bind-tiers-to-call-sites)):

```toml
[model.tiers.local]
provider   = "openai-compatible"
model      = "qwen2.5-coder:7b"
base_url   = "http://localhost:11434/v1"
max_tokens = 8192
```

Assign `[model.roles] execution = "local"` or set `local` as fallback during circuit-breaker trips ([Error Taxonomy](../03-contracts-and-models/error-taxonomy.md)). Note performance tradeoffs discussed in [Local GPU Target](../05-tech-stack/llm-providers-and-economics.md#3-local-gpu-target-16gb-vram).
