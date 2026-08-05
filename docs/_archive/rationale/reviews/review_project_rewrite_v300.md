---
status: rationale
retrieval: excluded
---

# DOCUMENTO DE DIRETRIZES E PROMPT DE AUDITORIA: Transição para o Aether v3.0.0 (Harness SOTA & AGI Autônomo)

> **Arquivo Target:** `docs/rationale/reviews/review_project_rewrite_v300.md`  
> **Branch Active:** `rewrite_aether_v300_foundation`  
> **Papel:** Prompt / RFP (Request for Proposal & Architecture Review) destinado ao **Tech Lead / Arquitetura de Software**.  
> **Diretriz de Tom:** Orientado estritamente a **sugestões, análises exploratórias, comparações sem viés e documentação de decisões (ADRs)**. Evitar dogmatismos ou imposições rígidas, solicitando ao Tech Lead um parecer totalmente honesto, de nível *Billion-Dollar Scale LLM Orchestrator & Coding Agent Design*.

---

## 1. OBJETIVO DO PROCESSO & FILOSOFIA DE DESIGN

O objetivo deste trabalho é guiar a transição da base prototípica atual (`src/sagiha/`) para a versão final de produção, batizada de **Aether v3.0.0**.

### 1.1 Princípios Fundamentais
* **Desacoplado, SOLID, Clean e Sem Bloat:** Construir um Harness extremamente leve, de alta performance e modular, eliminando abstrações prematuras ou bibliotecas pesadas desnecessárias.
* **Paper Trail & Padronização de Documentação (`docs/rationale/rewrite/`):** Todas as análises, especificações e Registros de Decisão de Arquitetura (ADRs) devem ser gravadas na pasta dedicada `docs/rationale/rewrite/` com o prefixo padronizado `rewrite_v300_<nome-informativo>.md`.
* **Fatos sobre Opiniões (Benchmarking & Ablações):** Nenhuma alteração de mecanismo deve ser promovida para a produção sem que uma ablação com validação estatística comprove ganho real de taxa de resolução ou redução substancial de latência/custo.
* **Do Coder Agent à AGI Autônoma:** O Harness deve nascer como um agente de código de ponta (capaz de competir com Claude Code CLI, Hermes, Aider e OpenHands) e evoluir naturalmente para uma infraestrutura autônoma de longo horizonte (*long-horizon execution*), auto-evolutiva e resiliente a falhas.

---

## 2. AUDITORIA BASEADA EM FATOS: ESTADO ATUAL DE `src/sagiha/`

Para embasar a revisão do Tech Lead, a inspeção empírica do código em `src/sagiha/` revela os seguintes pontos de atenção a serem diagnosticados e reavaliados para a v3:

### 2.1 Estrutura de Portas e Adaptadores (`ports/` e `adapters/`)
* **Situação Atual:** Existem 17 portas definidas em `src/sagiha/ports/` (e.g. `workspace.py`, `trajectory.py`, `policy.py`, `orchestrator.py`, `lsp.py`, `advisory.py`).
* **Fatos & Pontos de Análise:**
  - Nem todas as portas possuem adaptadores de produção completos. Por exemplo, `orchestrator.py` e `lsp.py` possuem suporte limitado ou nulo.
  - A porta `advisory.py` e a camada `src/sagiha/aoi/` (Auxiliary Optimization Intelligence) contêm esqueletos iniciais (`__init__.py` vazio ou stubs).
  - *Sugestão para o Tech Lead:* Investigar quais portas devem ser consolidadas, simplificadas ou temporariamente removidas (regra de "pagar aluguel" do contrato) para manter o núcleo enxuto na V3.

### 2.2 Ciclo de Execução e Loop de Reparo (`src/sagiha/agency/run_loop.py`)
* **Situação Atual:** O `RunLoop.run()` executa as etapas de chamada à LLM e despacho de ferramentas em um loop principal de passos.
* **Fatos & Pontos de Análise:**
  - Historicamente, a avaliação rigorosa das portas de teste (`GateEvaluator`) ocorria ao final da execução do loop.
  - Agentes SOTA (como Claude Code, OpenHands e Aider) devem seu alto desempenho ao **loop de reparo interno em tempo real**: quando um teste ou linter falha, a stack trace de erro é imediatamente alimentada de volta no contexto da LLM como uma nova observação sem destruir a prefix cache.
  - *Sugestão para o Tech Lead:* Avaliar como arquitetar o loop de reparo dentro do `RunLoop` ou da camada de agência, garantindo que o agente aprenda com falhas intermediárias antes de encerrar a tarefa.

