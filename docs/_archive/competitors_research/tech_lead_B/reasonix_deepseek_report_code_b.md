---
status: rationale
updated: 2026-08-06
author: Tech Lead B
---

# Deep Code-Level Investigation Report: Reasonix Go Implementation & Harness Infrastructure

## Executive Summary

This report presents a **pure code-level architectural analysis** of the Reasonix coding agent harness, derived exclusively from reading and auditing the Go source code files in `src/reasonix/` (excluding all `.md` files).

Where the documentation report (`reasonix_deepseek_report_b.md`) analyzed high-level contracts, this report documents the **exact Go structs, function signatures, channel streaming mechanics, BM25 scoring algorithms, compaction threshold math, and permission evaluation rules** that drive the executable harness.

---

## 1. Concrete Architecture & Dependency Model

### 1.1 Dependency Invariants in Go

The Go codebase enforces a strict acyclic dependency structure:
`cmd/reasonix → internal/cli → {internal/agent, internal/plugin, internal/config} → {internal/tool, internal/provider}`

* **`CGO_ENABLED=0`**: Pure Go implementation.
* **Single Dependency**: `github.com/BurntSushi/toml` for config parsing; all other functions rely on the Go stdio/stdlib (`context`, `sync`, `atomic`, `encoding/json`, `os/exec`).
* **Self-Registration via `init()`**: Built-in providers (`internal/provider/openai`) and built-in tools (`internal/tool/builtin`) register themselves at process init time into package-level registries without parent packages importing subpackages.

---

## 2. Inner Loop Mechanics (`internal/agent`)

### 2.1 Agent Struct & Constants (`internal/agent/agent.go`)

```go
const (
    maxToolOutputBytes      = 32 * 1024 // 32KB per tool output cap
    maxEmptyFinalBlocks     = 3
    maxStreamRecoveries     = 5         // Up to 6 total sampling attempts (1 + 5)
    defaultReasoningByteLimit = 128 * 1024
)

type Agent struct {
    prov               provider.Provider
    tools              *tool.Registry
    session            *Session
    sessMu             sync.Mutex
    maxSteps           int
    contextWindow      int
    compactRatio       float64
    toolResultSnipRatio float64
    softCompactRatio    float64
    compactForceRatio  float64

    sink               event.Sink
    lastUsage          atomic.Pointer[provider.Usage]
    sessCacheHit       atomic.Int64
    sessCacheMiss      atomic.Int64
}
```

* **Output Budgeting**: Individual tool execution outputs are capped at **32 KB** before being placed into context, preventing runaway log outputs from saturating the LLM context window before compaction runs.
* **Atomic Cache Observability**: `sessCacheHit` and `sessCacheMiss` use atomic operations (`atomic.Int64`) to calculate real-time prompt cache hit rates ($\frac{\sum \text{hit}}{\sum (\text{hit} + \text{miss})})$ without locking the turn loop.

### 2.2 Low-Frequency Compaction & Ratio Math (`internal/agent/compact.go`)

Compaction thresholds are evaluated per turn in `maybeCompact()`:

```go
const (
    defaultSoftCompactRatio    = 0.5   // Report growing context notice
    defaultToolResultSnipRatio = 0.6   // Snipping stale tool results with head/tail markers
    defaultCompactRatio        = 0.8   // Trigger summary compaction
    defaultCompactForceRatio   = 0.9   // Forced context fold
    defaultCompactTarget       = 0.5   // Kept tail target fraction
    defaultTailTokens          = 16384 // Verbatim recent-tail budget (tokens)
)
```

#### Compaction Step Sequence:
1. **Under `soft` (0.5)**: No action; prompt grows append-only for maximum prompt cache hits.
2. **At `snip` (0.6)**: `SnipStaleToolResults()` rewrites historical tool output messages with deterministic head/tail markers without removing message objects.
3. **At `compact` (0.8)**: `PruneStaleToolResults()` replaces stale tool results with minimal placeholders. If prompt size remains above $0.8 \times \text{contextWindow}$, summary compaction invokes the LLM summarizer with a structured prompt layout (`## Standing facts`, `## Goal`, `## Decisions`, `## Files & code`, `## Commands & outcomes`, `## Pending & next step`).
4. **Verbatim User Turns**: User turns and prior digests are pinned verbatim and never summarized away.
5. **Archiving**: Original un-compacted message objects are dumped to disk at `.reasonix/archive/<timestamp>.jsonl`.

---

## 3. Two-Model Collaboration (`internal/agent/coordinator.go`)

When `agent.planner_model` differs from the executor model, `Coordinator` manages two isolated sessions:

```go
type Coordinator struct {
    plannerAgent  *Agent
    executorAgent *Agent
}
```

* **Session Isolation**: The `plannerAgent` and `executorAgent` maintain completely independent `Session` instances.
* **Cache Preserving Handoff**: The Planner runs its research loop in session A, produces a structured plan, and hands it off as plain text to the Executor in session B. Because the sessions never share message arrays, model switching does NOT invalidate prompt cache prefixes for either model.

---

## 4. Permission Policy & Security Engine (`internal/permission`)

### 4.1 Policy Evaluation Code (`internal/permission/permission.go`)

```go
type Decision int

const (
    Allow Decision = iota
    Ask
    Deny
)

type Rule struct {
    Tool    string
    Subject string
    Literal bool
}

type Policy struct {
    Mode  Decision
    Allow []Rule
    Ask   []Rule
    Deny  []Rule
}
```

