---
status: rationale
retrieval: excluded
---

# BLUEPRINT COMPLETO DA ARQUITETURA DO AETHER v3.0.0B

> **Autor:** Tech Lead 2 (PhD) / Principal Software Architect  
> **Data:** 05 de Agosto de 2026  
> **Target:** `docs/rationale/rewrite_b/rewrite_v300_blueprint_arquitetura_B.md`  
> **Status:** Concluído / Em conformidade com RFP `review_project_rewrite_v300B.md`  
> **Tom de Escrita:** Analítico, baseado em evidências empíricas e propositivo (sem imperativos), fornecendo diretrizes flexíveis para a avaliação do Tech Lead.

---

## 1. VISÃO GERAL DA ARQUITETURA HEXAGONAL & ESTRUTURA MASTER MULTI-ENGINE

O **AETHER v3.0.0B** é estruturado sob os princípios de **Arquitetura Hexagonal (Ports & Adapters)**, **Capability Authorization (CAR Model)**, o desacoplamento **Brain / Hands / Session Log** (*Anthropic Managed Agents 2026* e paper arXiv 2605.18747), o **GEPA Reflective Auto-Evolution Engine** (*Hermes Self-Evolution*), a **Infraestrutura Nativa Rust com Actor Hunk Tracking e PTY Harness** (*Grok Build*) e os **Mecanismos de Fuzzy Patch Seeking, ExecPolicy AST, Pre-Warmed Containers e Codemode Execution** (*OpenAI Codex CLI & OpenHands*). O namespace final de produção é **`src/aether`**.

### As Três Propriedades Fundamentais do Harness (arXiv 2605.18747):
1. **Paridade (Parity):** O ambiente percebido pelo agente no workspace é idêntico ao ambiente do desenvolvedor humano no terminal, prevenindo desvios de contexto.
2. **Receptivity (Receptividade):** O loop aceita observações do ambiente (erros de compilação, linter, stack traces) diretamente na iteração seguinte para reparo em tempo real (*In-Loop Real-Time Repair*).
3. **Observability (Observabilidade):** Gravação determinística de todas as ações, chamadas de ferramentas e estados em um barramento de eventos append-only persistente com exportação OpenTelemetry.

---

## 2. ESTRUTURA GLOBAL DE DIRETÓRIOS (`src/aether/`)

```
src/aether/
├── __init__.py
├── cli.py                        # Entrypoint da linha de comando
├── core_rs/                      # Módulo nativo Rust (PyO3) - Inspirado no Grok/Codex
│   ├── Cargo.toml
│   └── src/
│       ├── ast_treesitter.rs     # AST Parsing de altíssima velocidade (<50ns)
│       ├── fast_indexer.rs       # Walk & FTS5 em Rust
│       ├── fast_worktree_cow.rs  # Worktrees nativos OverlayFS / Btrfs CoW (<10ms)
│       ├── hunk_tracker.rs       # Actor Hunk Tracking (Atribuição Agent vs User)
│       ├── seek_sequence.rs      # Fuzzy Hunk Sequence Seeking (Fuzzy Patch Matching)
│       ├── exec_policy_ast.rs    # Validador de AST de Comandos Shell (ExecPolicy)
│       ├── pty_harness.rs        # Terminal PTY Pseudo-Terminal Harness
│       └── prompt_queue.rs       # Fila e fusão dinâmica de prompts concorrentes
├── domain/                       # Pure Domain Models (Zero I/O)
│   ├── __init__.py
│   ├── config.py
│   ├── content.py
│   ├── control.py
│   ├── events.py
│   ├── trajectory.py
│   └── upcasters.py              # Migração Transparente de Schemas Legados
├── ports/                        # Interfaces Protocol (Contratos Hexagonais - 9 Módulos Harness)
│   ├── __init__.py
│   ├── code_graph.py
│   ├── evaluator.py              # Tri-State Gates & Ablation Evaluator
│   ├── governor.py               # Budget & Resource Governor
│   ├── indexer.py
│   ├── memory.py                 # 3-Track Memory Interface
│   ├── model.py                  # LLM Provider API Interface
│   ├── policy.py                 # CAR Policy Interface
│   ├── sandbox.py                # Isolated Hands Interface
│   ├── search.py
│   ├── tool_registry.py          # Tool Search on Demand Registry
│   ├── trajectory.py             # Event Stream Persistence Interface
│   └── workspace.py
├── kernel/                       # Trusted Computing Base (TCB)
│   ├── __init__.py
│   ├── bus.py                    # Event Bus Assíncrono com exportação OpenTelemetry (OTel)
│   ├── dispatch.py               # Choke-point seguro de ferramentas
│   ├── governor.py               # Resource & Budget Governor
│   └── policy/
│       ├── engine.py             # Capability Authorization Register (CAR)
│       └── effects.py
├── adapters/                     # Implementações concretas das Portas
│   ├── code_graph/               # Adaptação Rust PyO3 Tree-sitter
│   ├── indexer/                  # Adaptação FTS5 & Search Service
│   ├── model/                    # Adaptação LLM (Opus / Sonnet / DeepSeek)
│   ├── sandbox/                  # Pre-Warmed Container Pool & Native Sandbox (bwrap)
│   ├── search/                   # Adaptação Best-of-N & RRF Scoring
│   ├── tools/                    # 41 Ferramentas Nativas do Sistema
│   ├── trajectory/               # Adaptação SQLite Engine WAL Journaling
│   └── workspace/                # Adaptação Git Worktrees CoW
├── agency/                       # Agência, Loop de Execução e Contexto (The Brain)
│   ├── __init__.py
│   ├── architect.py              # Modelo Arquiteto (Opus 5 - Planejamento Conceitual)
│   ├── editor.py                 # Modelo Editor (Sonnet/Haiku - Diffs Cirúrgicos)
│   ├── codemode.py               # Execução Programática de Ferramentas em Loop Local
│   ├── freeze.py                 # Hibernação FrozenRunState
│   ├── conductor.py              # Conductor System 3 Multi-Agent Engine
│   ├── run_loop.py               # Real-Time In-Loop Repair Engine
│   └── context/
│       ├── assembler.py          # Montador de Contexto Alinhado a Cache (>92%)
│       ├── compactor.py          # Exchange-Granular Compactor
│       ├── dynamic_dispatch.py   # Tool Search on Demand (37% menos tokens)
│       └── taint_gate.py         # Sanitizador TaintGate (UNTRUSTED_TAINTED)
├── evolution/                    # Módulo de Auto-Evolução Reflexiva (GEPA / Hermes)
│   ├── __init__.py
│   ├── gepa_evolver.py           # Otimizador Reflexivo de Prompts & Skills (Auto Dream)
│   ├── trace_miner.py            # Mineração de Trajetórias de Produção
│   └── dataset_exporter.py       # Exportador SFT / DPO
└── tui/                          # Terminal User Interface (React + Ink / Textual)
    ├── __init__.py
    ├── app.py                    # Aplicação Multi-Pane
    ├── components/               # Painéis de Diff Side-by-Side, Hunk Reverter & Logs
    └── view_model.py             # Adaptador de Eventos para a UI
```

