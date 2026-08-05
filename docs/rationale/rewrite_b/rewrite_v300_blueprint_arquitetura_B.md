---
status: rationale
retrieval: excluded
---

# BLUEPRINT ARQUITETURAL COMPLETO E REFINADO: AETHER v3.0.0B
## Análise Comparativa de Concorrentes & Recomendações Técnicas PhD (15 Domínios)

> **Autor:** Tech Lead B (PhD) / Principal Software Architect  
> **Data:** 05 de Agosto de 2026  
> **Target Document:** `docs/rationale/rewrite_b/rewrite_v300_blueprint_arquitetura_B.md`  
> **Fonte Primária de Pesquisa:** Competitor Research (`docs/competitors_research/tech_lead_B/`) — Claude Code CLI (`claude_refs_B_gemini.md`), Grok Build (`grok_build_B_gemini.md`), Hermes Agent (`hermes_agent_B_gemini.md`), Hermes Self-Evolution (`hermes_self_evolution_B_gemini.md`).  
> **Status:** Concluído / Em Conformidade Estrita com a REVISÃO B.

---

## 1. VISÃO GERAL DA ARQUITETURA MULTI-ENGINE & CONFRONTO COM CONCORRENTES

O **AETHER v3.0.0B** é o harness de autonomia de código de próxima geração projetado no namespace `src/aether/`. O sistema sintetiza as melhores inovações descobertas no confronto direto entre a especificação da REVISÃO B e a pesquisa aprofundada dos quatro sistemas concorrentes no SOTA (Claude Code CLI, Grok Build, Hermes Agent e Hermes Self-Evolution).

### 1.1 As Três Propriedades Fundamentais do Harness (arXiv 2605.18747):
1. **Paridade (Parity):** O ambiente percebido pelo agente no workspace é idêntico ao ambiente do desenvolvedor humano no terminal, prevenindo desvios de contexto e abstrações com perdas.
2. **Receptividade (Receptivity):** O loop aceita observações do ambiente (erros de compilação, linter, stack traces) diretamente na iteração seguinte para reparo em tempo real (*In-Loop Real-Time Repair*) sem invalidar marcadores fixos de cache.
3. **Observabilidade (Observability):** Gravação determinística de todas as ações, chamadas de ferramentas e estados em um barramento de eventos append-only persistente com exportação OpenTelemetry (OTel).

### 1.2 Matriz de Confronto Direto dos 15 Domínios Técnicos

