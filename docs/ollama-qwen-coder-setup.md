# Tutorial: Setting Up & Running Qwen2.5-Coder with Ollama on Linux

This guide provides step-by-step instructions to install **Ollama** on Linux (Fedora, Ubuntu, Debian, Arch, RHEL), download and run **Qwen2.5-Coder 7B**, and start chatting with your local coding AI immediately.

---

## Quick Reference Commands

```bash
# 1. Install Ollama on Linux
curl -fsSL https://ollama.com/install.sh | sh

# 2. Download and launch Qwen2.5-Coder 7B
ollama run qwen2.5-coder:7b

# 3. Quick one-shot prompt from terminal
ollama run qwen2.5-coder:7b "Write a Python script to fetch data from an API and save it to CSV."
```

---

## Prerequisites

* **OS**: Any modern Linux distribution (Fedora, Ubuntu, Debian, Arch, RHEL).
* **RAM/VRAM**:
  * **Qwen2.5-Coder 7B**: Requires ~5 GB of RAM/VRAM. Runs on 8GB+ system RAM or any GPU with at least 6GB VRAM.
  * **Qwen2.5-Coder 14B**: Requires ~10 GB of RAM/VRAM. Recommended if you have 16GB VRAM or 32GB system RAM.
* **Acceleration (Optional but recommended)**:
  * **NVIDIA GPU**: CUDA drivers installed.
  * **AMD GPU**: ROCm drivers installed (supported natively on Linux).

---

## Step 1: Install Ollama on Linux

Open your Linux terminal and execute the official automated setup script:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### Manage the Ollama Systemd Service

Ollama automatically runs as a background service (`ollama.service`). You can check or control it with:

```bash
# Check service status
sudo systemctl status ollama

# Start service (if stopped)
sudo systemctl start ollama

# Enable on system boot
sudo systemctl enable ollama
```

---

## Step 2: Download & Run Qwen2.5-Coder 7B

To download the model weights and immediately start an interactive chat session, run:

```bash
ollama run qwen2.5-coder:7b
```

> **Tip:** If you have 16GB VRAM or 32GB RAM and want higher coding performance, run the 14B variant instead:
> ```bash
> ollama run qwen2.5-coder:14b
> ```

---

## Step 3: Chatting with the AI in Terminal

### Interactive Mode
Once the prompt `>>>` appears in your terminal, you can ask questions or prompt for code directly:

```text
>>> Write a Python function using asyncio to download multiple URLs concurrently.
```

### Essential Chat Commands Inside Ollama
While inside the `>>>` interactive session:

| Command | Action |
| :--- | :--- |
| `/help` | Show available interactive commands |
| `/clear` | Clear conversation context |
| `/set system "..."` | Modify the system prompt (e.g. `/set system "You are an expert Rust developer."`) |
| `"""` | Multi-line input mode (type `"""` at start and end of multi-line prompts) |
| `/bye` or `Ctrl+D` | Exit the chat session |

### One-Shot Shell Commands (CLI Integration)
You can pipe text or pass prompts directly from your shell without opening interactive mode:

```bash
# Ask a direct question
ollama run qwen2.5-coder:7b "Explain how Python decorators work with an example."

# Pipe file content into the model for review/refactoring
cat main.py | ollama run qwen2.5-coder:7b "Find any bugs or performance issues in this code."
```

---

## Step 4: IDE & API Integration

### 1. VS Code / VSCodium Integration (Continue.dev)
1. Install the **Continue** extension in VS Code.
2. Open `~/.continue/config.json` (or click settings in Continue sidebar).
3. Add Ollama as your provider:

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

### 2. Python API / REST Endpoint
Ollama exposes an OpenAI-compatible REST API locally at `http://localhost:11434`.

```python
import urllib.request
import json

url = "http://localhost:11434/api/generate"
data = {
    "model": "qwen2.5-coder:7b",
    "prompt": "Write a hello world function in Go.",
    "stream": False
}

req = urllib.request.Request(url, data=json.dumps(data).encode(), headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(req) as response:
    result = json.loads(response.read().decode())
    print(result['response'])
```

---

## Step 5: Ollama Cheat Sheet

| Command | Description |
| :--- | :--- |
| `ollama list` | List all downloaded models on your machine |
| `ollama ps` | List currently active/running models in VRAM/RAM |
| `ollama show qwen2.5-coder:7b` | Show details, system prompt, and parameters of a model |
| `ollama stop qwen2.5-coder:7b` | Unload the model from VRAM/RAM |
| `ollama rm qwen2.5-coder:7b` | Remove the model from disk |

---

## Troubleshooting & Tips for Linux Users

* **AMD GPU Hardware Acceleration (ROCm)**:
  If Ollama does not automatically utilize your AMD GPU, set the ROCm environment variable:
  ```bash
  echo 'export HSA_OVERRIDE_GFX_VERSION=10.3.0' >> ~/.bashrc
  source ~/.bashrc
  ```
* **VRAM Monitoring**:
  * NVIDIA: `nvidia-smi`
  * AMD: `rocm-smi` or `radeontop`
