"""Traces do agente no Langfuse.

Um atendimento é um trace. O passo que decide o fluxo é um `agent` (ou um `chain`,
quando o código decide). Cada chamada ao modelo é uma `generation` irmã da ferramenta
que ela pediu — a busca entra como `retriever`, o resto como `tool`.

As gerações são registradas aqui, e não pelo instrumentador automático do SDK da
Anthropic. Aquele span se chama sempre `anthropic.chat` e não existe para o
provedor openai_compat nem para o replay. Um único lugar deixa o nome, os tokens
e o formato da conversa iguais nos três caminhos.

Sem LANGFUSE_PUBLIC_KEY e LANGFUSE_SECRET_KEY o agente roda como antes e não envia nada.
"""
from __future__ import annotations

import atexit
import os
import re
from contextlib import contextmanager, nullcontext
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Iterator

from dotenv import load_dotenv

# O cliente lê as chaves na importação. O .env tem de entrar antes.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

try:
    from langfuse import Langfuse, get_client, propagate_attributes
    from langfuse.types import MaskOtelSpansParams, MaskOtelSpansResult, OtelSpanPatch
    from opentelemetry import trace as otel_trace
except ImportError:  # o resto do projeto funciona sem o pacote instalado
    Langfuse = None  # type: ignore[misc, assignment]
    get_client = None  # type: ignore[assignment]
    propagate_attributes = None  # type: ignore[assignment]
    MaskOtelSpansParams = MaskOtelSpansResult = OtelSpanPatch = None  # type: ignore[misc, assignment]
    otel_trace = None  # type: ignore[assignment]

_NOME_GERACAO: ContextVar[str | None] = ContextVar("lf_nome_geracao", default=None)
_PILHA: ContextVar[tuple] = ContextVar("lf_pilha", default=())

_iniciado = False
_ligado = False
ultimo_trace_id: str | None = None
ultimo_trace_url: str | None = None

_CHAVE = re.compile(r"(?:sk-ant-|sk-lf-|pk-lf-)[A-Za-z0-9_\-]+")
_BEARER = re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]+")
_EMAIL = re.compile(r"\b[\w.+\-]+@[\w.\-]+\.\w+\b")
_TELEFONE = re.compile(r"\b\d{3}[-. ]?\d{3}[-. ]?\d{4}\b")
_CPF = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
_CAMPO_SENSIVEL = re.compile(
    r'("(?:cpf|salario_base|valor_negociado_consulta)"\s*:\s*)(?:"[^"]*"|-?\d+(?:\.\d+)?)',
    re.IGNORECASE,
)


def slug(nome: str) -> str:
    """Nome estável e curto, sem acento, para filtrar no Langfuse."""
    import unicodedata

    texto = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    texto = re.sub(r"[^a-z0-9]+", "-", texto.lower()).strip("-")
    return texto or "passo"


def nome_da_geracao() -> str:
    return _NOME_GERACAO.get() or "gerar-resposta"


@contextmanager
def nome_geracao(nome: str) -> Iterator[None]:
    token = _NOME_GERACAO.set(nome)
    try:
        yield
    finally:
        _NOME_GERACAO.reset(token)


def _tem_trace_aberto() -> bool:
    """Há um span ativo? Não usa get_current_trace_id: ele avisa quando não há span."""
    if otel_trace is None:
        return False
    span = otel_trace.get_current_span()
    return bool(span and span.get_span_context().is_valid)


def habilitado() -> bool:
    _iniciar()
    return _ligado


def flush() -> None:
    if _ligado and get_client is not None:
        get_client().flush()


def url_do_ultimo_trace() -> str | None:
    return ultimo_trace_url


def saida_de_resultado(resultado) -> dict:
    """O que a tabela de traces mostra: a resposta, e o desfecho que a régua lê."""
    return {
        "resposta": resultado.resposta,
        "desfecho": resultado.desfecho,
        "fontes": list(resultado.fontes or []),
    }


def definir_saida(saida) -> None:
    pilha = _PILHA.get()
    if pilha:
        pilha[-1].update(output=saida)


