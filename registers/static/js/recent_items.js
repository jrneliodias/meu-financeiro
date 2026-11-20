// "Recent" lists under the register forms (register/components/recent_items.html):
// "Use" copies an item into the form above, "Delete" removes it.
document.querySelectorAll('[data-recent-items]').forEach((list) => {
  list.addEventListener('click', async (event) => {
    const button = event.target.closest('[data-action]');
    if (!button) return;
    const item = button.closest('[data-recent-item]');
    button.closest('[popover]')?.hidePopover();

    if (button.dataset.action === 'use') {
      const { description, amount, date, paymentMethodId, categoryId, categoryName } = item.dataset;
      const fields = { id_description: description, id_amount: amount, id_date: date,
                       id_payment_method: paymentMethodId, id_installments: '1' };
      for (const [id, value] of Object.entries(fields)) {
        const field = document.getElementById(id);
        if (field && value) field.value = value;
      }
      if (categoryId && categoryName) CategoryAutocomplete.selectCategory(categoryId, categoryName);
    }

    if (button.dataset.action === 'delete' && confirm(button.dataset.confirm)) {
      const response = await App.post(button.dataset.url);
      const data = await response.json().catch(() => ({}));
      if (data.success) item.remove();
      else alert(data.error || list.dataset.deleteError);
    }
  });
});

// Action menus ([popover][data-menu]) open under the button that toggles them, or above when there's no room.
// 'toggle' doesn't bubble, so listen in the capture phase.
document.addEventListener('toggle', (event) => {
  const menu = event.target;
  if (event.newState !== 'open' || !menu.matches('[data-menu]')) return;
  const rect = document.querySelector(`[popovertarget="${menu.id}"]`).getBoundingClientRect();
  const fitsBelow = rect.bottom + menu.offsetHeight + 8 < window.innerHeight;
  menu.style.top = `${fitsBelow ? rect.bottom + 4 : rect.top - menu.offsetHeight - 4}px`;
  menu.style.left = `${Math.max(8, rect.right - menu.offsetWidth)}px`;
}, true);

// A fixed menu would detach from its button on scroll, so close it instead.
document.addEventListener('scroll', () => {
  document.querySelector('[data-menu]:popover-open')?.hidePopover();
}, { capture: true, passive: true });