### 2.3 Desempenho Local & I/O
* **Situação Atual:** Grande parte da indexação de arquivos, buscas por regex e manipulação de contexto roda em Python síncrono/assíncrono tradicional.
* **Fatos & Pontos de Análise:**
  - Em repositórios de grande porte (100k+ linhas de código), a indexação e a busca de símbolos via AST podem sobrecarregar o processo Python.
  - *Sugestão para o Tech Lead:* Comparar e documentar os ganhos de isolar componentes de I/O e computação pesada local atrás de portas limpas, podendo usar Rust (`PyO3`) ou Go (via IPC/gRPC) onde for estritamente comprovado o gargalo de CPU/memória.

---

## 3. INSPIRAÇÃO E REFERÊNCIAS HISTÓRICAS (BIBLIOTECA DE PESQUISA)

As propostas presentes nos documentos de pesquisa em `docs/rationale/` e `docs/implementation/` servem como **fonte de inspiração e contexto histórico**, e **não como regras absolutas**. O Tech Lead tem total autonomia para aceitar, modificar ou rejeitar essas propostas com base em análises comparativas:

1. **`harness_research_2026_briefing.md`:**
   - *Conceitos:* Ciclo DMARTIC (9 estágios), separação estrita Gerador-Avaliador (Anthropic 3-agent pattern), controle estatístico via AOI, protocolos MCP e Agent-to-Agent (A2A).
2. **`go_rust_greenfield_harness.md`:**
   - *Conceitos:* Arquitetura poliglota (Microkernel em Rust para AST/Worktrees, TUI em Go/TS, Inteligência/Sidecar em Python), modelo de autorização de capacidades (CAR).
3. **`agi_evolution_path.md`:**
   - *Conceitos:* Camada *Conductor* (System 3) para orquestração de missões de semanas, hibernação durável de processos via `FrozenRunState`, consolidação ativa de memória episodica.
4. **`next_gen_architecture_specs.md`:**
   - *Conceitos:* `TaintGate` para segurança contra pontes de injeção de prompt em dados externos, `ExchangeCompactor` baseado em tokens e trocas inteiras, pipeline de exportação de traces para fine-tuning local (SFT/DPO).
5. **`planning_final_sprint_rev2.md` & `planning_future_sprints.md`:**
   - *Conceitos:* Divisão entre Papéis de Arquitetura e Edição (Architect/Editor split), busca e localização sintática antes de editar (Agentless pattern), medições em SWE-bench Verified/Pro e Terminal-Bench.

---

## 4. GUIA DE EXPLORAÇÃO ARQUITETURAL PARA O TECH LEAD (SUGESTÕES DE ANÁLISE)

Solicitamos ao Tech Lead uma análise profunda, sem viés e fundamentada nos seguintes tópicos-chave de engenharia:

### A. Seleção de Linguagens & Estratégia de Comunicação Poliglota (Polyglot vs. Monoglot Architecture)
* **Pergunta de Pesquisa:** Dado que possuímos desenvolvedores seniores nas três linguagens (Python, Rust e Go), qual a melhor combinação arquitetural para um sistema comercial de alto desempenho?
* **Dimensões a Comparar:**
  1. *Estratégias Monolíticas (Tudo em Python vs. Tudo em Rust vs. Tudo em Go):* Quais os limites práticos de velocidade de desenvolvimento, manutenção de ecossistema de LLMs e performance de runtime de cada uma?
  2. *Estratégia Híbrida Poliglota (Python Async Orchestrator + Rust Core via PyO3 + Go TUI/CLI):* Como balancear agilidade em Python com performance de máquina em Rust e UX/concorrência em Go?
  3. *Mecanismos de Comunicação Inter-Linguagens e Latência:*
     - **In-Process FFI / C-Bindings (`PyO3` / Maturin):** Latência em nanossegundos e transferência de memória *Zero-Copy* entre Python e Rust.
     - **IPC / Sockets / gRPC / Protobuf:** Latência em milissegundos sobre conexões de rede locais. Qual o impacto na taxa de throughput?
  4. *Empacotamento Comercial & Proteção de Código Fechado (IP Protection):*
     - Como distribuir o software para venda comercial protegendo a propriedade intelectual contra engenharia reversa? (Uso de **Nuitka** para compilação C/C++ do Python + Rust, **PyOxidizer** ou binários compilados nativos em **Go/Rust**).
* **Entregável Esperado:** `docs/rationale/rewrite/rewrite_v300_decisoes_runtime.md`

### B. Mecanismo de Edição de Código & Resiliência a Falhas (Claude Code vs. Aider vs. OpenHands)
* **Pergunta de Pesquisa:** Como garantir que o agente aplique alterações de código multi-arquivo sem corromper arquivos ou perder tempo de janela de contexto?
* **Caminhos a Avaliar:**
  - *Search/Replace Blocks (Aider style):* Blocos cirúrgicos de substituição vs. edições baseadas no escopo da AST.
  - *Rollback & Verificação Sintática Contínua:* Validação determinística de sintaxe (`ast.parse`) e restauração automática antes da execução de suítes pesadas.
  - *Architect/Editor Split:* Separar um modelo "Arquiteto" (sem acesso a ferramentas, focado em propor o plano) de um modelo "Editor" (focado apenas na aplicação cirúrgica de diffs).