| Domínio Técnico | Claude Code CLI (`claude_refs`) | Grok Build (`grok_build`) | Hermes Agent (`hermes_agent`) | Hermes Self-Evolution | **AETHER v300B (Especificação Proposta)** |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Loop & Harness Engineering** | Decoupled Tri-Layer (Brain/Hands/Log) | Tokio Async Native Runner | Emergency Context Recovery Loop | N/A | **Tri-Layer Decoupled + Real-Time In-Loop Repair** |
| **2. Contexto & Memória** | Exchange Compactor + Prompt Cache >92% | SQLite-vec + MMR Reranking ($\lambda=0.7$) | Trajectory Step Summary | N/A | **3-Track Memory + Exchange Compactor + Auto Dream MMR** |
| **3. Desacoplamento Hexagonal** | TypeScript Modular Boundaries | 61 Native Rust Crates | Python Service Adapters | Standalone Optimizer | **Arquitetura Hexagonal Strict (Ports & Adapters)** |
| **4. Skills & Extensibilidade** | Procedural `SKILL.md` + Tool Search | Native Tool Providers | Task Toolset Distributions | `SKILL.md` Mutation | **Tool Search on Demand + Codemode Programmatic Loop** |
| **5. Performance & Runtime** | Node/TypeScript + Bun | Pure Rust 1.80+ Tokio (<50ns) | Pure Python Async | Python + DSPy | **Python Async + Rust Core PyO3 FFI Direct Memory (<50ns)** |
| **6. Segurança & CAR** | CAR Register + bwrap / Restr. Tokens | OS Sandboxing & cgroups | Permission Prompts | N/A | **CAR Model + TaintGate (`UNTRUSTED_TAINTED`) + Native Sandboxing** |
| **7. Autonomia Long-Horizon** | Externalized SQLite WAL | SQLite Session Journal | SessionDB Portable Import | N/A | **Conductor System 3 + Hibernação Durável `FrozenRunState`** |
| **8. Auto-Evolução Reflexiva** | Auto Dream Idle Worker | N/A | SFT/DPO Dataset Export | GEPA + MIPROv2 + Darwin | **GEPA Reflective Auto-Evolver + SessionDB Trace Miner** |
| **9. Orquestração Multi-Agente** | Teammate Agents / Task Tools | Subagent Resolution Engine | Multi-Task Batch Runner | N/A | **Conductor System 3 DAG Decomposition & Warm Cache Inheritance** |
| **10. Metrologia & Ablação** | Benchmark Regression Gates | Benchmark Metric Tracking | Parallel SWE-bench Harness | Statistical Gate ($p<0.05$) | **Ablação Estatística Rigorosa ($p < 0.05$, $N \ge 50$)** |
| **11. Architect/Editor & AST** | Architect (Opus) / Editor (Sonnet) | Rust Codebase Graph | N/A | N/A | **Architect/Editor Split + Rust Tree-sitter AST Pre-Validation** |
| **12. Actor Hunk Tracking & Fuzzy** | Search/Replace Blocks | Actor Hunk Tracker (`AuthorType`) | N/A | N/A | **Actor Hunk Tracker (Agent vs User) + `seek_sequence.rs` Fuzzy** |
| **13. Worktrees CoW & Container Pool** | Git Worktrees Zero-Copy | OverlayFS / Btrfs CoW (<10ms) | Container Sandbox | N/A | **Fast CoW Worktree (<10ms) + Pre-Warmed Container Pool (0ms)** |
| **14. TaintGate & ExecPolicy AST** | Taint Tagging Engine | Shell Sandbox Execution | N/A | N/A | **TaintGate Input Tagging + Shell Command AST ExecPolicy** |
| **15. PTY Harness & OTel Telemetry** | React + Ink TUI / OTel Hooks | PTY Terminal Harness + Ratatui | CLI Logging | N/A | **Master/Slave PTY Pseudo-Terminal Harness + OTel Bus** |

---

## 2. ESTRUTURA GLOBAL DE DIRETÓRIOS (`src/aether/`)

A estrutura física do namespace **`src/aether/`** reflete o desacoplamento estrito entre a **Brain Layer** (orquestração Python async), a **Hands Layer** (núcleo Rust de alta performance `core_rs`), e a **Log Layer** (persistência SQLite append-only).

