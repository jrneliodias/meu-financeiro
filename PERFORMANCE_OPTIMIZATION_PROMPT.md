# PROMPT PARA OTIMIZAÇÃO DE PERFORMANCE - DJANGO

Você é um **engenheiro sênior de performance em Django**. Avalie meu projeto e proponha **modificações concretas** (com código e migrações) para reduzir o tempo de carregamento da **tela inicial**.

## Contexto do projeto

* **Django 5.1.x**, Python 3.10.
* Banco em **PostgreSQL (Render)** em produção, SQLite em desenvolvimento.
* Apps principais: `registers` (modelos: `Expense`, `Income`, `Category`, `PaymentMethod`, `RecurringExpense`) e `reports`.
* Campos relevantes dos modelos:

```python
# registers/models.py
class Expense(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=3)
    date = models.DateField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # ... outros campos

class Income(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=3)
    date = models.DateField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Category(models.Model):
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=10, choices=[('income', 'Income'), ('expense', 'Expense')])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class PaymentMethod(models.Model):
    name = models.CharField(max_length=100)
    start_billing_day = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

* Ambiente de produção com latência de rede entre web e DB; no Render usando **Internal Database URL**.

## Problema observado

A home (`expense_report` view em `reports/views.py`) dispara **muitas agregações semelhantes** e **N+1** de FKs. Análise do código atual revela:

### Problemas identificados na view atual:

1. **Múltiplas consultas por payment method**: O `ExpenseService.get_expenses_by_category_and_payment_method()` executa um loop para cada payment method e cada mês (12 meses × N payment methods = dezenas de queries).

2. **N+1 em listagens**: Queries como `get_monthly_expenses_by_year()` não usam `select_related()` para category e payment_method.

3. **Consultas repetitivas por período**: O `ExpenseCalculator` e `CategoryExpenseCalculator` fazem consultas similares com diferentes filtros de data.

4. **Falta de índices**: Não há índices compostos para os filtros mais comuns (payment_method + date, category + date).

### Consultas problemáticas típicas geradas:

```sql
-- Repetida para cada payment_method × cada mês
SELECT c.name, SUM(e.amount) AS total_amount
FROM registers_expense e
LEFT JOIN registers_category c ON e.category_id = c.id
WHERE e.date BETWEEN %s AND %s AND e.payment_method_id = %s
GROUP BY c.name
ORDER BY c.name ASC;

-- Séries por mês (múltiplas versões similares)
SELECT DATE_TRUNC('month', i.date) AS month, SUM(i.amount)
FROM registers_income i
WHERE i.date BETWEEN %s AND %s
GROUP BY 1 ORDER BY 1 ASC;

-- N+1 para Category, PaymentMethod
SELECT ... FROM registers_expense WHERE id = ... LIMIT 1;
```

## Objetivo

* **Consolidar** dezenas de consultas em **1–3 consultas agregadas** usando ORM.
* **Eliminar N+1** com `select_related()` / `prefetch_related()`.
* **Adicionar índices** compatíveis com os filtros (igualdade + range).
* Reduzir o TTFB/tempo do DB na home. Meta: **≤ 5 queries** na home e **cada consulta pesada < 100ms** em base realista.
* Opcional: reduzir overhead com `CONN_MAX_AGE` e **cache leve** da view.

## O que quero de você (saída esperada)

### 1. **Revisão do padrão atual**
Identifique onde o código atual gera loops que disparam várias `SUM(...)` por período/método, baseado na estrutura atual do `ExpenseService` e `ExpenseRepository`.

### 2. **Proposta de código otimizado**
Código copiável para substituir a view/serviço que monta a home:

**a) View otimizada (`reports/views.py`):**
```python
def expense_report(request):
    # Sua implementação otimizada aqui
    # Consolidando múltiplas queries em 1-2 consultas agregadas
    pass
