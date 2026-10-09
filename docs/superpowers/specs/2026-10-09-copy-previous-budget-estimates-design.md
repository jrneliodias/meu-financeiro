# Design: Reaproveitar Estimativas do Mês Anterior

**Data:** 2026-10-09
**Status:** Aprovado

## Objetivo

Na página de estimativas (`/register/estimativas/`), mostrar abaixo das estimativas do mês selecionado a lista de estimativas do **último mês anterior que tenha estimativas**, permitindo copiar para o mês selecionado:

- **Copiar selecionadas** — só as linhas marcadas, com o valor que estiver no campo (editável por linha).
- **Copiar todas** — todas as linhas copiáveis, ignorando os checkboxes, mas respeitando os valores editados.

Fora de escopo (decidido no brainstorming): sobrescrever estimativas já existentes no mês de destino; escolher manualmente o mês de origem.

## Regras de Negócio

1. **Mês de origem** = mês mais recente estritamente anterior ao selecionado (`(year, month) < (selected_year, selected_month)`) que tenha ao menos uma estimativa do usuário. Ex.: em 10/2026, com 09/2026 vazio e 08/2026 preenchido, a origem é 08/2026. Atravessa ano (01/2027 → 12/2026).
2. Sem mês de origem → a seção não é renderizada.
3. Uma linha é **copiável** se a categoria ainda não tem estimativa no mês de destino. Linhas não copiáveis aparecem numa lista somente leitura com o aviso "Já existe neste mês".
4. Linhas copiáveis vêm **marcadas** e com o **valor do mês de origem** preenchido.
5. Nunca sobrescreve: no POST, categorias que já existem no destino (inclusive criadas entre o GET e o POST) são ignoradas e contadas como `skipped`.
6. O mês de origem é **recalculado no servidor** no POST; o cliente só envia `category_id`, `selected` e `amount`. `category_id` que não pertence ao mês de origem do usuário é descartado silenciosamente (proteção contra POST forjado).
7. Valor deve ser `>= 0` (mesma regra do formulário de criação).
8. Criação é atômica: um único `bulk_create` (o Django já o executa dentro de uma transação). Linhas repetidas com o mesmo `category_id` no POST são deduplicadas (vale a última).

## Fluxo do Usuário

1. Usuário abre `/register/estimativas/?month=10&year=2026`.
2. Abaixo da tabela de outubro, vê "Estimativas de 08/2026" com checkbox + campo de valor por linha copiável, e as já existentes em outubro listadas como somente leitura.
3. Ajusta valores, desmarca o que não quer e clica **Copiar selecionadas para 10/2026** — ou clica **Copiar todas**.
4. Redireciona para `?month=10&year=2026` com a mensagem "N estimativa(s) copiada(s)." (+ "M ignorada(s) porque já existiam." quando `M > 0`). Se nada foi selecionado: mensagem de erro "Nenhuma estimativa selecionada.".

## Arquitetura

Segue o padrão Repository → Service → View já usado em `RecentIncomeRepository`/`RecentIncomeService`. Cada unidade tem uma responsabilidade; dependências injetadas pelo construtor (com default), facilitando teste.

```
budget_estimate_list (GET)  ─┐
                             ├─► BudgetEstimateCopyService ─► BudgetEstimateRepository ─► CategoryBudgetEstimate
budget_estimate_copy (POST) ─┘          ▲
        │                               │ items: list[CopyItem]
        └── EstimateCopyFormSet ────────┘ (valida linhas; view interpreta "selecionadas" vs "todas")
```

### Arquivos criados

| Arquivo | Responsabilidade |
|---|---|
| `registers/repository/budget_estimate_repository.py` | `BudgetEstimateRepository` — **só acesso a dados**. |
| `registers/services/budget_estimate_copy_service.py` | `BudgetEstimateCopyService` + dataclasses `CopyCandidates`, `CopyItem`, `CopyResult` — **regras de negócio** da cópia. |
| `registers/templates/register/components/estimate_copy_section.html` | Partial da seção de cópia. |
| `registers/tests/test_budget_estimate_copy.py` | Testes de repository, service e views. |

### Arquivos alterados

