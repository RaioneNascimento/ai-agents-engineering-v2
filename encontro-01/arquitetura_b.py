"""Arquitetura B — workflow determinístico.   (COMPLETE OS TODOs 1 e 2)

O fluxo está escrito no código. O modelo só faz duas tarefas pequenas:
classificar a pergunta e redigir a resposta.

    pergunta ──► classificar ──► tema?
                                   ├── "elegibilidade" ──► escalar (sem chamar o modelo)
                                   └── "rh" | "ti" | "beneficios"
                                          ──► buscar(tema, pergunta) ──► [ modelo + 3 documentos ] ──► resposta

Quem decide o próximo passo é o CÓDIGO, não o modelo.
"""
from comum import modelo
from comum.resultado import Resultado
from ferramentas import buscar, formatar
from politica_de_resposta import FORMATO_JSON, REGRAS

CATEGORIAS = ("rh", "ti", "beneficios", "elegibilidade")


# --------------------------------------------------------------------------
# TODO 1 — o classificador
#
# Escreva o prompt de sistema que faz o modelo responder com UMA das
# CATEGORIAS acima, e nada mais. Dicas:
#   - diga o que entra em cada categoria (ex.: "ti: notebook, senha, VPN...");
#   - "elegibilidade" é quando a pessoa pergunta se ELA tem direito a algo;
#   - peça a resposta em minúsculas, sem pontuação.
# --------------------------------------------------------------------------
PROMPT_CLASSIFICADOR = """Classifique a pergunta de um colaborador da Aurora Tecnologia.

Responda com uma única palavra, em minúsculas, sem pontuação e sem explicação.
A palavra tem de ser exatamente uma destas: rh, ti, beneficios, elegibilidade.

elegibilidade: a pessoa pergunta se ELA tem direito a um benefício.
  Exemplos: "tenho direito ao auxílio-creche?", "sou elegível?", "posso receber esse benefício?".
  Não use esta categoria para perguntas sobre a regra em geral
  (prazo, valor, como incluir um dependente). Essas vão em beneficios.

ti: notebook, equipamento, seguro do aparelho, senha, conta bloqueada,
  VPN, acesso remoto, instalação de software, sistema que não abre.
  Se a pessoa está em casa mas o problema é o equipamento ou o acesso ao sistema, a categoria é ti.

beneficios: plano de saúde, inclusão de dependente, vale-refeição, auxílio-creche
  (regras do benefício, sem perguntar se a pessoa tem direito).

rh: férias, jornada, banco de horas, trabalho remoto, licenças, integração.

Se a pergunta mistura dois temas, escolha o tema da primeira informação pedida.
Se não tiver certeza, responda rh.
"""


def classificar(pergunta: str) -> str:
    resposta = modelo.chamar([modelo.mensagem_do_usuario(pergunta)],
                             sistema=PROMPT_CLASSIFICADOR, max_tokens=10)
    categoria = resposta.texto.strip().lower()

    for palavra in categoria.replace(",", " ").split():
        limpa = palavra.strip(".,:;!\"'`")
        if limpa in CATEGORIAS:
            return limpa
    return "rh"


def resolver(pergunta: str) -> Resultado:
    categoria = classificar(pergunta)

    if categoria == "elegibilidade":
        return Resultado(
            "escalar",
            [],
            "Essa análise de elegibilidade é feita pelo RH. Vou encaminhar o seu caso.",
        )

    docs = buscar(categoria, pergunta)
    if not docs:
        return Resultado("nao_sei", [], "Não encontrei essa informação nos documentos deste tema.")

    documentos = "\n\n".join(formatar(doc) for doc in docs)
    sistema = f"{REGRAS}\n\n{FORMATO_JSON}\n\nDocumentos disponíveis:\n\n{documentos}"
    resposta = modelo.chamar([modelo.mensagem_do_usuario(pergunta)], sistema=sistema)
    return Resultado.de_json(resposta.texto)
