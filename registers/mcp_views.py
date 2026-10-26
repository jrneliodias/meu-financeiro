"""Servidor MCP minimo (Streamable HTTP, sem estado) para cadastrar movimentacoes pelo chat do Claude.

Autenticacao: token secreto na URL (/mcp/<MCP_TOKEN>/) e usuario fixo MCP_USER.
"""
import hmac
import json
import os
from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib.auth.models import User
from django.http import Http404, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Category, Expense, Income, PaymentMethod
from .services.expense_service import ExpenseService
from .services.income_service import IncomeService

PROTOCOL_VERSION = "2025-06-18"

_COMMON = {
    "description": {"type": "string", "description": "Descricao curta (max 100 caracteres)"},
    "amount": {"type": "number", "description": "Valor em reais, positivo"},
    "date": {"type": "string", "description": "YYYY-MM-DD"},
    "category": {"type": "string", "description": "Nome exato de uma categoria de listar_opcoes"},
}
TOOLS = [
    {
        "name": "listar_opcoes",
        "description": "Lista categorias (de despesa e de receita) e formas de pagamento. Chame antes de cadastrar.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "criar_despesa",
        "description": "Cadastra uma despesa. Se ja existir uma igual (mesma data, valor e descricao) avisa em vez de duplicar; use force=true para cadastrar mesmo assim.",
        "inputSchema": {
            "type": "object",
            "properties": {
                **_COMMON,
                "payment_method": {"type": "string", "description": "Nome exato de uma forma de pagamento"},
                "force": {"type": "boolean"},
            },
            "required": ["description", "amount", "date", "category", "payment_method"],
        },
    },
    {
        "name": "criar_receita",
        "description": "Cadastra uma receita.",
        "inputSchema": {
            "type": "object",
            "properties": _COMMON,
            "required": ["description", "amount", "date", "category"],
        },
    },
]


def _lookup(model, name, **filters):
    obj = model.objects.filter(name__iexact=name.strip(), **filters).first()
    if not obj:
        valid = ", ".join(model.objects.filter(
            **filters).values_list("name", flat=True))
        raise ValueError(f"'{name}' nao existe. Opcoes: {valid}")
    return obj


def _parse(args):
    try:
        amount = Decimal(str(args["amount"]))
        when = date.fromisoformat(args["date"])
    except (KeyError, InvalidOperation, ValueError):
        raise ValueError("amount ou date invalido (date = YYYY-MM-DD)")
    if amount <= 0:
        raise ValueError("amount deve ser positivo")
    desc = args.get("description", "").strip()[:100]
    if not desc:
        raise ValueError("description obrigatoria")
    return desc, amount, when


def _call_tool(name, args, user):
    if name == "listar_opcoes":
        return json.dumps({
            "categorias_despesa": list(Category.objects.filter(type="expense").values_list("name", flat=True)),
            "categorias_receita": list(Category.objects.filter(type="income").values_list("name", flat=True)),
            "formas_pagamento": list(PaymentMethod.objects.values_list("name", flat=True)),
        }, ensure_ascii=False)

    if name == "criar_despesa":
        desc, amount, when = _parse(args)
        category = _lookup(Category, args.get("category", ""), type="expense")
        method = _lookup(PaymentMethod, args.get("payment_method", ""))
        if not args.get("force") and Expense.objects.filter(
                user=user, date=when, amount=amount, description__iexact=desc).exists():
            raise ValueError(
                "Ja existe uma despesa igual. Confirme com o usuario e use force=true se for outra.")
        e = ExpenseService().create_single_expense(user, {
            "description": desc, "amount": amount, "date": when,
            "category": category, "payment_method": method})
        return f"Despesa #{e.pk} cadastrada: {desc} R$ {amount} em {when} ({category}, {method})"

    if name == "criar_receita":
        desc, amount, when = _parse(args)
        category = _lookup(Category, args.get("category", ""), type="income")
        i = IncomeService().create_income(user, {
            "description": desc, "amount": amount, "date": when, "category": category})
        return f"Receita #{i.pk} cadastrada: {desc} R$ {amount} em {when} ({category})"

    raise KeyError(name)


def _handle(msg, user):
    """Retorna a resposta JSON-RPC, ou None para notificacoes."""
    mid, method, params = msg.get("id"), msg.get(
        "method"), msg.get("params") or {}
    if mid is None:
        return None

    def ok(result):
        return {"jsonrpc": "2.0", "id": mid, "result": result}

    if method == "initialize":
        return ok({
            "protocolVersion": params.get("protocolVersion", PROTOCOL_VERSION),
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "meu-financeiro", "version": "1.0"},
        })
    if method == "ping":
        return ok({})
    if method == "tools/list":
        return ok({"tools": TOOLS})
    if method == "tools/call":
        try:
            text, is_error = _call_tool(params.get(
                "name"), params.get("arguments") or {}, user), False
        except KeyError:
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": "tool desconhecida"}}
        except ValueError as exc:
            text, is_error = str(exc), True
        return ok({"content": [{"type": "text", "text": text}], "isError": is_error})
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "method not found"}}


@csrf_exempt
@require_POST
def mcp(request, token):
    expected = os.getenv("MCP_TOKEN", "")
    # 404 (nao 403) para nao revelar que o endpoint existe
    if not expected or not hmac.compare_digest(token, expected):
        raise Http404
    user = User.objects.filter(username=os.getenv("MCP_USER", "")).first()
    if not user:
        raise Http404
    try:
        msg = json.loads(request.body)
    except ValueError:
        return JsonResponse({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}})
    # ponytail: sem batch JSON-RPC; o Claude envia uma mensagem por POST
    if not isinstance(msg, dict):
        return JsonResponse({"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "invalid request"}})
    reply = _handle(msg, user)
    return HttpResponse(status=202) if reply is None else JsonResponse(reply)
