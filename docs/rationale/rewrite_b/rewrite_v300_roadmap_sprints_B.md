# ROADMAP DE SPRINTS, GATES DE ABLAÇÃO E CRITÉRIOS BENCHMARK (AETHER v300B)

> **Autor:** Tech Lead 2 (PhD) / Principal Software Architect  
> **Data:** 05 de Agosto de 2026  
> **Target:** `docs/rationale/rewrite_b/rewrite_v300_roadmap_sprints_B.md`  
> **Status:** Concluído / Em conformidade com RFP `review_project_rewrite_v300B.md`  
> **Tom de Escrita:** Analítico, baseado em evidências empíricas e propositivo (sem imperativos), fornecendo diretrizes flexíveis para a avaliação do Tech Lead.

---

## 1. OBJETIVO DO ROADMAP & REGRAS DE ABLAÇÃO QUANTITATIVA

Este roadmap apresenta o plano de execução propositivo por Sprints para a construção do **AETHER v3.0.0B** no namespace `src/aether/`.

### Princípio de Admissão de Código:
Recomenda-se que nenhuma alteração de mecanismo, heurística de prompt ou nova ferramenta seja promovida para a branch principal de produção sem passar por uma **Ablação Estatisticamente Comprovada** ($p < 0.05$, mínimo de 50 instâncias de teste) demonstrando:
1. Elevação estatisticamente significante na taxa de resolução (*pass rate*).
2. Redução ou manutenção do custo monetário e de latência total por tarefa.
3. Adimplência estrita à regra `require_tests_unmodified` (vedada qualquer modificação na suíte de testes de validação para forçar resultados positivos).

---

## 2. MÉTRICAS ALVO E BENCHMARKS DE ACEITE (ACCEPTANCE CRITERIA)

| Benchmark / Métrica | Baseline Prototípico | Sprint 1 Target | Sprint 2 Target | Target Final (AETHER v300B) |
| :--- | :--- | :--- | :--- | :--- |
| **SWE-bench Verified** | ~68.0% | 78.0% | 84.0% | **90.0%+** (com Opus 5) |
| **SWE-bench Pro** | ~38.0% | 45.0% | 52.0% | **60.0%+** |
| **Terminal-Bench** | ~45.0% | 58.0% | 68.0% | **75.0%+** |
| **Prompt Cache Hit Rate**| ~50.0% | 75.0% | 88.0% | **>92.0%** |
| **Tempo de Criação de Worktree**| ~1.5s - 4.5s | 0.8s | 0.1s | **< 10 ms** (OverlayFS / Btrfs CoW) |
| **Alocação de Container Subagente**| ~3.5s | 1.0s | 0.2s | **0 ms** (Pre-Warmed Container Pool) |
| **Latência por Chamada FFI**| ~1.5s (gRPC/IPC) | 2.0s | 0.5s | **< 50 ns** (Rust PyO3 Native) |

---

## 3. PLANO FASEADO POR SPRINTS

```mermaid
gantt
    title Cronograma Proposto de Desenvolvimento do AETHER v300B
    dateFormat  YYYY-MM-DD
    section Sprint 0: Foundation & Rust Core
    Hexagonal Core & Domain     :active, s0_1, 2026-08-05, 7d
    Rust CoW Worktrees & PTY    :s0_2, after s0_1, 7d
    section Sprint 1: Real-Time Repair
    In-Loop Repair & Fuzzy Patch:s1_1, after s0_2, 7d
    Architect/Editor & HunkActor:s1_2, after s1_1, 7d
    section Sprint 2: Context & AST
    Exchange Compactor & Codemode:s2_1, after s1_2, 7d
    AST Skeleton Mapping        :s2_2, after s2_1, 7d
    section Sprint 3: Sandboxing & Security
    Pre-Warmed Containers & bwrap:s3_1, after s2_2, 7d
    TaintGate & ExecPolicy AST  :s3_2, after s3_1, 7d
    section Sprint 4: Autonomy & GEPA Evolution
    Conductor System 3 & GEPA   :s4_1, after s3_2, 7d
    SWE-bench 90% Gate Final    :s4_2, after s4_1, 7d
```

---

### 3.1 SPRINT 0: FUNDAÇÃO HEXAGONAL, RUST CORE, COW WORKTREES & TUI MVP
* **Objetivo:** Construir a estrutura base no namespace `src/aether/`, compilar o módulo nativo em Rust via PyO3 (com suporte a CoW Worktrees <10ms e PTY Terminal Harness) e disponibilizar a TUI reativa inicial.
* **Entregáveis Propostos:**
  1. Estruturação do pacote `src/aether/` (`domain/`, `ports/`, `kernel/`, `adapters/`, `agency/`, `tui/`, `core_rs/`).
  2. Implementação das portas remotáveis Pydantic-serializable.
  3. Módulo Rust `aether_core_rs` compilado via Maturin para AST Tree-sitter, `fast_worktree_cow.rs` (<10ms) e `pty_harness.rs`.
  4. Interface TUI reativa MVP em Rich/Textual para exibição de eventos e status.
* **Gate de Aceite:** Passagem nos testes de conformidade de portas, tempo de criação de worktree < 10ms e inicialização da TUI < 200ms.

---

