"""Arquitetura A — prompt único.            (PRONTA: só rode e observe)

Uma chamada ao modelo. Todos os documentos vão no contexto, e o modelo
faz tudo de uma vez: entende a pergunta, acha a informação e responde.

    pergunta ──► [ modelo + todos os documentos ] ──► resposta

Perguntas para observar:
  - Quantos tokens de entrada cada pergunta gasta? Por quê?
  - O que aconteceria com essa arquitetura se o corpus tivesse 5.000 documentos?
"""
from comum import modelo, rastreio
from comum.resultado import Resultado
from ferramentas import carregar_corpus, formatar
from politica_de_resposta import FORMATO_JSON, REGRAS


def resolver(pergunta: str) -> Resultado:
    with rastreio.observacao(
        "chain", "responder-com-contexto", pergunta,
        trace_name="responder-com-contexto", tags=["workflow", "prompt-unico"],
    ):
        with rastreio.nome_geracao("redigir-resposta"):
            documentos = "\n\n".join(formatar(doc) for doc in carregar_corpus())
            sistema = f"{REGRAS}\n\n{FORMATO_JSON}\n\nDocumentos disponíveis:\n\n{documentos}"
            resposta = modelo.chamar([modelo.mensagem_do_usuario(pergunta)], sistema=sistema)
            resultado = Resultado.de_json(resposta.texto)
        rastreio.definir_saida(rastreio.saida_de_resultado(resultado))
        return resultado
