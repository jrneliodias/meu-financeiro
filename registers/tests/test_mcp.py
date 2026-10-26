import json
import os
from decimal import Decimal
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase

from registers.models import Category, Expense, Income, PaymentMethod


@mock.patch.dict(os.environ, {"MCP_TOKEN": "segredo", "MCP_USER": "nelio"})
class McpTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("nelio", password="x")
        self.cat = Category.objects.create(name="Mercado", type="expense")
        Category.objects.create(name="Salario", type="income")
        self.pm = PaymentMethod.objects.create(name="Crédito - Nubank", start_billing_day=1)

    def rpc(self, method, params=None, token="segredo", id=1):
        body = {"jsonrpc": "2.0", "method": method, "params": params or {}}
        if id is not None:
            body["id"] = id
        return self.client.post(f"/mcp/{token}/", json.dumps(body), content_type="application/json")

    def call(self, name, **args):
        r = self.rpc("tools/call", {"name": name, "arguments": args}).json()["result"]
        return r["isError"], r["content"][0]["text"]

    def test_token_errado_404_e_get_405(self):
        self.assertEqual(self.rpc("tools/list", token="errado").status_code, 404)
        self.assertEqual(self.client.get("/mcp/segredo/").status_code, 405)

    def test_initialize_list_e_notificacao(self):
        self.assertEqual(self.rpc("initialize").json()["result"]["serverInfo"]["name"], "meu-financeiro")
        self.assertEqual(len(self.rpc("tools/list").json()["result"]["tools"]), 3)
        self.assertEqual(self.rpc("notifications/initialized", id=None).status_code, 202)

    def test_criar_despesa_e_duplicada(self):
        args = dict(description="Mercado X", amount=45.5, date="2026-10-20",
                    category="mercado", payment_method="crédito - nubank")
        err, _ = self.call("criar_despesa", **args)
        self.assertFalse(err)
        e = Expense.objects.get()
        self.assertEqual((e.user, e.amount, e.category, e.payment_method), (self.user, Decimal("45.5"), self.cat, self.pm))
        err, text = self.call("criar_despesa", **args)
        self.assertTrue(err)
        self.assertEqual(Expense.objects.count(), 1)
        self.assertFalse(self.call("criar_despesa", force=True, **args)[0])
        self.assertEqual(Expense.objects.count(), 2)

    def test_categoria_invalida_lista_opcoes(self):
        err, text = self.call("criar_despesa", description="a", amount=1, date="2026-10-20",
                              category="Salario", payment_method="Crédito - Nubank")
        self.assertTrue(err)
        self.assertIn("Mercado", text)

    def test_criar_receita(self):
        self.assertFalse(self.call("criar_receita", description="Pgto", amount=100, date="2026-10-05", category="Salario")[0])
        self.assertEqual(Income.objects.get().amount, Decimal("100"))
