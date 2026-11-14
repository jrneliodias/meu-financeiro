# Modais de lista viram páginas — Plano

**Goal:** Modais ficam só para confirmação (excluir, sincronizar). Todo modal que lista dados ou tem botões/edição vira página.

**Decisões do usuário:** uma página genérica de lista para os 4 modais de despesas; o sino abre `Pagamentos do mês` (página que já existe); detalhamento do "Total esperado" e "Processar recorrentes" viram páginas.

## Tarefas
1. `/despesas/lista/` (`date=` | `category_id=&month=&year=` | `installments=1&month=&year=`): linhas com editar e excluir (confirmação em `<dialog>`), totais e botão voltar. Repositório: `ExpenseRepository.get_expense_list(user, ...)`.
2. Pontos de entrada passam a navegar para a lista: gráfico diário, tabela de categorias, card de parcelas, lista de recentes no cadastro. Remover os 4 modais e o JS morto.
3. Sino: link para `recurring_payments`, mantém o selo. Remover `payment_notifications_dialog`.
4. `/orcamento/detalhamento/` substitui `budgetBreakdownModal`.
5. `/recurring-expenses/processar/` substitui `processRecurringModal` (formulário + resultado).
6. Limpeza, CLAUDE.md, regressão completa, verificação no navegador.

## Verificação
- Testes novos por página (filtro, escopo por usuário, login obrigatório) e um teste de regressão: nenhuma página renderiza os ids dos modais antigos.
- Suíte completa + Playwright em desktop e celular (clique do gráfico/tabela/card leva à lista; excluir pede confirmação).