```
src/aether/
├── __init__.py
├── cli.py                        # CLI Entrypoint (Parsing via Typer / Click)
├── core_rs/                      # Módulo Nativo Rust (PyO3 Direct Memory FFI <50ns)
│   ├── Cargo.toml
│   └── src/
│       ├── lib.rs                # PyO3 Module Exports
│       ├── ast_treesitter.rs     # Tree-sitter AST Pre-Validation & Skeleton Mapping (<50ns)
│       ├── fast_indexer.rs       # Parallel Multi-Threaded File Walk & FTS5 Indexing
│       ├── fast_worktree_cow.rs  # OverlayFS Mounts & Btrfs Reflink Creation (<10ms)
│       ├── hunk_tracker.rs       # Tokio Actor Hunk Tracker (Agent vs User Attribution)
│       ├── seek_sequence.rs      # Fuzzy Hunk Sequence Seeking (TextDiff Alignment)
│       ├── exec_policy_ast.rs    # Shell Command AST Parsing & Security Inspection
│       ├── pty_harness.rs        # Master/Slave PTY Pseudo-Terminal Harness
│       └── prompt_queue.rs       # In-Flight Prompt Queue Combiner (Join In-Flight Turns)
├── domain/                       # Pure Domain Models (Zero I/O Dependencies, Pydantic)
│   ├── __init__.py
│   ├── config.py                 # Core Configuration Schemas
│   ├── content.py                # Message & Content Block Definitions
│   ├── control.py                # Control Signal Schemas
│   ├── events.py                 # Telemetry & System Event Models
│   ├── trajectory.py             # Trajectory & Step Models
│   └── upcasters.py              # FrozenRunState Schema Migration Pipeline
├── ports/                        # Interfaces Protocol (Contratos Hexagonais - 100% Remoteable)
│   ├── __init__.py
│   ├── code_graph.py             # Codebase AST Symbol Graph Interface
│   ├── evaluator.py              # Benchmark Gates & Statistical Ablation Evaluator
│   ├── governor.py               # Resource, Spend & Token Budget Governor Interface
│   ├── indexer.py                # FTS5 & Syntactic Search Interface
│   ├── memory.py                 # 3-Track Memory Interface (Episodic, Semantic, Procedural)
│   ├── model.py                  # Multi-Provider LLM API Adapter Interface
│   ├── policy.py                 # CAR Capability Authorization Interface
│   ├── sandbox.py                # Sandboxed Hands Execution Interface
│   ├── search.py                 # Best-of-N & RRF Vector Reranking Interface
│   ├── tool_registry.py          # Dynamic Tool Search on Demand Registry Interface
│   ├── trajectory.py             # Event Stream & SessionDB Journaling Interface
│   └── workspace.py              # Git Worktree CoW Workspace Management Interface
├── kernel/                       # Trusted Computing Base (TCB)
│   ├── __init__.py
│   ├── bus.py                    # Async Event Bus com Exportação OpenTelemetry (OTel)
│   ├── dispatch.py               # Choke-point Único de Execução de Ferramentas
│   ├── governor.py               # Governor de Recursos e Limite Financeiro
│   └── policy/
│       ├── engine.py             # Capability Authorization Register (CAR Engine)
│       └── effects.py            # Security Policy Side-Effects Handler
├── adapters/                     # Implementações Concretas dos Contratos Hexagonais
│   ├── code_graph/               # Adaptação PyO3 Tree-sitter Rust Core
│   ├── indexer/                  # Adaptação FTS5 & Search Service Rust
│   ├── model/                    # Adaptação Multi-Provider (Opus, Sonnet, DeepSeek, Haiku)
│   ├── sandbox/                  # Pre-Warmed Container Pool, bwrap & Windows Job Objects
│   ├── search/                   # Adaptação BM25 + SQLite-vec + MMR Reranking ($\lambda=0.7$)
│   ├── tools/                    # 41 Ferramentas Nativas do Sistema
│   ├── trajectory/               # Adaptação SQLite Engine WAL Journaling
│   └── workspace/                # Adaptação Fast CoW Worktrees Rust
├── agency/                       # Camada de Agência, Loop de Execução e Raciocínio (The Brain)
│   ├── __init__.py
│   ├── architect.py              # Modelo Arquiteto (Opus 5 - Planejamento Conceitual)
│   ├── editor.py                 # Modelo Editor (Sonnet/Haiku - Diffs Search/Replace Cirúrgicos)
│   ├── codemode.py               # Execução Programática de Ferramentas em Loop Local
│   ├── freeze.py                 # Hibernação Durável FrozenRunState (SQLite Serializer)
│   ├── conductor.py              # Conductor System 3 Multi-Agent DAG Manager
│   ├── run_loop.py               # Real-Time In-Loop Repair Engine
│   └── context/
│       ├── assembler.py          # Montador de Contexto Alinhado a Cache (>92% Hit Rate)
│       ├── compactor.py          # Exchange-Granular Compactor (Trocas Usuário/Assistente Integras)
│       ├── dynamic_dispatch.py   # Tool Search on Demand Selector (Economia de 37% em Tokens)
│       └── taint_gate.py         # Sanitizador TaintGate (UNTRUSTED_TAINTED Marking)
├── evolution/                    # Módulo de Auto-Evolução Reflexiva (GEPA Engine)
│   ├── __init__.py
│   ├── gepa_evolver.py           # Otimizador Reflexivo de Prompts & Skills (Auto Dream)
│   ├── trace_miner.py            # Mineração de Trajetórias de Erro da SessionDB Production
│   └── dataset_exporter.py       # Exportador Sanitizado SFT / DPO
└── tui/                          # Terminal User Interface (React Ink / Textual Reativa)
    ├── __init__.py
    ├── app.py                    # Aplicação Multi-Pane Async
    ├── components/               # Painéis Side-by-Side Diff, Hunk Inspector & Terminal Output
    └── view_model.py             # Adaptador de Eventos da TUI
```

