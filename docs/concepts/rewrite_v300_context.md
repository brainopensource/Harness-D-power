---
status: rationale
retrieval: excluded
updated: 2026-08-05
---

Contexto. Encerramos a fase de protótipo do AETHER. Toda a documentação anterior foi arquivada em docs/_archive/. Vamos escrever a documentação V0 do zero, mas informada por tudo que já foi produzido. Antes disso há uma reunião de alinhamento entre os dois Tech Leads.

Sua primeira tarefa é leitura, não escrita. Leia, nesta ordem:

1. docs/00/rewrite_v300_decision_brief.md — o brief da reunião. Comece por ele; ele te diz o que está em disputa e por quê.
2. docs/_archive/rationale/rewrite/ — proposta do Track A (12 documentos, ~57k palavras). Prioridade: measurement_strategy (§1c, §2, §3), blueprint_arquitetura (§1 invariantes, §8c.1 árvore de arquivos), decisoes_adr (Parte IIc — o registro de forks).
3. docs/_archive/rationale/rewrite_b/ — proposta do Track B (5 documentos, ~8k palavras). Prioridade: blueprint_arquitetura_B §2 — a árvore de arquivos até o arquivo individual, que é o artefato mais imediatamente útil que qualquer um dos dois tracks produziu.
4. docs/_archive/competitors_research/tech_lead_A/ — teardowns de Grok Build, Hermes, Hermes Self-Evolution e Claude Code, com 78 propostas numeradas (P1–P78). Leia rewrite_v300_synthesis_amendments.md primeiro: ele mapeia as 78 contra o plano (19 já cobertas, 17 a afiar, 34 lacunas, 8 recusadas).
5. docs/_archive/competitors_research/tech_lead_B/ — os quatro estudos paralelos do Track B.
6. docs/_archive/rationale/rewrite_ab_comparison.md — o confronto direto. Escrito pelo autor do Track A, com o conflito de interesse declarado. Leia com essa ressalva.

O que produzir, e em que ordem:

Antes da reunião — nada de spec. Apenas: liste toda contradição factual que encontrar entre os dois tracks, e toda afirmação numérica que não consiga rastrear até uma medição neste repositório. Já sabemos de algumas (a baseline de ~68% do Track B, as latências de <50ns / <10ms / 0ms, o re-baseline de leaderboard do Track A). Ache o resto. Essa lista é sua entrega pré-reunião.

Depois da reunião, com F1, F2 e F6 decididos:

- Tier 2 — o spec normativo. ~2–3k palavras. Não é resumo do rationale. É a declaração mínima do que é verdade. Regra rígida: se algo pode ser contrato em código, não é prosa aqui. O spec navega; src/aether/ports/ define. Ele entra no orçamento de palavras normativas, então acrescentar N palavras significa deletar N.
- Tier 4 — os contratos executáveis. ports/*.py mesmo que stubs, domain/, o catálogo de eventos gerado com checagem de drift em CI, o conjunto de mock adapters, a suíte de conformidade, cassetes de record/replay. Isso não espera o Tier 2 — comece por aqui.
- Backlog do Sprint 1. Converta cada exit gate dos milestones em item de backlog com critério de aceite verificável. Se um gate for prosa, ele não é um gate.

Orçamento de diagramas: cinco. Grafo de camadas/dependências · sequência do run loop · choke point de dispatch · layout do prefixo de contexto · grafo de dependência de fases. Cada um codifica algo que uma tentativa anterior errou. Além de cinco, apodrecem mais rápido do que informam.

Três coisas que você pode começar segunda-feira, independente do resultado da reunião: o cache de repositórios upstream (B1) — utilitário isolado, sem dependência do AETHER, e é o que destrava qualquer número; o conjunto de mock adapters; e dois cronômetros (criação de worktree, parse-e-valida de AST), que resolvem o F1 com um número em vez de uma preferência.

Duas regras que valem antes de qualquer decisão: um experimento produz um número e uma recomendação, e só vira decisão via ADR com condição de reversão. E um experimento que não mostra nada é registrado como não mostrando nada — essa regra é a que teria salvado o predecessor.

---
Duas coisas que você precisa saber

O arquivamento quebrou os dois gates de CI. 19 links relativos mortos, e a contagem normativa foi de 13.941 para 19.720 contra um teto de 15.000 — documentos que antes estavam isentos mudaram de caminho e voltaram a contar. Não é problema de arquitetura, mas precisa de dono antes do próximo PR. Posso corrigir se quiser.

O brief é enviesado e diz isso. Escrevi as descrições dos forks a partir do Track A, e o Track B não revisou o enquadramento. O apêndice F lista isso junto com o fato de que o re-baseline de leaderboard por trás do F4 é pesquisa minha de uma única sessão, não verificada de forma independente — e o F4 inteiro repousa nele. Se o Tech Lead B corrigir alguma linha na reunião, a correção dele vale mais que o meu texto.