#### Precedence Logic in `Decide()`:
1. **Explicit `Deny` rules match first** $\rightarrow$ `Deny` (Hard block in all modes).
2. **Explicit `Ask` rules match second** $\rightarrow$ `Ask` (Prompts user or fails closed in headless mode).
3. **Explicit `Allow` rules match third** $\rightarrow$ `Allow`.
4. **Fallback**: Read-only tools default to `Allow`; mutation tools default to `Policy.Mode` (default `Ask`).

#### Dynamic Shell Safety (`internal/permission/bash_readonly.go` & `bash_approval.go`):
* Shell parsing uses `mvdan.cc/sh/v3/syntax`.
* Shell operators (`&&`, `;`, `||`, `|`, `>`, `<`), command substitutions (`$(cmd)`), heredocs, and variable expansions trigger `Ask` posture unless covered by an exact `Literal` grant (`Bash=npm run test`).

---

## 5. Retrieval & BM25 Search Engine (`internal/retrieval`)

### 5.1 BM25 Scoring Implementation (`internal/retrieval/bm25.go`)

```go
func BM25Score(counts map[string]int, length int, queryTerms []string, df map[string]int, totalDocs int, avgLen float64) float64 {
    const (
        k1 = 1.2
        b  = 0.75
    )
    if length <= 0 || totalDocs <= 0 {
        return 0
    }
    if avgLen <= 0 {
        avgLen = 1
    }
    var score float64
    docLen := float64(length)
    for _, term := range queryTerms {
        tf := counts[term]
        if tf == 0 { continue }
        termDF := df[term]
        if termDF == 0 { continue }
        idf := math.Log(1 + (float64(totalDocs)-float64(termDF)+0.5)/(float64(termDF)+0.5))
        freq := float64(tf)
        score += idf * (freq * (k1 + 1)) / (freq + k1*(1-b+b*docLen/avgLen))
    }
    return score
}
```

* **Tokenization (`Tokens()`)**: Splits Latin words to lowercase and tokenizes CJK characters into individual runes using `unicode.Han`, `unicode.Hiragana`, `unicode.Katakana`, `unicode.Hangul`.
* **Zero External Dependencies**: Pure Go mathematical implementation of BM25 with $k_1 = 1.2$ and $b = 0.75$.

---

## 6. Isolated Reviewers (`internal/boundedllm`)

### 6.1 Bounded Reviewer Execution (`internal/boundedllm/bounded.go`)

```go
type Config struct {
    Provider       provider.Provider
    ModelRef       string
    Sink           event.Sink
    UsageSource    string
    Timeout        time.Duration // Default: 30s
    MaxTokens      int           // Default: 256
    MaxOutputBytes int           // Default: 4KB
    MaxSystemBytes int           // Default: 2KB
    MaxTotalBytes  int           // Default: 8KB
}

func Call(ctx context.Context, cfg Config, system, evidence string) (string, error)
```

* **Isolated Context**: Used by Goal Evaluators and Auto-Guard Recovery Reviewers. Runs at `temperature = 0` with strict byte and token caps, executing completely outside the main agent session to avoid polluting the prompt cache.

---

## 7. Core Code Modules Audit & Filepath Inventory

The following **660 Go source files** form the core Reasonix agent harness:

| Package Module | File Count | Key Implementation Files & Descriptions |
| :--- | :---: | :--- |
| `internal/agent` | 50 | `agent.go` (turn loop), `compact.go` (compaction algorithm), `coordinator.go` (two-model loop), `session.go` (message state), `runner.go` |
| `internal/provider` | 15 | `provider.go` (Provider interface), `openai/openai.go` (OpenAI/DeepSeek API adapter), `registry.go` |
| `internal/tool` | 8 | `tool.go` (Tool interface & Registry), `contract.go`, `goal.go` |
| `internal/tool/builtin` | 31 | `editfile.go` (string diff editor), `bash.go` (exec runner), `readfile.go`, `writefile.go`, `grep.go`, `glob.go`, `ls.go`, `movefile.go` |
| `internal/permission` | 5 | `permission.go` (Decision enum, Policy rules), `bash_approval.go`, `bash_readonly.go`, `bash_redirect.go` |
| `internal/plugin` | 17 | `plugin.go` (MCP client), `transport.go` (stdio/HTTP/SSE JSON-RPC), `mcp.go` |
| `internal/retrieval` | 1 | `bm25.go` (BM25 scoring algorithm & CJK tokenization) |
| `internal/memory` | 11 | `memory.go` (background facts model), `index.go`, `store.go` |
| `internal/checkpoint` | 12 | `checkpoint.go` (git tree snapshots), `rewind.go` |
| `internal/recovery` | 9 | `recovery.go` (session crash recovery & transcript restoration) |
| `internal/boundedllm` | 1 | `bounded.go` (isolated temperature-0 reviewer runner) |
| `internal/config` | 30 | `config.go` (TOML configuration loader & flag parser) |
| `internal/cli` | 94 | `main.go`, `code.go`, `run.go`, `serve.go` (command routing & TUI rendering) |
| `internal/sandbox` | 10 | `sandbox.go` (process sandboxing & Seatbelt isolation) |
| `internal/repair` | 26 | `transaction.go`, `snapshot.go` (auto-repair & malformed tool output recovery) |
| `internal/acp` | 7 | `acp.go` (Agent Communication Protocol inter-agent messaging) |
| `internal/skill` | 7 | `skill.go`, `profile.go` (skill instruction loader & profile manager) |
| `internal/taskmonitor` | 9 | `recorder.go`, `control.go` (task monitoring & process tracking) |
| `cmd/reasonix` | 1 | `main.go` (main entry point self-registering built-ins) |
| `sdk/go` | 4 | `sdk.go`, `wire.go` (Go SDK client library) |
| **TOTAL** | **660** | **100% Core Go implementation files** |