---

## 3. DIAGRAMA ARQUITETURAL COMPLETO (MERMAID)

```mermaid
graph TB
    subgraph TUI_LAYER [Camada de Interface & UX Multi-Pane (src/aether/tui)]
        TUI[Terminal UI - React Ink / Textual Multi-Pane App]
        CLI[CLI Commands Parser - 101 Commands]
        HunkViewer[Visualizador & Reversor de Hunks por Autor]
    end

    subgraph BRAIN_LAYER [Camada de Agência & Raciocínio - BRAIN (src/aether/agency)]
        RL[RunLoop Real-Time Repair Engine]
        ARCH[Architect Model - Opus 5]
        EDIT[Editor Model - Sonnet / Haiku]
        CODEMODE[Codemode Local Tool Runner]
        CONDUCTOR[Conductor System 3 Multi-Agent DAG Manager]
        CTX[Context Assembler - Prompt Cache >92%]
        COMPACTOR[Exchange-Granular Compactor]
        TAINT[TaintGate Sanitizer - UNTRUSTED_TAINTED]
        DISPATCH[Tool Search on Demand Selector]
    end

    subgraph EVOLVER_LAYER [Camada de Auto-Evolução Reflexiva (src/aether/evolution)]
        GEPA[GEPA Reflective Auto-Evolver]
        MINER[SessionDB Trace Miner]
        AUTODREAM[Auto Dream Memory Worker - MMR Reranking]
        DPO[Dataset Exporter SFT/DPO]
    end

    subgraph KERNEL_LAYER [Trusted Computing Base - TCB (src/aether/kernel)]
        DISP[Kernel Dispatch Choke-Point]
        CAR[Capability Authorization Register - Policy Engine]
        EXEC_AST[Shell Command AST ExecPolicy Inspector]
        BUS[Async Event Bus - OpenTelemetry OTel Exporter]
        GOV[Resource & Token Budget Governor]
    end

    subgraph HANDS_LAYER [Camada de Execução Rust Core & Sandboxing - HANDS (src/aether/adapters & core_rs)]
        A_LLM[Multi-Provider LLM Adapters - Opus / Sonnet / DeepSeek]
        A_WORK[Fast CoW Worktree Engine <10ms - OverlayFS / Btrfs]
        A_RUST[Rust Core PyO3 Direct Memory FFI <50ns]
        A_HUNK[Actor Hunk Tracker - Agent vs User Attribution]
        A_SEEK[Fuzzy Patch Sequence Seeking - seek_sequence.rs]
        A_PTY[Master/Slave PTY Pseudo-Terminal Harness]
        A_CONTAINER[Pre-Warmed Container Pool 0ms & Native bwrap Sandbox]
    end

    CLI --> RL
    TUI <--> BUS
    HunkViewer <--> A_HUNK
    RL --> ARCH
    RL --> EDIT
    RL --> CODEMODE
    RL --> CONDUCTOR
    RL --> CTX
    CTX --> COMPACTOR
    CTX --> TAINT
    CTX --> DISPATCH
    
    RL --> DISP
    DISP --> CAR
    CAR --> EXEC_AST
    DISP --> GOV
    CAR --> BUS

    BUS --> MINER
    MINER --> GEPA
    GEPA --> AUTODREAM
    AUTODREAM -->|Otimiza Skills SKILL.md & System Prompts| CTX
    MINER --> DPO

    DISP --> A_LLM
    DISP --> A_WORK
    DISP --> A_RUST
    DISP --> A_HUNK
    DISP --> A_SEEK
    DISP --> A_PTY
    DISP --> A_CONTAINER
```