* **Entregável Esperado:** `docs/rationale/rewrite/rewrite_v300_mecanismo_edicao.md`

### C. Gestão de Janela de Contexto, Compacidade e Mapeamento de Repositório
* **Pergunta de Pesquisa:** Como evitar a atenuação de atenção (*loss in the middle*) e otimizar a taxa de acerto no cache de tokens da LLM (*prompt cache hit rate*)?
* **Caminhos a Avaliar:**
  - *Exchange-Granular Compactor:* Compactador que opera em nível de trocas completas de mensagens/ferramentas, preservando a paridade de blocos do provedor e mantendo os tokens iniciais e finais intactos.
  - *AST Skeleton Mapping:* Envio de assinaturas e estruturas sintáticas geradas via Tree-sitter em vez do arquivo integral no início da tarefa (padrão Agentless/AutoCodeRover).
  - *Episodic Memory & Knowledge Net:* Separação entre dados estruturados (código) e memórias episódicas não-estruturadas com expiração bi-temporal.
* **Entregável Esperado:** `docs/rationale/rewrite/rewrite_v300_contexto_memoria.md`

### D. Segurança, Sandboxing e Proteção contra Contaminação (TaintGate)
* **Pergunta de Pesquisa:** Como garantir autonomia de execução sem expor a máquina do usuário ou permitir injeção de instruções maliciosas?
* **Caminhos a Avaliar:**
  - *Isolamento de Execução:* Git Worktrees para concorrência zero-copy vs. Podman/Docker rootless para sandboxing de comandos.
  - *TaintGate:* Rastreamento de dados provenientes de fontes externas (issue trackers, READMEs de terceiros, outputs de web search) marcados como não-confiáveis para prevenir ataques OWASP LLM.
* **Entregável Esperado:** `docs/rationale/rewrite/rewrite_v300_seguranca_sandbox.md`

### E. Caminho para Autonomia de Longo Prazo e Evolução AGI (Conductor System 3)
* **Pergunta de Pesquisa:** Como desenhar a transição de um agente de código simples para um orquestrador autônomo de missões de longa duração?
* **Caminhos a Avaliar:**
  - *Hibernação Durável de Processos:* Congelamento e restauração de estado (`FrozenRunState`) imune a reboots de máquina, quedas de rede e limitação de taxa de APIs.
  - *Síntese Autônoma de Ferramentas (Tool Synthesis):* Capacidade do agente detectar tarefas repetitivas e gerar/compilar suas próprias ferramentas de suporte.
  - *Dataset Exporter (SFT / DPO):* Curadoria de trajetórias bem-sucedidas para exportação e fine-tuning contínuo de modelos locais (Qwen/DeepSeek).
* **Entregável Esperado:** `docs/rationale/rewrite/rewrite_v300_autonomia_agi.md`

---

## 5. CHECKLIST DE ENTREGÁVEIS & ESTRUTURA DE ARQUIVOS (`docs/rationale/rewrite/`)

O Dev Tech Lead deverá criar a pasta **`docs/rationale/rewrite/`** e gravar todos os relatórios e especificações seguindo rigorosamente o padrão de nomes `rewrite_v300_<nome-informativo>.md`:

1. **`docs/rationale/rewrite/rewrite_v300_auditoria_sagiha.md`**  
   - Diagnóstico completo da base `src/sagiha/` classificando componentes em **Manter**, **Refatorar** ou **Eliminar/Substituir**.

2. **`docs/rationale/rewrite/rewrite_v300_decisoes_runtime.md`**  
   - Análise comparativa sem viés sobre a linguagem final/estratégia poliglota, latência de comunicação (FFI/PyO3 vs. IPC/gRPC) e empacotamento comercial fechado.

3. **`docs/rationale/rewrite/rewrite_v300_decisoes_adr.md`**  
   - Compilação dos Registros de Decisão de Arquitetura (ADRs) abordando edições resilientes, gestão de contexto, segurança e sandboxing.

4. **`docs/rationale/rewrite/rewrite_v300_blueprint_arquitetura.md`**  
   - Blueprint completo da arquitetura do **Aether v3.0.0**, especificando interfaces, portas hexagonais, diagrama de componentes e fluxos de dados.

5. **`docs/rationale/rewrite/rewrite_v300_roadmap_sprints.md`**  
   - Plano de execução faseado em sprints, definindo critérios quantitativos de aceite em benchmarks (SWE-bench Verified/Pro, Aider Polyglot, Terminal-Bench) e portas de ablação.
