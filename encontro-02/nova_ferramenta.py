"""TODO 4 — Construir do zero: consultar_rede_credenciada.     (CONTRATO E IMPLEMENTAÇÃO)

Nas ferramentas 1 a 5, a implementação veio pronta e vocês escreveram o contrato.
Aqui não tem nada pronto: vocês escrevem as duas coisas.

O pedido do time de Benefícios
------------------------------
"Todo dia alguém pergunta se tal hospital ou laboratório atende pelo plano. A resposta
está na nossa planilha da rede credenciada, no Google Sheets. Queremos que o assistente
consulte a planilha."

O sistema: a planilha
---------------------
    SHEETS.ler("planilha-rede-credenciada", "prestadores")

devolve o mesmo formato da API do Google Sheets (spreadsheets.values.get):

    {"spreadsheetId": "planilha-rede-credenciada",
     "range": "prestadores!A1:L31",
     "majorDimension": "ROWS",
     "values": [
        ["prestador", "tipo", "especialidades", "cidade", "uf", "bairro", "telefone",
         "atende_24h", "situacao", "codigo_operadora", "valor_negociado_consulta",
         "observacao_interna"],                                            <- cabeçalho
        ["Hospital Jacarandá Paulista", "Hospital", "clínica geral; ...", "São Paulo", ...],
        ...
     ]}

Tudo vem como texto, e a planilha é mantida à mão desde 2021. Olhem os dados antes
de escrever qualquer linha:

    python encontro-02/nova_ferramenta.py          (a partir da raiz: imprime a planilha inteira)

Passo a passo
-------------
  4a. IMPLEMENTAÇÃO: escrevam consultar_rede_credenciada(). Decidam os parâmetros.
      Devolvam um dicionário com a lista de prestadores em "resultados" (um dicionário
      por prestador). Chaves fora de "resultados" também podem voltar ao modelo,
      se o contrato declarar (ex.: a fonte).
  4b. CONTRATO: preencham CONTRATO (descrição, schema, saída), como nos TODOs 1 a 3.
      Os parâmetros do schema precisam bater com os da função.
  4c. TESTE: assim que CONTRATO["parametros"] deixar de ser None, a ferramenta entra
      no catálogo do agente sozinha. Os casos c16 e c17 dependem dela:

          python encontro-02/rodar.py --casos c16 c17 --detalhe

Perguntas para decidir
----------------------
  - Que parâmetros o modelo precisa para chegar ao prestador certo? Quais valores aceitar?
  - "Campinas", "campinas" e "CAMPINAS " são a mesma cidade. Quem resolve isso: o modelo
    ou o código?
  - A planilha tem prestadores descredenciados e em negociação. O modelo deveria vê-los?
  - São Paulo tem mais de dez prestadores. Quantos voltam para o contexto?
  - Quais colunas nunca deveriam entrar no contexto? (O placar tem uma coluna para isso.)
  - Como o agente cita a planilha como fonte?
  - E erros: cidade sem prestador? Tipo que não existe?
"""
import unicodedata

from ferramentas import ErroDeFerramenta   # para devolver erros legíveis ao modelo (veja ferramentas.py)
from sistemas import PlanilhaGoogle

SHEETS = PlanilhaGoogle()
PLANILHA_ID = "planilha-rede-credenciada"
ABA = "prestadores"


def normalizar(texto: str) -> str:
    """'  São Paulo ' -> 'sao paulo'. Minúsculas, sem acento, sem espaço nas pontas."""
    sem_acento = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return " ".join(sem_acento.lower().split())


# ======================================================================
# TODO 4a — a implementação
#
# Troquem a assinatura pelos parâmetros que vocês decidirem (com tipos e valores
# padrão) e escrevam o corpo. Esqueleto sugerido:
#   1. ler a planilha com SHEETS.ler(PLANILHA_ID, ABA)
#   2. transformar cada linha num dicionário (cabeçalho -> valor)
#   3. filtrar (normalizar() ajuda)
#   4. devolver {"resultados": [...], ...}
# ======================================================================
TIPOS = {
    "hospital": "hospital",
    "laboratorio": "laboratorio",
    "clinica": "clinica",
    "pronto_socorro": "pronto-socorro",
}
LIMITE = 5


def _linhas() -> list[dict]:
    valores = SHEETS.ler(PLANILHA_ID, ABA)["values"]
    cabecalho, linhas = valores[0], valores[1:]
    return [{coluna: (linha[i] if i < len(linha) else "") for i, coluna in enumerate(cabecalho)}
            for linha in linhas]


