// Expense list page: delete with a confirmation <dialog> (then reload, so every total is right), and a back
// button that keeps the previous page's state.
(() => {
  const dialog = document.getElementById('confirm-delete');
  const text = document.getElementById('confirm-delete-text');
  const error = document.getElementById('confirm-delete-error');
  const ok = document.getElementById('confirm-delete-ok');
  let pending = null;

  document.querySelectorAll('.delete-expense-btn').forEach((btn) => btn.addEventListener('click', () => {
    pending = btn;
    text.textContent = `A despesa "${btn.dataset.expenseDescription}" será excluída.`;
    error.hidden = true;
    dialog.showModal();
  }));

  ok.addEventListener('click', async () => {
    ok.disabled = true;
    try {
      const response = await App.post(pending.dataset.url);
      const data = await response.json();
      if (!data.success) throw new Error(data.error || 'Falha ao excluir');
      window.location.reload();
    } catch (e) {
      error.textContent = e.message;
      error.hidden = false;
    } finally {
      ok.disabled = false;
    }
  });

  document.getElementById('list-back').addEventListener('click', (e) => {
    if (document.referrer && history.length > 1) { e.preventDefault(); history.back(); }
  });
})();
