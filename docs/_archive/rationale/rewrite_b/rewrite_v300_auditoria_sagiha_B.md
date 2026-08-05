---
status: rationale
retrieval: excluded
---

# AUDITORIA TÉCNICA EMPÍRICA DA BASE PROTOTÍPICA `src/sagiha/` E PLANO DE TRANSIÇÃO PARA O AETHER v300B
## Análise de Falhas Históricas, Sugestões da Track A & Pontos de Debate na Triagem de Portas

> **Autor:** Tech Lead B (PhD) / Principal Software Architect  
> **Data:** 05 de Agosto de 2026  
> **Target Document:** `docs/rationale/rewrite_b/rewrite_v300_auditoria_sagiha_B.md`  
> **Fontes Primárias:** Competitor Research (`docs/competitors_research/tech_lead_B/`) & Track A Rationale (`docs/rationale/rewrite/`).  
> **Status:** Concluído / Em Conformidade Estrita com a REVISÃO B.

---

## 1. RESUMO EXECUTIVO & DIAGNÓSTICO EMPÍRICO DA BASE ATUAL (`src/sagiha/`)

Esta auditoria apresenta uma avaliação quantitativa e arquitetural da base prototípica `src/sagiha/`, confrontada diretamente com as evidências empíricas dos concorrentes SOTA (Claude Code, Grok Build, Hermes), as lições da literatura (arXiv 2605.18747, arXiv 2602.11988 da ETH Zürich) e os diagnósticos da **Track A** (Tech Lead A).

O objetivo é fundamentar a transição estrutural do ecossistema para o **AETHER v3.0.0B** em `src/aether/`, assegurando o cumprimento das metas globais: **90.0%+ em SWE-bench Verified**, **60.0%+ em SWE-bench Pro** e **75.0%+ em Terminal-Bench**.

---

## 2. DIAGNÓSTICO DAS FALHAS HISTÓRICAS DE MEDIÇÃO (CONTRIBUIÇÃO CRÍTICA DA TRACK A)

A auditoria da Track A identificou quatro defeitos críticos de instrumentação no protótipo original (`s4-harvest-findings.md` D1-D4) que invalidavam medições de benchmark anteriores:

1. **Vazamento do `.pth` do Virtualenv (Defeito D3):** O instalador editável injetava o caminho `.pth` do ambiente virtual para dentro dos containers de teste isolados. Como resultado, os testes executados pelos *gates* rodavam contra o código-fonte vivo do repositório em vez de rodar contra os diffs modificados pelo candidato, gerando pontuações falsas.
2. **Ausência de Canary Tests:** Inexistência de testes canário para verificar se um candidato comprovadamente quebrado causava a reprovação do gate.
3. **Ausência de Rastreamento de Ruído A/A:** Inexistência de medição de oscilação estocástica das próprias APIs de LLM entre chamadas idênticas.

### Recomendação de Solução Incorporada:
* Eliminar installs editáveis dentro dos containers de teste.
* Injetar **Canary Tests** que forçam falhas deliberadas para provar a sensibilidade dos gates.
* Medir o ruído baseline A/A e reportar o **Scaffold-Attributable Lift** (delta emparelhado versus baseline single-shot no mesmo modelo).

---

## 3. TRIAGEM DE PORTAS: COMPARATIVO TRACK A VS. TRACK B

### 3.1 Tabela de Consolidação das Portas Hexagonais (`src/aether/ports/`)