---

## 3. DIAGRAMA ARQUITETURAL COMPLETO BRAIN / HANDS / LOG (MERMAID)

```mermaid
graph TB
    subgraph TUI_LAYER [Camada de Interface & UX Multi-Pane (src/aether/tui)]
        TUI[Terminal UI - React Ink / Textual App]
        CLI[CLI Commands Parser - 101 Commands]
        HunkViewer[Hunk Diff Inspector & Reverter]
    end

    subgraph BRAIN_LAYER [Camada de Agência & Raciocínio - BRAIN (src/aether/agency)]
        RL[RunLoop Real-Time Repair Engine]
        ARCH[Architect Model - Opus 5]
        EDIT[Editor Model - Sonnet / Haiku]
        CODEMODE[Codemode Local Tool Runner]
        CONDUCTOR[Conductor System 3 Manager]
        CTX[Context Assembler - Prompt Cache >92%]
        COMPACTOR[Exchange-Granular Compactor]
        TAINT[TaintGate Sanitizer]
        DISPATCH[Tool Search on Demand]
    end

    subgraph EVOLVER_LAYER [Camada de Auto-Evolução Reflexiva (src/aether/evolution)]
        GEPA[GEPA Reflective Evolver]
        MINER[SessionDB Trace Miner]
        AUTODREAM[Auto Dream Memory Worker]
        DPO[Dataset Exporter SFT/DPO]
    end

    subgraph KERNEL_LAYER [Trusted Computing Base - TCB (src/aether/kernel)]
        DISP[Kernel Dispatch Choke-Point]
        CAR[Capability Authorization Engine - Policy]
        EXEC_AST[Shell Command AST ExecPolicy]
        BUS[Async Event Bus - OpenTelemetry OTel]
        GOV[Resource & Budget Governor]
    end

    subgraph HANDS_LAYER [Camada de Execução Rust & Containers - HANDS (src/aether/adapters & core_rs)]
        A_LLM[LLM API Adapters - Opus/Sonnet/DeepSeek]
        A_WORK[Git Worktrees CoW Adapter <10ms]
        A_RUST[Rust Core PyO3 - Tree-sitter & Fuzzy Patch Seeking]
        A_HUNK[Actor Hunk Tracker - Agent vs User]
        A_PTY[PTY Pseudo-Terminal Harness]
        A_CONTAINER[Pre-Warmed Container Pool & Native bwrap Sandbox]
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
    AUTODREAM -->|Otimiza Texto de Skills & Prompts| CTX
    MINER --> DPO

    DISP --> A_LLM
    DISP --> A_WORK
    DISP --> A_RUST
    DISP --> A_HUNK
    DISP --> A_PTY
    DISP --> A_CONTAINER
```

---

## 4. REQUISITOS DE CONFORMIDADE E REGRAS DE QUALIDADE

1. **Async I/O Concurrency:** Utilização exclusiva de `anyio` ou `asyncio` não-bloqueante em todas as operações de I/O.
2. **Type Hints & Rigor:** 100% de cobertura de tipagem estrita com `pyright` no modo strict e `ruff`.
3. **Observabilidade OTel:** Exportação de eventos de telemetria no padrão OpenTelemetry via `kernel/bus.py`.
4. **Zero Legacy Bloat:** Abstrações de terceiros genéricas são vedadas no núcleo. O harness do **AETHER v300B** é minimalista, desacoplado e customizado para alta performance.