```

**b) Consulta agregada única usando ORM:**
- Uma única consulta usando `annotate()` + `TruncMonth` agrupando por `month`, `payment_method__name` e `category__name`.
- Versão alternativa se necessário apenas "por método" ou apenas "por categoria".
- Eliminar loops em Python substituindo por agregação no banco.

**c) Listagem sem N+1:**
```python
# Exemplo de como aplicar select_related/prefetch_related
expenses_queryset = Expense.objects.select_related(
    'category', 'payment_method'
).filter(...).only('fields_needed')
```

### 3. **Migrações de índice**
Arquivo de migration completo (`reports/migrations/XXXX_add_performance_indexes.py`):

```python
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('registers', '0007_recurringexpense_generate_debit_and_more'),
    ]

    operations = [
        # Seus índices aqui
        # Índice composto em Expense(payment_method, date)
        # Índice simples em Expense(date) e Income(date)  
        # Índice composto em Expense(category, date)
    ]
```

### 4. **Ajustes de settings**
```python
# finance/settings.py
DATABASES = {
    'default': {
        # ... configuração existente ...
        'CONN_MAX_AGE': 60,  # Reutilizar conexões
    }
}

# Cache (opcional)
CACHES = {
    'default': {
        # Configuração para django-redis ou cache simples
    }
}
```

### 5. **Decorador de cache na view:**
```python
from django.views.decorators.cache import cache_page

@cache_page(60)  # Cache por 1 minuto
def expense_report(request):
    # implementação
```

### 6. **Critérios de aceite e verificação**
- Código para medir número de queries antes/depois.
- Como rodar `qs.explain(analyze=True, verbose=True, buffers=True, timing=True)` e interpretar se apareceu `Seq Scan` versus uso de índice.
- Comandos prontos para rodar testes/perf localmente.

### 7. **Riscos e compatibilidade**
- Garantir que o agrupamento com `values(...)` não quebre labels exibidos na UI.
- Considerar que `Category.name` não é unique; se necessário, agrupar também por `category_id`.
- Manter ordenações atuais (mês asc, nome do método asc, etc.) ou explicar mudanças.

## Estrutura atual do código (para referência)

**View atual (`reports/views.py:24-88`):**
```python
def expense_report(request):
    # ... código atual que gera múltiplas queries ...
    expense_service = ExpenseService(expense_repository, income_repository, year=selected_year)
    monthly_reports = expense_service.get_expenses_by_category_and_payment_method()
    # ... mais processamento que gera queries adicionais ...
```

**ExpenseService problemático (`reports/services/expense_service.py:279-335`):**
```python
def get_expenses_by_category_and_payment_method(self) -> List[MonthlyExpenseReport]:
    payment_methods = PaymentMethod.objects.all()  # Query 1
    # Loop que gera dezenas de queries:
    for month in range(1, 13):
        for payment_method in payment_methods:  # N × 12 queries
            category_expenses = self.category_calculator.calculate_monthly_expenses(...)
```

**ExpenseRepository com N+1 (`reports/repository/expense_repository.py`):**
```python
def get_monthly_expenses_by_year(self, year, month):
    return (
        Expense.objects
        .filter(date__year=year, date__month=month)
        .order_by('date')  # SEM select_related!
    )
```

## Formato da resposta

Entregue **diffs**/blocos de código completos (view/serviço, migrations, ajustes em `settings.py`) prontos para colar. Nada de pseudo-código. Se algo for incerto, proponha a opção mais padrão/segura.

## Dicas adicionais (aplique diretamente)

* Para séries temporais: `TruncMonth('date')` em `Expense` e `Income`.
* Para dashboards: calcule tudo em uma consulta e depois pivote no Python, em vez de várias queries por período/método.
* Use `.only('campos_que_rendem')` para cortar colunas grandes da listagem.
* Se necessário, proponha **materialized views**/tabela de métricas para contagens pesadas (com cron de refresh), mas priorize primeiro índices e agregação única.

**Entregue a resposta com as seções acima e os blocos de código prontos para uso.**