| Arquivo de Porta em `sagiha` | Status no Provedor | Recomendação Track A | Recomendação Track B | **Decisão Proposta para o AETHER v300B** |
| :--- | :--- | :--- | :--- | :--- |
| `policy.py` | Adaptador existia | Reduzir para 8 portas base | Manter & Evoluir (CAR Model) | **MANTER (TCB):** Integrar ao TaintGate (`UNTRUSTED_TAINTED`). |
| `workspace.py` | Adaptador existia | Fundir com WorktreeManager | Manter & Expandir (Rust CoW) | **MANTER:** Suporte nativo PyO3 a OverlayFS e Btrfs CoW (<10ms). |
| `trajectory.py` | Adaptador existia | Manter (SQLite WAL) | Manter (SQLite WAL) | **MANTER:** Base para a hibernação durável `FrozenRunState`. |
| `model.py` | Adaptador existia | Exigir `stream()` nativo | Adicionar Prompt Caching | **REFATORAR:** Adicionar suporte a streaming e marcadores de cache. |
| `tool_registry.py` | Adaptador existia | Versionar contratos de ferramentas | Tool Search on Demand | **REFATORAR:** Integrar versionamento e despacho dinâmico. |
| `code_graph.py` | Adaptador existia | Deferir para fase posterior | Migrar para Rust PyO3 | **REFATORAR (Rust Core):** Tree-sitter em Rust (`ast_treesitter.rs`). |
| `indexer.py` | Adaptador existia | FTS5 + Tree-sitter | Multi-thread Rust Walk | **REFATORAR (Rust Core):** Percurso paralelo e FTS5 em Rust. |
| `search.py` | Adaptador existia | Deferir para fase posterior | MMR Reranking ($\lambda=0.7$) | **REFATORAR:** BM25 + `sqlite-vec` + MMR Reranking. |
| `sandbox.py` | Adaptador existia | Rootless Podman | Containers 0ms + `bwrap` | **REFATORAR:** Pre-Warmed Container Pool + `bwrap` nativo. |
| `memory.py` | Adaptador existia | Deferir para fase posterior | Memória de 3 Trilhas | **REFATORAR:** 3 Trilhas + Auto Dream Consolidation Worker. |
| `evaluator.py` | Adaptador existia | Gate TCB Isolado | Gate de Ablação Estatística | **MANTER (TCB):** Admissão por ablação estatística ($p < 0.05$). |
| `governor.py` | Adaptador existia | Spend/Lease Governor | Spend/Budget Governor | **MANTER:** Leases e controle de orçamento monetário. |
| `advisory.py` | Apenas Stub | **ELIMINAR** (Regra A-010) | **ELIMINAR** (Regra do Aluguel) | **ELIMINAR DE IMEDIATO** |
| `lsp.py` | Apenas Stub | **ELIMINAR** (Regra A-010) | Substituir por Tree-sitter | **ELIMINAR:** Tree-sitter Rust substitui o LSP. |
| `orchestrator.py` | Apenas Stub | **ELIMINAR** (Regra A-010) | Substituir por Conductor | **SUBSTITUIR:** Conductor System 3 Multi-Agent Engine. |
| `meta_improver.py` | Apenas Stub | **ELIMINAR** (Regra A-010) | Substituir por GEPA | **SUBSTITUIR:** GEPA Reflective Auto-Evolver em `evolution/`. |

---

## 4. PONTOS DE DEBATE NA AUDITORIA (PARA A REUNIÃO DE TECH LEADS)

### DEBATE: Regra de Entrada de Novas Portas (Regra A-010) vs. Disponibilização Antecipada
* **Opção A (Tech Lead A):** Regra estrita **A-010**: Reduzir a base para 8 portas essenciais (`ModelProvider`, `Workspace`, `ToolRegistry`, `PolicyEngine`, `TrajectoryStore`, `Evaluator`, `Indexer`, `ResourceGovernor`). Nenhuma nova porta pode ser criada sem a entrega simultânea do seu primeiro adaptador funcional e testes de conformidade.
* **Opção B (Tech Lead B):** Manter 9 portas base incluindo `Memory` e `CodeGraph` desde a fundação para estruturar os contratos de auto-evolução reflexiva e AST desde o primeiro momento.
* **Proposta de Consenso:** Aceitar a **Regra A-010 da Track A**: iniciar o `src/aether/ports/` com 8 portas essenciais e promover `Memory` e `CodeGraph` no exato momento em que seus adaptadores nativos Rust forem acoplados (Sprint 0 / Sprint 1).

---

## 5. METRICAS ALVO E CRITÉRIOS DE ABLAÇÃO ESTATÍSTICA

| Benchmark / Métrica | Baseline Prototípico (`sagiha`) | Meta Target Final (AETHER v300B) | Mecanismo-Chave Garantidor |
| :--- | :--- | :--- | :--- |
| **SWE-bench Verified** | ~68.0% - 72.0% | **90.0%+** (com Opus 5) | In-Loop Repair + Architect/Editor Split + AST Rust Pre-Validation |
| **SWE-bench Pro** | ~38.0% - 40.0% | **60.0%+** | AST Skeleton Mapping + Exchange Compactor + Conductor System 3 |
| **Terminal-Bench** | ~45.0% | **75.0%+** | PTY Pseudo-Terminal Harness + ExecPolicy Shell AST + TUI Reativa |
| **Prompt Cache Hit Rate**| ~50.0% | **> 92.0%** | 3 Marcadores de Cache Fixos + Compactor por Troca Granular |
| **Tempo de Worktree Clone**| ~1.5s - 4.5s | **< 10 ms** | Fast CoW Worktree Engine (OverlayFS / Btrfs `reflink` em Rust) |
| **Alocação de Container Subagente**| ~3.5s | **0 ms** | Pre-Warmed Container Pool em Background |
| **Latência por Chamada FFI**| ~1.5ms - 5.0ms (gRPC) | **< 50 ns** | Direct Memory Sharing via Rust `PyO3` C-ABI |

---

## 6. REGRA DE ACEITAÇÃO POR ABLAÇÃO ESTATÍSTICA ($p < 0.05$)
Nenhuma nova funcionalidade, heurística de prompt ou ferramenta será aceita sem passar pelo seguinte protocolo de validação:
1. Execução em no mínimo **50 instâncias independentes de teste** dos benchmarks de referência.
2. Demonstração de aumento estatisticamente significante na taxa de sucesso ($p < 0.05$ via teste t de Student / teste bicaudal de permutação).
3. Manutenção ou redução do custo monetário por tarefa concluída.
4. Cumprimento estrito da regra `require_tests_unmodified` e aprovação nos **Canary Tests** contra vazamentos de ambiente.