| Arquivo | Alteração |
|---|---|
| `registers/forms.py` | + `EstimateCopyRowForm` e `EstimateCopyFormSet = formset_factory(EstimateCopyRowForm, extra=0)`. |
| `registers/views.py` | `budget_estimate_list` passa `copy_candidates` e `copy_formset` ao template; + view `budget_estimate_copy` (POST). |
| `registers/urls.py` | + `path("estimativas/copiar/", views.budget_estimate_copy, name="budget_estimate_copy")`. |
| `registers/templates/register/budget_estimate_list.html` | `{% include "register/components/estimate_copy_section.html" %}` após a tabela/estado vazio. |
| `registers/services/__init__.py`, `registers/repository/__init__.py` | Exportar `BudgetEstimateCopyService` e `BudgetEstimateRepository` nos respectivos `__all__`. |
| `locale/pt_BR/LC_MESSAGES/django.po`, `locale/en/LC_MESSAGES/django.po` | Strings novas; rodar `compilemessages`. |

## Detalhes de Backend

### `BudgetEstimateRepository`

```python
class BudgetEstimateRepository:
    def get_for_month(self, user, month, year) -> QuerySet[CategoryBudgetEstimate]:
        """Estimativas do mês, com category, ordenadas por nome da categoria."""

    def find_latest_month_before(self, user, month, year) -> Optional[tuple[int, int]]:
        """(month, year) mais recente estritamente anterior que tenha estimativas, ou None.
        Filtro: Q(year__lt=year) | Q(year=year, month__lt=month); order_by('-year', '-month')."""

    def get_category_ids_for_month(self, user, month, year) -> set[int]:

    def bulk_create(self, estimates: list[CategoryBudgetEstimate]) -> list[CategoryBudgetEstimate]:
```

### `BudgetEstimateCopyService`

```python
@dataclass(frozen=True)
class CopyItem:
    category_id: int
    amount: Decimal

@dataclass(frozen=True)
class CopyCandidates:
    source_month: int
    source_year: int
    copyable: list[CategoryBudgetEstimate]        # categoria ainda não existe no destino
    already_existing: list[CategoryBudgetEstimate]  # categoria já existe no destino

@dataclass(frozen=True)
class CopyResult:
    created: int
    skipped: int

class BudgetEstimateCopyService:
    def __init__(self, repository: Optional[BudgetEstimateRepository] = None): ...

    def get_copy_candidates(self, user, month, year) -> Optional[CopyCandidates]:
        """None se não houver mês de origem."""

    def copy_estimates(self, user, month, year, items: list[CopyItem]) -> CopyResult:
        """Recalcula a origem; descarta category_id fora da origem; ignora (skipped)
        categorias já existentes no destino; deduplica por category_id; cria o restante com um bulk_create."""
```

O service **não sabe** se os itens vieram de "selecionadas" ou "todas" — essa interpretação é da view (quem lê o formulário).

### Formulário

```python
class EstimateCopyRowForm(forms.Form):
    category_id = forms.IntegerField(widget=forms.HiddenInput)
    selected = forms.BooleanField(required=False)
    amount = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0)

EstimateCopyFormSet = formset_factory(EstimateCopyRowForm, extra=0)
```

Prefixo fixo do formset: `copy`. `initial` montado a partir de `CopyCandidates.copyable` (`selected=True`, `amount` da origem).

### View `budget_estimate_copy` (`@login_required`, `@require_http_methods(["POST"])`)

1. Lê `month`/`year` do POST (destino).
2. Faz bind de `EstimateCopyFormSet(request.POST, prefix='copy')`. Inválido → `messages.error(_('Invalid values. Check the amounts and try again.'))` + redirect.
3. `copy_all = request.POST.get('action') == 'all'`; monta `items` com as linhas em que `copy_all or selected`.
4. `items` vazio → `messages.error(_('No estimates selected.'))` + redirect.
5. Chama `service.copy_estimates(...)`; monta mensagem com `ngettext` para `created` e, se `skipped > 0`, para `skipped`.
6. Redirect para `reverse('budget_estimate_list') + f'?month={month}&year={year}'`.

### View `budget_estimate_list` (alteração)

No contexto, adiciona `copy_candidates = service.get_copy_candidates(user, selected_month, selected_year)` e, quando houver, `copy_formset` com `initial` das linhas copiáveis.

