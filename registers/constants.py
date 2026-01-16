"""
Constantes semânticas para o módulo registers.

Segue o princípio de eliminar magic numbers e strings,
fornecendo uma única fonte de verdade para valores de configuração.
"""


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

    EXPENSE_NOT_FOUND = "Despesa não encontrada"
    UNAUTHORIZED_ACCESS = "Acesso não autorizado"
    DELETE_SUCCESS = "Despesa '{description}' excluída com sucesso"
    AUTOFILL_SUCCESS = "Dados da despesa recuperados para autofill"
    DETAILS_SUCCESS = "Detalhes da despesa recuperados"
    RECENT_EXPENSES_SUCCESS = "Despesas recentes recuperadas"
    INVALID_REQUEST = "Requisição inválida"
