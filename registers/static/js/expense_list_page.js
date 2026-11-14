// Página de lista de despesas: excluir com confirmação (<dialog>) e botão voltar.
(() => {
  const dialog = document.getElementById('confirm-delete');
  const text = document.getElementById('confirm-delete-text');
  const error = document.getElementById('confirm-delete-error');
  const ok = document.getElementById('confirm-delete-ok');
  const total = document.getElementById('list-total');
  const count = document.getElementById('list-count');
  let pending = null;

  const brl = (v) => v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  const csrf = () => (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || '';

  document.querySelectorAll('.delete-expense-btn').forEach((btn) => btn.addEventListener('click', () => {
    pending = btn;
    text.textContent = `A despesa "${btn.dataset.expenseDescription}" será excluída.`;
    error.hidden = true;
    dialog.showModal();
  }));

  ok.addEventListener('click', async () => {
    ok.disabled = true;
    try {
      const response = await fetch(`/register/expense/${pending.dataset.expenseId}/delete/`, {
        method: 'POST', headers: { 'X-CSRFToken': csrf() },
      });
      const data = await response.json();
      if (!data.success) throw new Error(data.error || 'Falha ao excluir');
      pending.closest('.expense-row').remove();
      total.dataset.total = String(Number(total.dataset.total) - Number(pending.dataset.amount));
      total.textContent = brl(Number(total.dataset.total));
      count.textContent = String(Number(count.textContent) - 1);
      dialog.close();
    } catch (e) {
      error.textContent = e.message;
      error.hidden = false;
    } finally {
      ok.disabled = false;
    }
  });

  // volta para a página anterior (mantém filtros e posição) quando houver histórico
  document.getElementById('list-back').addEventListener('click', (e) => {
    if (document.referrer && history.length > 1) { e.preventDefault(); history.back(); }
  });
})();
