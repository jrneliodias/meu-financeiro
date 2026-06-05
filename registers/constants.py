"""
Constantes semânticas para o módulo registers.

Segue o princípio de eliminar magic numbers e strings,
fornecendo uma única fonte de verdade para valores de configuração.
"""
from django.utils.translation import gettext_noop


class ExpenseConstants:
    """Constantes relacionadas a operações de despesas."""

    RECENT_EXPENSES_LIMIT = 10
    MAX_DESCRIPTION_LENGTH = 100
    MAX_AMOUNT_DIGITS = 10
    AMOUNT_DECIMAL_PLACES = 3
    DEFAULT_INSTALLMENTS_COUNT = 1


class ApiStatus:
    """Códigos de status HTTP para respostas da API."""

    OK = 200
    CREATED = 201
    BAD_REQUEST = 400
    UNAUTHORIZED = 403
    NOT_FOUND = 404
    SERVER_ERROR = 500


class ApiMessages:
    """Mensagens padrão para respostas da API."""

    EXPENSE_NOT_FOUND = gettext_noop("Expense not found")
    UNAUTHORIZED_ACCESS = gettext_noop("Unauthorized access")
    DELETE_SUCCESS = gettext_noop("Expense '%(description)s' deleted successfully")
    AUTOFILL_SUCCESS = gettext_noop("Expense data retrieved for autofill")
    DETAILS_SUCCESS = gettext_noop("Expense details retrieved")
    RECENT_EXPENSES_SUCCESS = gettext_noop("Recent expenses retrieved")
    INVALID_REQUEST = gettext_noop("Invalid request")