@contextmanager
def observacao(
    tipo: str,
    nome: str,
    entrada,
    *,
    trace_name: str | None = None,
    tags: list[str] | None = None,
    metadata: dict | None = None,
) -> Iterator[Any]:
    """Abre um span e, se for a raiz, um trace. Sem Langfuse, não faz nada."""
    if not habilitado():
        yield None
        return

    langfuse = get_client()
    raiz = not _tem_trace_aberto()
    meta = metadata or {}
    with langfuse.start_as_current_observation(
        as_type=tipo, name=nome, input=entrada, metadata=meta or None,
    ) as obs:
        token = _PILHA.set(_PILHA.get() + (obs,))
        try:
            if raiz:
                _guardar_url(langfuse)
                contexto = propagate_attributes(
                    trace_name=trace_name or nome,
                    tags=["aurora", *(tags or [])],
                    metadata=_meta_curta({"provedor": os.getenv("PROVEDOR", "anthropic"),
                                          "modelo": os.getenv("MODELO", "claude-haiku-4-5-20251001"),
                                          **meta}),
                )
            else:
                contexto = nullcontext()
            with contexto:
                yield obs
        except Exception as erro:
            obs.update(level="ERROR", status_message=f"{type(erro).__name__}: {erro}"[:500])
            raise
        finally:
            _PILHA.reset(token)
    if raiz:
        langfuse.flush()


@contextmanager
def ferramenta(nome: str, entrada, *, tipo: str) -> Iterator[Any]:
    """Ferramenta ou busca, filha do agent/chain que está aberto. Sem trace pai, não vira trace solto."""
    if not habilitado():
        yield None
        return
    langfuse = get_client()
    if langfuse is None or not _tem_trace_aberto():
        yield None
        return
    with langfuse.start_as_current_observation(as_type=tipo, name=nome, input=entrada) as obs:
        try:
            yield obs
        except Exception as erro:
            obs.update(level="ERROR", status_message=f"{type(erro).__name__}: {erro}"[:500])
            raise


def registrar_ferramenta(nome: str, entrada, saida) -> None:
    """A ferramenta que encerra o atendimento (responder, escalar). O args já é o resultado."""
    with ferramenta(slug(nome), entrada, tipo="tool") as obs:
        if obs is not None:
            obs.update(output=saida)


@contextmanager
def geracao(nome: str, modelo_nome: str, mensagens: list, parametros: dict | None = None) -> Iterator[Any]:
    if not habilitado():
        yield None
        return
    langfuse = get_client()
    raiz = not _tem_trace_aberto()
    with langfuse.start_as_current_observation(
        as_type="generation",
        name=nome,
        model=modelo_nome,
        input=mensagens,
        model_parameters=parametros or None,
    ) as gen:
        try:
            if raiz:
                _guardar_url(langfuse)
                contexto = propagate_attributes(
                    trace_name=nome, tags=["aurora"],
                    metadata=_meta_curta({"provedor": os.getenv("PROVEDOR", "anthropic"),
                                          "modelo": modelo_nome}))
            else:
                contexto = nullcontext()
            with contexto:
                yield gen
        except Exception as erro:
            gen.update(level="ERROR", status_message=f"{type(erro).__name__}: {erro}"[:500])
            raise
    if raiz:
        langfuse.flush()


def completar_geracao(
    gen,
    *,
    resposta,
    uso: dict,
    pensamento: str = "",
    origem: str = "ao-vivo",
    modelo_nome: str | None = None,
) -> None:
    if gen is None:
        return
    from comum import medidor

    mensagem: dict = {"role": "assistant", "content": resposta.texto or None}
    if resposta.chamadas:
        mensagem["tool_calls"] = [
            {"id": c.id, "type": "function",
             "function": {"name": c.nome, "arguments": _json(c.args)}}
            for c in resposta.chamadas
        ]
    if pensamento:
        mensagem["reasoning"] = pensamento
    uso_int = {chave: int(valor) for chave, valor in uso.items() if valor}
    if "input" not in uso_int:
        uso_int["input"] = int(uso.get("input", 0))
    if "output" not in uso_int:
        uso_int["output"] = int(uso.get("output", 0))
    custo = {
        "input": _preco(uso_int.get("input", 0), medidor.PRECO_ENTRADA),
        "output": _preco(uso_int.get("output", 0), medidor.PRECO_SAIDA),
    }
    # Tokens de cache e de raciocínio não estão dentro de input/output. O preço do
    # cache segue o de entrada: é o que o placar da disciplina consegue ver.
    for chave in ("cache_read_input_tokens", "cache_creation_input_tokens"):
        if chave in uso_int:
            custo[chave] = _preco(uso_int[chave], medidor.PRECO_ENTRADA)
    if "output_reasoning_tokens" in uso_int:
        custo["output_reasoning_tokens"] = _preco(uso_int["output_reasoning_tokens"], medidor.PRECO_SAIDA)
    campos: dict = {
        "output": [mensagem],
        "usage_details": uso_int,
        "cost_details": custo,
        "metadata": {"origem": origem},
    }
    if modelo_nome:
        campos["model"] = modelo_nome
    gen.update(**campos)


