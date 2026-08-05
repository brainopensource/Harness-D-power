---
status: rationale
retrieval: excluded
---

# BLUEPRINT ARQUITETURAL COMPLETO E REFINADO: AETHER v3.0.0B
## Análise Comparativa de Concorrentes, Sugestões da Track A & Pontos de Debate PhD (15 Domínios)

> **Autor:** Tech Lead B (PhD) / Principal Software Architect  
> **Data:** 05 de Agosto de 2026  
> **Target Document:** `docs/rationale/rewrite_b/rewrite_v300_blueprint_arquitetura_B.md`  
> **Fontes Primárias:** Competitor Research (`docs/competitors_research/tech_lead_B/`) & Track A Rationale (`docs/rationale/rewrite/`).  
> **Status:** Concluído / Em Conformidade Estrita com a REVISÃO B.

---

## 1. VISÃO GERAL DA ARQUITETURA MULTI-ENGINE & CONFRONTO COM CONCORRENTES

O **AETHER v3.0.0B** é o harness de autonomia de código de próxima geração projetado no namespace `src/aether/`. O sistema sintetiza as melhores inovações descobertas no confronto direto entre a especificação da REVISÃO B, a pesquisa dos concorrentes SOTA (Claude Code, Grok Build, Hermes) e os valiosos princípios de controle da **Track A** (Tech Lead A).

### 1.1 As Três Propriedades Fundamentais do Harness (arXiv 2605.18747):
1. **Paridade (Parity):** O ambiente percebido pelo agente no workspace é idêntico ao ambiente do desenvolvedor humano no terminal, prevenindo desvios de contexto e abstrações com perdas.
2. **Receptividade (Receptivity):** O loop aceita observações do ambiente (erros de compilação, linter, stack traces) diretamente na iteração seguinte para reparo em tempo real (*In-Loop Real-Time Repair*) sem invalidar marcadores fixos de cache.
3. **Observabilidade (Observability):** Gravação determinística de todas as ações, chamadas de ferramentas e estados em um barramento de eventos append-only persistente com exportação OpenTelemetry (OTel).

---

## 2. ESTRUTURA GLOBAL DE DIRETÓRIOS (`src/aether/`)

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
├── ports/                        # Interfaces Protocol (Contratos Hexagonais - 100% Remoteable)
├── kernel/                       # Trusted Computing Base (TCB)
│   ├── bus.py                    # Async Event Bus com Exportação OpenTelemetry (OTel)
│   ├── dispatch.py               # Choke-point Único de Execução de Ferramentas
│   ├── governor.py               # ResourceGovernor (Spend, Leases & Token Budget)
│   └── policy/                   # Capability Authorization Register (CAR Engine)
├── adapters/                     # Implementações Concretas dos Contratos Hexagonais
├── agency/                       # Camada de Agência, Loop de Execução e Raciocínio (The Brain)
│   ├── architect.py              # Modelo Arquiteto (Opus 5 - Planejamento Conceitual)
│   ├── editor.py                 # Modelo Editor (Sonnet/Haiku - Diffs Search/Replace Cirúrgicos)
│   ├── codemode.py               # Execução Programática de Ferramentas em Loop Local
│   ├── freeze.py                 # Hibernação Durável FrozenRunState (SQLite Serializer)
│   ├── conductor.py              # Conductor System 3 Multi-Agent DAG Manager
│   ├── run_loop.py               # Real-Time In-Loop Repair Engine
│   └── context/                  # Assembler, Compactor, Dynamic Dispatch & TaintGate
├── workflow/                     # [Sugestão Track A] WorkflowStep DAG & Memoização por Input Digest
├── evolution/                    # Módulo de Auto-Evolução Reflexiva (GEPA Engine)
└── tui/                          # Terminal User Interface (React Ink / Textual Reativa)
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

    subgraph BRAIN_LAYER [Camada de Agência & Raciocínio - BRAIN (src/aether/agency & workflow)]
        RL[RunLoop Real-Time Repair Engine]
        ARCH[Architect Model - Opus 5]
        EDIT[Editor Model - Sonnet / Haiku]
        CODEMODE[Codemode Local Tool Runner]
        CONDUCTOR[Conductor System 3 Multi-Agent DAG Manager]
        WORKFLOW_DAG[WorkflowStep DAG Memoizado - Sugestão Track A]
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

    subgraph HANDS_LAYER [Camada de Execução Rust Core & Sandboxing (src/aether/adapters & core_rs)]
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
    RL --> WORKFLOW_DAG
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

## 4. INVARIANTES MECÂNICOS & REGRAS DE LINTER (SUGESTÃO DA TRACK A)

Sugerimos a incorporação estrita dos **9 Invariantes Mecânicos da Track A** garantidos por regras automatizadas do `import-linter` e testes de CI:

1. **I1 (Pure Domain):** `domain` não importa DBs, I/O ou HTTP (`import-linter: domain-is-pure`).
2. **I2 (Typed Ports):** Todo I/O cruza uma fronteira `Protocol` tipada (`pyright --strict`).
3. **I3 (Wire-Serializable Ports):** Todo método de porta é `async` e trafega apenas modelos Pydantic serializáveis.
4. **I4 (Adapter Substitutability):** Todo adaptador passa na mesma suíte de conformidade parametrizada.
5. **I5 (Single Dispatch Choke Point):** Toda execução de ferramenta passa exclusivamente por `kernel/dispatch.py`.
6. **I6 (Frozen Extension Resolution):** Entrypoints são resolvidos na composição e congelados.
7. **I7 (Generator ≠ Evaluator):** O agente que escreve código nunca altera os testes que o avaliam (`require_tests_unmodified`).
8. **I8 (Immutable TCB):** A camada Kernel e o Evaluator são imutáveis e isolados (`import-linter: tcb-isolation`).
9. **I9 (Hard Gates Admit; Proxies Rank):** Gates determinísticos admitem soluções; modelos aprendidos apenas ranqueiam.