## Template (`estimate_copy_section.html`)

- Só renderiza `{% if copy_candidates %}`.
- Título: "Estimativas de {source_month}/{source_year}" (mesmo formato `M/AAAA` já usado na página).
- Um `<form method="post" action="{% url 'budget_estimate_copy' %}">` com `csrf_token`, `management_form`, hidden `month`/`year` de destino.
- Por linha copiável: checkbox + nome da categoria em `<label for>` do checkbox; campo de valor com `aria-label` "Valor para {categoria}".
- Linhas `already_existing`: nome, valor e o texto "Já existe neste mês", sem inputs.
- Se `copyable` for vazio: texto "Todas as categorias já existem neste mês." e nenhum botão.
- Dois botões `type="submit"`: `name="action" value="selected"` → "Copiar selecionadas para M/AAAA"; `name="action" value="all"` → "Copiar todas".
- Classes Tailwind no mesmo estilo da tabela existente (`bg-zinc-700/50`, `text-gray-400`, botões `bg-blue-600` / `bg-zinc-600`).

## Testes (`registers/tests/test_budget_estimate_copy.py`)

Rodar localmente com SQLite: `DATABASE_URL= python manage.py test registers.tests.test_budget_estimate_copy`.

### `BudgetEstimateRepositoryTest`
- `test_find_latest_month_before_skips_empty_months` — estimativa em 08/2026; busca antes de 10/2026 → `(8, 2026)`.
- `test_find_latest_month_before_crosses_year` — estimativa em 12/2026; busca antes de 01/2027 → `(12, 2026)`.
- `test_find_latest_month_before_ignores_same_and_future_months` — estimativas em 10/2026 e 11/2026; busca antes de 10/2026 → `None`.
- `test_find_latest_month_before_ignores_other_users` — só outro usuário tem 08/2026 → `None`.
- `test_get_category_ids_for_month` — retorna o set de `category_id` do mês, só do usuário.

### `BudgetEstimateCopyServiceTest`
- `test_get_copy_candidates_returns_none_without_source`.
- `test_get_copy_candidates_splits_copyable_and_existing` — origem 08 com A e B; destino 10 já tem B → `copyable=[A]`, `already_existing=[B]`, `source=(8, 2026)`.
- `test_copy_estimates_creates_with_given_amounts` — item A com valor ajustado → estimativa em 10/2026 com o valor ajustado; `CopyResult(created=1, skipped=0)`.
- `test_copy_estimates_skips_existing_categories` — B já existe no destino → não duplica, valor original de B preservado, `skipped=1`.
- `test_copy_estimates_ignores_categories_not_in_source` — item com categoria fora da origem → nada criado.
- `test_copy_estimates_without_source_creates_nothing` — sem origem → `CopyResult(0, 0)`.

### `BudgetEstimateCopyViewTest`
- `test_list_shows_copy_section_from_latest_month` — GET em 10/2026 com dados em 08/2026 → contexto tem `copy_candidates` com origem (8, 2026) e resposta contém o nome da categoria.
- `test_list_hides_copy_section_without_source` — `copy_candidates is None`.
- `test_copy_selected_creates_only_checked_rows` — POST com A marcada e B desmarcada → só A criada; redirect para `?month=10&year=2026`.
- `test_copy_all_ignores_checkboxes` — POST com `action=all` e nenhuma marcada → A e B criadas com os valores enviados.
- `test_copy_with_nothing_selected_shows_error` — `action=selected` sem marcar → nada criado, mensagem de erro.
- `test_copy_rejects_negative_amount` — valor `-1` → nada criado, mensagem de erro.
- `test_copy_requires_login` — anônimo → redirect para login, nada criado.
- `test_copy_get_not_allowed` — GET em `/copiar/` → 405.

## Internacionalização

Strings novas (pt_BR / en) em `django.po`: título "Estimates from %(month)s/%(year)s", "Copy selected to %(month)s/%(year)s", "Copy all", "Already exists this month", "All categories already exist this month.", "Amount for %(category)s", "No estimates selected.", "Invalid values. Check the amounts and try again.", plurais de "%(count)s estimate copied." e "%(count)s skipped because it already existed.". Sem entradas fuzzy/vazias; rodar `compilemessages`.
