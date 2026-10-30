# Nota de avaliação · Encontro 5

**Equipe:**
**Integrantes:**
**Domínio:** caso Aurora

> Uma página. As tabelas das seções 1, 2 e 4 saem prontas do Passo 6 do notebook 02. O que vale nota é o
> raciocínio das seções 3, 4 e 5: números que aguentam o teste do ruído e uma decisão defendida.

## 1 · Golden set do grupo

8 perguntas do banco de produção, com o gabarito que o grupo escreveu a partir da wiki. O arquivo
`encontro-05/golden-equipe.json` está no fork.

| id | pergunta | desfecho | fontes | contém | não contém |
|---|---|---|---|---|---|
| B16 | Qual o valor do auxílio-creche? | responder | beneficios-auxilio-creche | 600 |  |
| B03 | Voltei de viagem ontem. Até quando preciso lançar as despesas? | responder | fin-viagens-e-reembolso | 10 dias corridos / dez dias corridos | 10 dias úteis / 5 dias úteis |
| B04 | Qual a diária máxima de hotel numa viagem para uma capital? | responder | fin-viagens-e-reembolso | 450 | 320 |
| B07 | Em quanto tempo preciso compensar as horas do banco de horas? | responder | rh-jornada-e-banco-de-horas | 6 meses / seis meses | 5 dias úteis |
| B13 | Meu filho nasceu há 40 dias. Ainda dá para incluir ele no plano de saúde sem carência? | responder | beneficios-plano-de-saude | novembro |  |
| B23 | Valeu pela ajuda, até mais! | responder |  |  |  |
| B22 | Sou contratado como PJ. Tenho direito ao vale-refeição? | escalar |  |  |  |
| B18 | Qual o horário do refeitório do escritório? | nao_sei |  |  |  |

**Um gabarito difícil de decidir:** B13. A página `beneficios-plano-de-saude` (§5.2–5.3) diz que a inclusão sem carência vale até 30 dias corridos após o nascimento; depois disso, só na janela de novembro, e com carência. Com 40 dias, o prazo já passou. Duas leituras: `responder`, porque a wiki dá a regra, ou `escalar`, porque a pessoa pergunta do filho dela. Ficamos com `responder` e o texto `novembro`: o plano publica a regra geral, ao contrário do auxílio-creche, que veda confirmar elegibilidade fora do RH. O `contem` é o marco da seção 5.3. Não usamos `nao_contem` com "sem carência", porque uma resposta certa também escreve essa expressão ao negá-la.

## 2 · Placar

Golden set da turma (25 casos) mais o do grupo (8), 5 amostras de cada.

| versão | acerto (IC 90%) | pass^5 | instáveis | US$/acerto | p95 (s) | loops |
|---|---|---|---|---|---|---|
| v1 · produção | 72% (61%–83%) | 58% | 11/33 | 0.00078 | 9.7 | 12% |
| v2 · prompt enxuto (PR #42) | 75% (63%–87%) | 70% | 4/33 | 0.00046 | 5.7 | 2% |
| v3 · modelo mais barato | 98% (94%–100%) | 94% | 2/33 | 0.00022 | 4.4 | 0% |

A v3 lidera em acerto, confiabilidade (pass^5), custo por acerto, latência e loops. Os intervalos da v1 e da v2 se sobrepõem: os 3 pontos entre elas cabem no ruído.

## 3 · Regressão ou ruído

- **Ruído (teste A/A da v1):** o acerto variou até 9 pontos entre duas rodadas da mesma versão.
- **PR #42:** diferença de +3% (IC 90%: −5% a +12%). Veredito: não dá para afirmar. Casos que mudaram: pioraram P1, R1 e G5 (todos a 0%); melhoraram C2, B13 e B22.
- **Modelo barato:** diferença de +25% (IC 90%: +14% a +38%). Veredito: melhora. Casos que mudaram: piorou N1 (100% → 40%); melhoraram S1, S2, P1, R1, R2, G5, G6, B13, B23, B22 e B18.

**Os casos do grupo mudaram alguma conclusão?** Sozinhos, os 8 casos dariam **melhora** à v2 (+22%, IC 90%: +3% a +45%), puxada por B13 e B22. Com 8 casos o intervalo é frágil, e na suíte de 33 a diferença (+3%) é menor que o ruído de 9 pontos. Não deixamos esses 8 casos derrubar o veredito da suíte inteira.

## 4 · SLOs e gate

| SLO | por que esse número (e quem na Aurora concordaria) |
|---|---|
| acerto ≥ 80% | Benefício errado chega ao colaborador. Orçamento de erro de 20% (1 em 5). RH e jurídico concordariam; abaixo disso o time para de lançar e conserta. |
| custo por acerto ≤ US$ 0,002 | Teto folgado: a v1 já custa US$ 0,00078. Financeiro aceita. Não separa as versões; o placar é que mostra a v3 cerca de 3,5 vezes mais barata por acerto. |
| p95 ≤ 10 s | 95% dos colaboradores esperam no máximo 10 s. Operações e o time de pessoas. A v1 passa por 0,3 s (9,7 s). |

| SLO | v1 · produção | v2 · prompt enxuto (PR #42) | v3 · modelo mais barato |
|---|---|---|---|
| acerto ≥ 80% | **FALHA** (72%) | **FALHA** (75%) | passa (98%) |
| custo_por_acerto ≤ US$ 0.00200 | passa (US$ 0.00078) | passa (US$ 0.00046) | passa (US$ 0.00022) |
| p95_segundos ≤ 10.0s | passa (9.7s) | passa (5.7s) | passa (4.4s) |

**A decisão:** a v3 vai para produção. É a única que passa no gate, e a melhora de +25 pontos (IC 90%: +14 a +38) é maior que o ruído de 9. Rejeitamos a v2: +3 pontos cabe no ruído, e P1, R1 e G5 foram a 0%. P1 é uma saudação; G5 é um "não sei" (curso de inglês) que o prompt enxuto passou a responder. A média da v3 esconde o N1, licença-paternidade (20 dias), que caiu de 100% para 40%. Mudaríamos de ideia se esse tipo de benefício com número não voltasse a acertar nas cinco amostras, ou se uma suíte maior fizesse o intervalo da v3 cruzar o zero.

## 5 · Um atendimento por dentro

**Caso, versão e amostra:** P1, v2, amostra 1. Pergunta: "Bom dia! Você consegue me ajudar com dúvidas de RH e TI?" Esperado: `responder`.
**O que a cascata mostra:** um único passo, sem busca. A chamada ao modelo levou 1,09 s, 454 tokens e US$ 0,00008, e encerrou com `nao_sei`.
**Diagnóstico:** o problema aparece no passo do agente, no prompt enxuto, antes da busca. O PR #42 trata uma saudação de escopo como pergunta sem resposta na wiki. Consertaria o prompt para responder a esse tipo de abertura, sem exigir página citada.