def ler_saida(texto: str) -> tuple[Any, dict]:
    """JSON quando a ferramenta devolveu JSON; senão o texto. Conta os trechos da busca."""
    import json

    try:
        dado = json.loads(texto)
    except json.JSONDecodeError:
        return texto, {}
    meta: dict = {}
    if isinstance(dado, dict) and isinstance(dado.get("resultados"), list):
        meta["quantidade"] = len(dado["resultados"])
        meta["fonte"] = "wiki-aurora"
    return dado, meta


def _preco(tokens: int, usd_por_milhao: float) -> float:
    return round(tokens * usd_por_milhao / 1_000_000, 8)


def _json(dado) -> str:
    import json
    return json.dumps(dado, ensure_ascii=False)


def _meta_curta(metadata: dict) -> dict:
    """propagate_attributes recusa valor cujo JSON passa de 200 caracteres."""
    curto = {}
    for chave, valor in metadata.items():
        texto = str(valor)
        if texto and len(texto) <= 180:
            curto[str(chave)] = texto
    return curto


def _guardar_url(langfuse) -> None:
    global ultimo_trace_id, ultimo_trace_url
    ultimo_trace_id = langfuse.get_current_trace_id()
    ultimo_trace_url = langfuse.get_trace_url(trace_id=ultimo_trace_id)


def _iniciar() -> None:
    global _iniciado, _ligado
    if _iniciado:
        return
    _iniciado = True
    if Langfuse is None:
        return
    publico = os.getenv("LANGFUSE_PUBLIC_KEY", "").strip()
    secreto = os.getenv("LANGFUSE_SECRET_KEY", "").strip()
    if not publico or not secreto:
        return
    os.environ.setdefault("LANGFUSE_TRACING_ENVIRONMENT", "development")
    base = os.getenv("LANGFUSE_BASE_URL", "").strip()
    if base and not os.getenv("LANGFUSE_HOST"):
        os.environ["LANGFUSE_HOST"] = base
    try:
        Langfuse(mask_otel_spans=_mascarar)
        _ligado = bool(get_client().auth_check())
    except Exception as erro:
        _ligado = False
        print(f"Langfuse: não foi possível autenticar ({type(erro).__name__}). O agente segue sem traces.")
        return
    if not _ligado:
        print("Langfuse: chaves recusadas. Confira LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY e LANGFUSE_BASE_URL no .env. "
              "O agente segue sem traces.")
        return
    atexit.register(flush)


def _mascarar(*, params: MaskOtelSpansParams):
    """Tira chave de API, CPF e os campos que a camada já trata como sensíveis, antes do envio."""
    try:
        patches = {}
        for identificador, span in params.spans.items():
            trocas = {}
            for chave, valor in span.attributes.items():
                if not isinstance(valor, str):
                    continue
                novo = _redigir(valor)
                if novo != valor:
                    trocas[chave] = novo
            if trocas:
                patches[identificador] = OtelSpanPatch(set_attributes=trocas)
        if not patches:
            return None
        return MaskOtelSpansResult(span_patches=patches)
    except Exception:
        return None


def _redigir(texto: str) -> str:
    texto = _CHAVE.sub("[REDACTED]", texto)
    texto = _BEARER.sub("Bearer [REDACTED]", texto)
    texto = _EMAIL.sub("[REDACTED EMAIL]", texto)
    texto = _TELEFONE.sub("[REDACTED PHONE]", texto)
    texto = _CPF.sub("[REDACTED CPF]", texto)
    texto = _CAMPO_SENSIVEL.sub(r'\1"[REDACTED]"', texto)
    return texto