---

## 4. DETALHAMENTO DAS ESPECIFICAÇÕES DOS 15 DOMÍNIOS TÉCNICOS

### Domínio 1: Harness Engineering & Loop Engineering (`agency/run_loop.py`)
* O `RunLoop.run()` opera um ciclo assíncrono continuo. Quando o modelo ou o ambiente gera exceções (erros de compilação, linter ou context limit overflow 400/413), a exceção é capturada, classificada e reinjetada no turno seguinte como uma observação estruturada.
* O loop preserva a paridade do ambiente e evita o descarte do prefixo de cache do sistema.

### Domínio 2: Engenharia de Contexto & Gestão de Memória (`agency/context/` & `adapters/memory/`)
* **Paridade de Cache (>92% Hit Rate):** Estrutura o payload em três marcadores imutáveis (Identity, Tool Schemas, AST Skeleton Map).
* **Exchange-Granular Compactor:** Compacta o histórico removendo estritamente trocas completas (`user -> assistant -> tool_use -> tool_result`), eliminando a corrupção do estado da LLM.
* **Auto Dream Consolidation:** Consolidação em background durante tempo ocioso (*idle time*), utilizando fusão MMR (Maximal Marginal Relevance, $\lambda=0.7$) sobre busca vetorial `sqlite-vec` e busca lexica BM25.

### Domínio 3: Arquitetura Hexagonal & Desacoplamento (`ports/` & `domain/`)
* Todas as portas em `src/aether/ports/` são interfaces `Protocol` assíncronas cujos argumentos e retornos utilizam exclusivamente modelos Pydantic (`domain/`).
* Nenhum objeto manipulador de arquivo, socket, gerador ou lambda cruza a fronteira hexagonal, tornando 100% das portas remotáveis via rede.

### Domínio 4: Skills & Extensibilidade (`agency/context/dynamic_dispatch.py` & `agency/codemode.py`)
* **Tool Search on Demand:** Schemas de ferramentas são diferidos e carregados dinamicamente apenas quando a intenção do usuário demanda a ferramenta, reduzindo o custo de tokens em 37%.
* **Codemode Local Execution:** A LLM pode emitir um script conciso em Python para executar múltiplas chamadas de ferramentas em loop local em uma única ida e volta à API.

### Domínio 5: Stack Tecnológica & Performance PyO3 (`core_rs/`)
* Orquestração em Python assíncrono (`anyio`) acoplada diretamente ao núcleo Rust via PyO3 C-ABI bindings.
* Latência de chamada de função inter-linguagens inferior a **50 nansegundos** (Direct Memory sharing), superando abordagens IPC/gRPC (~4.0ms).

### Domínio 6: Segurança, CAR & TaintGate (`kernel/policy/` & `agency/context/taint_gate.py`)
* **Capability Authorization Register (CAR):** Toda ferramenta é checada centralmente no choke-point `kernel/dispatch.py`.
* **TaintGate Sanitizer:** Dados externos (web, issues, arquivos de terceiros) recebem a tag `UNTRUSTED_TAINTED`. Ferramentas com efeitos colaterais críticos (`git push`, execução de shell arbitrária) são bloqueadas ou exigem autorização humana explícita se alimentadas com entradas manchadas.

