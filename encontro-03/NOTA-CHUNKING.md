# Nota de chunking · Equipe: Raione Nascimento

Caso: (x) Aurora  ( ) domínio próprio: ____________

## 1. O que adotamos

Estratégia de chunking: estrutura (corte por seção), com prefixo "Título > Seção".
Busca (vetor, BM25 ou híbrida): vetor.
Tratamento de versões e de autoridade: nenhum. Vigência e autoridade ficaram desligadas.
k (quantos trechos o agente recebe): 3.

## 2. Por quê

| configuração | normal | excecao | conflito | termo-exato | autoridade | total |
|---|---|---|---|---|---|---|
| base: tamanho 400 · vetor | 7/7 (0) | 2/2 (1) | 2/3 (3) | 3/3 (1) | 1/1 (0) | 15/16 (5) |
| Estrutura default | 6/7 (0) | 2/2 (0) | 2/3 (3) | 3/3 (0) | 1/1 (0) | 14/16 (3) |
| Tamanho 800 - Sobreposição 0 | 6/7 (0) | 2/2 (0) | 2/3 (3) | 3/3 (0) | 1/1 (0) | 14/16 (3) |
| Estrutura - Tamanho 800 - Sobreposição 0 | 5/7 (0) | 2/2 (0) | 1/3 (3) | 3/3 (0) | 1/1 (0) | 12/16 (3) |
| Estrutura - Tamanho 800 - Sobreposição 0 - hibrida | 6/7 (0) | 2/2 (0) | 1/3 (3) | 3/3 (0) | 1/1 (0) | 13/16 (3) |

Formato: achou/casos (contaminados).

A base acha 15 de 16, mas contamina 5. Estrutura default e tamanho 800 com sobreposição 0 empatam no melhor placar: 14 de 16 achados e 3 contaminados. As duas zeram a contaminação de exceção (1 para 0) e de termo exato (1 para 0), ao custo de um caso normal (7/7 para 6/7). Ficamos com a estrutura. Nas linhas seguintes o total cai: estrutura com tamanho 800 fica em 12/16, e a mesma com busca híbrida em 13/16; conflito passa de 2/3 para 1/3. Com estratégia estrutura, tamanho e sobreposição não entram no corte, então o ganho que se sustenta é o da linha Estrutura default. Os 3 contaminados que sobram estão todos em conflito.

## 3. O que ela não resolve

S1, "A Aurora oferece previdência privada?". Causa: sem resposta. O placar não mede essa categoria (S1, S2 e S3). A busca trouxe licenças remuneradas, seguro de vida e plano odontológico; a resposta esperada é não saber e encaminhar para Benefícios. Nenhuma configuração de chunking ou de busca resolve: o "não sei" tem que ser decidido pelo agente, quando os trechos não sustentam a pergunta.

No que o placar mede, o buraco que resta é conflito: 2/3 achados e 3 contaminados nas duas melhores linhas. A página de 2024 continua competindo com a vigente.

## 4. O que a ingestão precisa garantir

- **titulo**, no cabeçalho da página. Quem publica a política preenche na publicação e revisa quando o título muda. Se estiver errado, o prefixo "Título > Seção" rotula o chunk com outro assunto e a busca vetorial ordena pelo rótulo errado.
- **Seções em markdown** (`##`). O mesmo autor escreve; o chunker lê o título da seção. Sem heading, ou com dois assuntos no mesmo bloco, o trecho certo se mistura com outro. Foi o que a base fez em exceção: 1 contaminado em 2 casos.
- **politica e vigencia**. Esta configuração não filtra por eles. Quem publica uma versão nova preenche os dois no cabeçalho. Se a vigência estiver velha ou vazia, a página antiga continua tão elegível quanto a atual, que é o 3/3 contaminado de conflito.
- **autoridade** (`oficial` ou não). Quem classifica a página preenche na ingestão. Não usamos o filtro, mas se uma FAQ ou um resumo for marcado como oficial, o valor informal entra no mesmo índice que a política (o caso do vale-refeição).