---

## 5. ANÁLISE DE CONVERGÊNCIA: SUGESTÕES DA TRACK A & PONTOS DE DEBATE PARA A REUNIÃO DOS TECH LEADS

Apresentamos abaixo os tópicos para alinhamento entre as abordagens do Tech Lead A e Tech Lead B:

### 5.1 Sugestões da Track A Incorporadas à Track B (Recomendação de Consenso)
* **Sugestão 1: Workflow Step DAG com Memoização (`workflow/`):** Adotar a abstração `WorkflowStep[In, Out]` com caching por digest dos inputs (ADR-0018 / A-024) para reduzir drasticamente o custo computacional de ablações em subgrafos de agentes.
* **Sugestão 2: Sequenciamento de Cache no Best-of-N:** Em chamadas Best-of-N concorrentes, aguardar o primeiro token retornado da 1ª requisição antes de disparar as N-1 requisições restantes. Isso evita converter N-1 leituras de cache em N-1 gravações de cache na Anthropic.
* **Sugestão 3: Verificação de Catálogo de Eventos no CI (`gen_event_catalog.py --check`):** Garantir que a documentação dos eventos da telemetria seja gerada diretamente a partir do código tipado e validada no CI contra desvios.
* **Sugestão 4: Chamadas Auxiliares com Prefixo Aquecido (A-023):** Garantir que requisições auxiliares (sumarizador, juiz BoN) derivem do mesmo runtime do pai, herdando o prefixo de cache já aquecido.

---

### 5.2 Pontos de Debate e Opções Conflitantes (Para Decisão na Reunião de Tech Leads)

#### DEBATE 1: Estratégia de Runtime Inicial — Python Monoglota vs. Rust PyO3 Direct FFI desde o Sprint 0
* **Opção A (Tech Lead A):** Iniciar 100% em Python 3.13 no Phase 1 sem binários compilados. Migrar partes críticas para Rust (PyO3 ou IPC) apenas quando gatilhos quantitativos empíricos (`RT-1`: re-indexação >10 min, `RT-2`: RAM >300MB) forem violados.
  * *Vantagem A:* Build e ciclo de dev extremamente simples no início; zero esforço de compilação C-ABI.
* **Opção B (Tech Lead B - Nossa Proposta):** Integrar o módulo nativo `core_rs` via PyO3 C-ABI bindings desde o Sprint 0.
  * *Vantagem B:* Latência <50ns por chamada, zero contestações de GIL, parsing de AST Tree-sitter em altíssima velocidade e suporte nativo a Fast CoW Worktrees (<10ms) e PTY Harness desde o primeiro dia.
* **Proposta de Compromisso:** Desenvolver o módulo nativo em Rust PyO3 como especificado na Track B, fornecendo um *fallback* em Python puro para ambientes onde o compilador Rust não estiver presente.

#### DEBATE 2: Modelo de Execução de Diffs — Search/Replace Ancorado por Texto vs. Architect/Editor Split com AST Rust
* **Opção A (Tech Lead A):** Utilizar um único modelo executando blocos Search/Replace ancorados por texto com validação sintática post-hoc em Python (`ast.parse`).
  * *Vantagem A:* Menor custo por tarefa (apenas uma chamada de modelo por turno).
* **Opção B (Tech Lead B - Nossa Proposta):** Separar em Arquiteto (Opus 5 - plano conceitual) e Editor (Sonnet/Haiku - diff cirúrgico) com pré-validação sintática Tree-sitter em Rust em <50ns.
  * *Vantagem B:* Maior precisão em edições complexas e zero risco de SyntaxError gravado no disco; rollback atômico antes do I/O.
* **Proposta de Compromisso:** Manter a estrutura desacoplada em `architect.py` e `editor.py`, permitindo alternar via configuração entre modo único (Single Model) ou modo separado (Dual Model Split).

#### DEBATE 3: Estratégia de Benchmarking & Medição — Tier 0 Local vs. Direct SOTA Frontier Ablation
* **Opção A (Tech Lead A):** Foco prioritário na estratégia **Tier 0** (rodar modelos locais open-weight em hardware próprio) para medir o *scaffold-attributable lift* (delta emparelhado versus baseline single-shot no mesmo modelo) a custo zero antes de testar APIs pagas.
  * *Vantagem A:* Elimina custos com APIs durante a fase de desenvolvimento e detecta ruídos de medição A/A precocemente.
* **Opção B (Tech Lead B - Nossa Proposta):** Executar ablações estatísticas rigorosas ($p < 0.05$, $N \ge 50$) diretamente contra APIs de ponta (Opus 5 / Sonnet 3.5) visando metas de benchmark absolutas (**SWE-bench Verified 90%+**, **Pro 60%+**).
  * *Vantagem B:* Valida o agente no cenário real de produção com modelos de capacidade máxima.
* **Proposta de Compromisso:** Adotar o **Tier 0 da Track A** nos Sprints 0 e 1 para validação de instrumentação sem custo, evoluindo para a **Ablação Estatística da Track B** nos Sprints 2, 3 e 4.