### 3.2 SPRINT 1: REAL-TIME IN-LOOP REPAIR, ARCHITECT/EDITOR, HUNK TRACKER & FUZZY PATCHES
* **Objetivo:** Desenvolver o loop de reparo em tempo real no `run_loop.py`, a separação entre Arquiteto e Editor, o rastreamento de diffs por autor (`HunkTrackerActor`) e a busca aproximada de hunks (`seek_sequence.rs`).
* **Entregáveis Propostos:**
  1. Separação de papéis: **Architect** (plano conceitual) e **Editor** (diffs cirúrgicos).
  2. Mecanismo de **Search/Replace Blocks com Fuzzy Sequence Seeking** (`seek_sequence.rs`) para suporte a deslocamento imprevisto de linhas sem rejeição de patches.
  3. Actor Hunk Tracker (`hunk_tracker.rs`) para rastreamento e atribuição de autoria de alterações (`Agent` vs `User`) com suporte a reversão atômica por hunk.
  4. Re-injeção de stack traces no loop sem invalidar a prefix cache.
* **Gate de Aceite:** Aumento comprovado na taxa de sucesso de edições multi-arquivo em tarefas complexas e reversão atômica de hunks no visualizador TUI.

---

### 3.3 SPRINT 2: GESTÃO DE CONTEXTO, AST MAPPING, TOOL SEARCH & CODEMODE
* **Objetivo:** Otimizar o reaproveitamento de cache de prompt, eliminar o *Dumb Zone* de difusão de atenção e habilitar a execução programática de ferramentas em lote.
* **Entregáveis Propostos:**
  1. **Exchange-Granular Compactor:** Compactação por trocas completas preservando a paridade de mensagens.
  2. **AST Skeleton Mapping (Agentless Pattern):** Injeção de mapa sintático do repositório no topo do prompt.
  3. **Tool Search on Demand & Codemode Execution:** Despacho dinâmico de ferramentas (redução de 37% de tokens) e suporte à execução programática de ferramentas em lote local via `codemode.py`.
* **Gate de Aceite:** **Prompt Cache Hit Rate > 88%** e melhoria estatisticamente significante em repositórios de grande porte.

---

### 3.4 SPRINT 3: SANDBOXING RIGOROSO, PRE-WARMED CONTAINERS & TAINTGATE
* **Objetivo:** Implementar isolamento seguro de execução, pool de containers pré-aquecidos e proteção contra Prompt Injection Indireto.
* **Entregáveis Propostos:**
  1. Sandboxing Híbrido: **Git Worktrees CoW** (<10ms) + **Pre-Warmed Container Pool** (0ms de alocação de subagente) + **Native Sandbox** (`bwrap` no Linux / Restricted Tokens no Windows).
  2. **TaintGate Sanitizer & ExecPolicy Shell AST:** Marcação de entradas externas (`UNTRUSTED_TAINTED`) e verificação de políticas de execução de comandos shell pela AST.
  3. Telemetria do kernel integrada ao Event Bus da TUI com suporte a exportação **OpenTelemetry (OTel)**.
* **Gate de Aceite:** 0% de execução de comandos maliciosos em suítes de teste de segurança e 0ms de espera no alocador de containers.

---

### 3.5 SPRINT 4: CONDUCTOR SYSTEM 3, AUTO-EVOLUÇÃO GEPA & GATE FINAL (90% SWE-BENCH)
* **Objetivo:** Entregar autonomia de longo prazo (*Long-Horizon Autonomy*), auto-otimização reflexiva de prompts e atingir os alvos finais dos benchmarks.
* **Entregáveis Propostos:**
  1. Orquestrador **Conductor System 3** com hibernação durável `FrozenRunState`.
  2. **GEPA Reflective Auto-Evolver & SessionDB Miner:** Pipeline de mineração de trajetórias de erro e otimização textual automatizada de skills/prompts (`src/aether/evolution/`).
  3. **Dataset Exporter:** Sanitização e exportação de trajetórias aprovadas para fine-tuning local (SFT/DPO).
  4. Avaliação completa das suítes **SWE-bench Verified** e **SWE-bench Pro**.
* **Gate de Aceite Final:** **90.0%+ SWE-bench Verified**, **60.0%+ SWE-bench Pro** e **75.0%+ Terminal-Bench**.

---

## 4. GOVERNANÇA DE RELEASES & FLUXO DE ABLAÇÃO

```mermaid
flowchart TD
    PR[Pull Request de Nova Funcionalidade] --> TestSuite[Executa Tests Unitários & Conformidade de Portas]
    TestSuite -->|Falha| Reject1[Rejeição Imediata]
    TestSuite -->|Passa| AblationRun[Executa Benchmark de Ablação em 50+ Instâncias]
    AblationRun --> CheckStats{Aumento de Pass Rate p < 0.05?}
    CheckStats -->|Não| Reject2[Rejeição: Sem Ganho Comprovado]
    CheckStats -->|Sim| CheckCost{Aumento de Latência/Custo Aceitável?}
    CheckCost -->|Não| Reject3[Rejeição: Ineficiência de Recursos]
    CheckCost -->|Sim| Merge[Aprovação & Merge em Production src/aether]
```

A governança quantitativa garante que apenas melhorias estatisticamente comprovadas sejam integradas ao **AETHER v300B**, assegurando excelência técnica e consistência de produto.