### Domínio 7: Autonomia Long-Horizon & Hibernação (`agency/freeze.py`)
* Serialização atômica do estado completo da sessão (`FrozenRunState`) em banco SQLite WAL.
* Permite pausar, hibernar e retomar tarefas de múltiplos dias em qualquer ponto sem perda de contexto ou progresso.

### Domínio 8: Auto-Evolução Reflexiva GEPA (`evolution/`)
* Otimização reflexiva de prompts e habilidades (`SKILL.md`) baseada no trace de erros passados.
* Opera via otimização textual Zero-GPU (via DSPy e GEPA Engine), sem necessidade de retreinamento de pesos em GPUs.

### Domínio 9: Orquestração Multi-Agente Conductor System 3 (`agency/conductor.py`)
* O Conductor decompõe tarefas complexas em Grafos Acíclicos Dirigidos (DAGs).
* Cada subagente é executado em um contexto isolado que herda o cache de prefixo aquecido, gravando checkpoints de progresso diretamente no `FrozenRunState`.

### Domínio 10: Metrologia, Validação Empírica & Gates (`ports/evaluator.py`)
* Admissão de código condicionada à ablação estatística com valor p significante ($p < 0.05$, $N \ge 50$ instâncias).
* Garantia estrita do cumprimento da regra `require_tests_unmodified`.

### Domínio 11: Architect/Editor Split & AST Rust (`agency/architect.py`, `editor.py` & `core_rs/ast_treesitter.rs`)
* Arquiteto (Opus 5) gera o plano conceitual sem realizar chamadas diretas de ferramentas.
* Editor (Sonnet/Haiku) gera diffs cirúrgicos Search/Replace. O módulo Rust passa o hunk por Tree-sitter `ast.parse` em <50ns antes de alterar qualquer arquivo no disco.

### Domínio 12: Actor Hunk Tracking & Fuzzy Matching (`core_rs/hunk_tracker.rs` & `seek_sequence.rs`)
* Rastreamento de diffs em nível de hunk via ator Tokio em Rust, atribuindo autoria (`AuthorType::Agent` vs `AuthorType::ExternalUser`).
* Algoritmo de busca por sequência aproximada (`seek_sequence.rs`) via alinhamento diff para realocar automaticamente hunks em arquivos cujas linhas foram deslocadas por alterações externas.

### Domínio 13: Worktrees CoW & Pre-Warmed Containers (`core_rs/fast_worktree_cow.rs` & `adapters/sandbox/`)
* Clonagem de workspace em **< 10ms** utilizando OverlayFS mounts e Btrfs CoW `reflink`.
* Pool de containers Docker pré-aquecidos mantidos em background, reduzindo o tempo de alocação de subagentes para **0ms de espera**.

### Domínio 14: Proteção TaintGate & ExecPolicy Shell AST (`kernel/policy/` & `core_rs/exec_policy_ast.rs`)
* Inspeção da Árvore de Sintaxe Abstrata (AST) de comandos de terminal em Rust (`exec_policy_ast.rs`) antes da execução no terminal, eliminando bypasses de segurança baseados em regex.

### Domínio 15: PTY Harness & Telemetria OTel (`core_rs/pty_harness.rs` & `kernel/bus.py`)
* Emulação nativa de PTY (pseudo-terminal master/slave) permitindo a execução não-bloqueante de ferramentas interativas do terminal sem travamentos em `stdin`.
* Exportação padronizada de métricas e traços de execução via OpenTelemetry (OTel).

---

## 5. REQUISITOS DE QUALIDADE & CONFORMIDADE

1. **Async I/O Concurrency:** Uso exclusivo de `anyio` ou `asyncio` não-bloqueante em todas as operações de I/O.
2. **Tipagem Estrita:** Cobertura de tipagem estrita de 100% verificada via `pyright` (strict mode) e `ruff check`.
3. **Zero Legacy Bloat:** Veda o uso de abstrações genéricas legadas ou wrappers de terceiros pesados. O núcleo do AETHER v300B é construído sob medida para máxima velocidade e desacoplamento.