def _radicais(texto: str) -> set:
    """'exames de sangue' e 'exame de sangue' compartilham o começo de cada palavra."""
    return {palavra[:5] for palavra in normalizar(texto).replace(";", " ").split() if len(palavra) > 2}


def _especialidade_bate(pedido: str, especialidades: str) -> bool:
    alvo = _radicais(pedido)
    return not alvo or alvo <= _radicais(especialidades)


def consultar_rede_credenciada(cidade: str, tipo: str = "", especialidade: str = "",
                               atende_24h: bool | None = None) -> dict:
    """Busca prestadores ativos na planilha da rede credenciada."""
    if not str(cidade).strip():
        raise ErroDeFerramenta("cidade_vazia", "Informe a cidade.",
                               como_corrigir="repita a chamada com o nome da cidade")
    if tipo and tipo not in TIPOS:
        raise ErroDeFerramenta("tipo_invalido", "'tipo' não é um valor aceito.",
                               recebido=tipo, aceitos=list(TIPOS),
                               como_corrigir="repita com tipo igual a um dos valores aceitos")

    cidade_alvo = normalizar(cidade)
    tipo_alvo = TIPOS.get(tipo, "")
    encontrados = []
    for linha in _linhas():
        if normalizar(linha.get("situacao", "")) != "ativo":
            continue
        if normalizar(linha.get("cidade", "")) != cidade_alvo:
            continue
        if tipo_alvo and normalizar(linha.get("tipo", "")) != tipo_alvo:
            continue
        if especialidade and not _especialidade_bate(especialidade, linha.get("especialidades", "")):
            continue
        if atende_24h is not None and (normalizar(linha.get("atende_24h", "")) == "sim") != atende_24h:
            continue
        encontrados.append({"id": PLANILHA_ID, **linha})

    aviso = ("Encerre chamando a ferramenta responder, não em texto solto. "
             "Em fontes, cite exatamente planilha-rede-credenciada. "
             "Na resposta, indique só prestadores desta lista.")
    if len(encontrados) > LIMITE:
        aviso = (f"Há {len(encontrados)} prestadores ativos. Voltaram os {LIMITE} primeiros. "
                 "Refine com tipo, especialidade ou atende_24h. " + aviso)
        encontrados = encontrados[:LIMITE]
    elif not encontrados:
        aviso = "Nenhum prestador ativo encontrado para essa busca. " + aviso

    return {"id": PLANILHA_ID, "resultados": encontrados, "aviso": aviso}


# ======================================================================
# TODO 4b — o contrato (mesmo formato de contratos.py)
# ======================================================================
CONTRATO = {
    "descricao": (
        "Consulta a planilha da rede credenciada do plano de saúde da Aurora: hospital, "
        "laboratório, clínica e pronto-socorro que atendem pelo plano numa cidade. "
        "Devolve só prestadores ativos (descredenciado e em negociação não aparecem), "
        "no máximo 5, com o id planilha-rede-credenciada. "
        "Depois do resultado, encerre com a ferramenta responder e coloque esse id em fontes. "
        "Não escreva a resposta final em texto solto. "
        "A cidade é comparada sem diferenciar maiúsculas, acento ou espaço. "
        "Use atende_24h true quando a pessoa precisa de atendimento 24 horas. "
        "Use tipo e especialidade para não devolver a cidade inteira. "
        "Não use para valor, prazo ou como pedir o benefício (consultar_regra_beneficio), "
        "nem para saber se um colaborador tem direito ao plano (verificar_elegibilidade_beneficio). "
        "Não use para políticas de RH nem para dúvidas de TI."
    ),
    "parametros": {
        "type": "object",
        "properties": {
            "cidade": {"type": "string", "maxLength": 80,
                       "description": "A cidade do atendimento, como o colaborador falou. Ex.: 'Campinas'."},
            "tipo": {"type": "string", "enum": ["hospital", "laboratorio", "clinica", "pronto_socorro"],
                     "description": "O tipo de prestador. Omita para buscar todos os tipos ativos na cidade."},
            "especialidade": {"type": "string", "maxLength": 120,
                              "description": "O que a pessoa precisa. Ex.: 'exame de sangue', 'cardiologia'."},
            "atende_24h": {"type": "boolean",
                           "description": "true quando o atendimento precisa funcionar 24 horas."},
        },
        "required": ["cidade"],
        "additionalProperties": False,
    },
    "saida": ["id", "prestador", "tipo", "especialidades", "cidade", "bairro", "telefone",
              "atende_24h", "situacao", "aviso"],
}


NOME = "consultar_rede_credenciada"


if __name__ == "__main__":   # olhar os dados antes de escrever a ferramenta
    for linha in SHEETS.ler(PLANILHA_ID, ABA)["values"]:
        print(linha)
