// Helpers shared by every page (loaded in core/base.html).
window.App = {
  brl: (value, decimals = 2) => new Intl.NumberFormat('pt-BR', {
    style: 'currency', currency: 'BRL', minimumFractionDigits: decimals, maximumFractionDigits: decimals,
  }).format(value),
  csrfToken: () => (document.cookie.match(/(?:^|; )csrftoken=([^;]*)/) || [])[1] || '',
  // POST with Django's CSRF token; `body` is sent as JSON when given.
  post(url, body) {
    const headers = { 'X-CSRFToken': App.csrfToken(), 'X-Requested-With': 'XMLHttpRequest' };
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    return fetch(url, { method: 'POST', headers, body: body === undefined ? undefined : JSON.stringify(body) });
  },
};

// <form data-confirm="…">: ask before submitting.
document.addEventListener('submit', (event) => {
  const form = event.target;
  if (form.dataset.confirm && !confirm(form.dataset.confirm)) event.preventDefault();
});

// <button data-post-url="…" [data-confirm="…"]>: confirm, POST, reload on success, show the error otherwise.
document.addEventListener('click', async (event) => {
  const button = event.target.closest('[data-post-url]');
  if (!button || (button.dataset.confirm && !confirm(button.dataset.confirm))) return;
  const response = await App.post(button.dataset.postUrl);
  const data = await response.json().catch(() => ({}));
  if (data.success) window.location.reload();
  else alert(data.error || `Erro ${response.status}`);
});
