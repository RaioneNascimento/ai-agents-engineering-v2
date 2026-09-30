# Agent Decision Record — Equipe Encontro 1

**Caso:** Dúvidas internas do colaborador · Aurora Tecnologia
**Data:** 29/09/2026 · **Integrantes:** a completar pela equipe
**Status:** proposta

## 1. Contexto

A Aurora Tecnologia quer um assistente para dúvidas de colaboradores sobre RH, TI e benefícios. A resposta precisa citar a fonte, usar "não sei" quando a informação não existe ou os documentos se contradizem, e encaminhar ao RH quando a pessoa pergunta se ela tem direito a um benefício. A medição usou os mesmos 10 casos e as mesmas regras de resposta nas três arquiteturas, com o modelo `claude-haiku-4-5`, em 29/09/2026. A e B rodaram uma vez; o agente C rodou três vezes. O corpus tem 12 documentos.

**Ação irreversível do caso:** confirmar a um colaborador que ele é elegível a um benefício, ou cravar um valor de benefício quando as fontes discordam. A elegibilidade (caso c09) é analisada pelo RH.

## 2. Alternativas consideradas

Números do Hands-on 1 (mesmos 10 casos):

| Arquitetura | Acertos | Custo total | p50 | p95 | Custo por acerto | Variou entre execuções? |
|---|---|---|---|---|---|---|
| A · Prompt único | 9/10 | US$ 0.03927 | 1.93 s | 2.74 s | US$ 0.00436 | — |
| B · Workflow | 7/10 | US$ 0.01700 | 2.01 s | 2.90 s | US$ 0.00243 | — |
| C · Agente em loop | 9/10 | US$ 0.06134 | 3.95 s | 7.47 s | US$ 0.00682 | 0 de 10 casos |

Custo total e acertos de C são a média das 3 rodadas. Fontes: `encontro-01/resultados/execucao_20260929_224706_ab.csv` e `encontro-01/resultados/execucao_20260929_224927_c.csv`.

**Onde cada uma errou, e por quê:** A errou só o c07. Os dois valores do vale-refeição estavam no prompt (R$ 45 em `beneficios-vale-refeicao` e R$ 42 em `rh-guia-de-integracao`) e o modelo respondeu R$ 45, citando só o documento de benefícios. B errou três. No c10 a pergunta pede licença-paternidade e inclusão do bebê no plano; o fluxo busca um único tema e devolveu só `rh-licencas`, e o modelo disse que a regra do plano não estava nos documentos. No c04 a resposta veio `nao_sei`, sem citar `rh-ferias`, que descreve a divisão das férias em até três períodos. No c07 a busca fica no tema benefícios e o valor conflitante, que está no guia de RH, não entra no contexto. C acertou 9/10 nas três rodadas, inclusive o c10 (3/3, com `rh-licencas` e `beneficios-plano-de-saude`). Errou o c07 nas três: duas chamadas ao modelo, e a resposta citou só `beneficios-vale-refeicao`. Nenhum desfecho mudou de uma rodada para outra.

## 3. Decisão

Para este corpus, a arquitetura é o prompt único (A): empata com o agente em 9/10, custa menos por acerto e responde mais rápido.

**Escopo de autonomia:** o sistema pode responder com os documentos do prompt, dizer que não sabe e escalar a elegibilidade. Quem decide se uma pessoa tem direito a um benefício é o RH.

**Critério de parada** (se houver agente): a arquitetura escolhida faz uma chamada e para. Na alternativa C, medida nesta rodada, o limite era 6 chamadas ao modelo por pergunta; esgotado o limite, o atendimento escala para o RH.

## 4. Trade-offs assumidos

Cada pergunta leva os 12 documentos no contexto. Com milhares de documentos essa chamada deixa de caber, e o custo deixa de ser o da tabela. O erro do c07 permanece: o modelo escolhe um valor em vez de declarar o conflito, e o agente, com liberdade para buscar de novo, fez o mesmo nas três rodadas. Em troca, a latência típica fica em 1,93 s (p95 de 2,74 s), o caminho é uma chamada só, e a rodada custa US$ 0.03927, contra US$ 0.06134 do agente. O workflow segue com o melhor custo por acerto (US$ 0.00243). Abrimos mão dele porque a pergunta que cruza duas áreas sai errada por construção: o código escolhe um tema e não volta atrás.

## 5. Critério de reversão

Passar para o agente em loop (C, no máximo 6 passos) se, numa nova medição dos mesmos 10 casos, o custo por acerto do prompt único passar de US$ 0.00682, ou se o corpus deixar de caber numa chamada. Reavaliar o workflow se uma suíte maior mostrar que as perguntas de um tema só passaram a ser a regra e o prompt único cair abaixo de 8/10.
