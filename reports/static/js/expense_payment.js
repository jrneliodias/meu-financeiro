// Payment checkboxes of recurring occurrences (reports/components/payment_checkbox.html), on any page
// and inside the bell pop-up. Every checkbox of the same expense is kept in sync; on success the
// 'expense-payment-saved' event tells the page (detail: expenseId, isPaid, fromNotifications).
document.addEventListener('change', async (event) => {
  const control = event.target.closest('.expense-payment-checkbox');
  if (!control) return;
  const requested = control.checked;
  const peers = [...document.querySelectorAll('.expense-payment-checkbox')]
    .filter((peer) => peer.dataset.expenseId === control.dataset.expenseId);
  const show = (isPaid, text) => peers.forEach((peer) => {
    peer.checked = isPaid;
    const label = peer.closest('label').querySelector('.payment-label');
    label.textContent = text ?? (isPaid ? peer.dataset.paidLabel : peer.dataset.pendingLabel);
    label.classList.toggle('text-green-400', isPaid);
    label.classList.toggle('text-yellow-400', !isPaid);
  });

  peers.forEach((peer) => {
    peer.disabled = true;
    peer.closest('label').setAttribute('aria-busy', 'true');
  });
  show(requested, control.dataset.savingLabel);
  try {
    const response = await App.post(control.dataset.url, { is_paid: requested });
    const data = response.ok ? await response.json() : {};
    if (data.success !== true || typeof data.is_paid !== 'boolean') throw new Error('Payment could not be saved');
    show(data.is_paid);
    document.dispatchEvent(new CustomEvent('expense-payment-saved', {
      detail: {
        expenseId: control.dataset.expenseId,
        isPaid: data.is_paid,
        fromNotifications: Boolean(control.closest('#payment-notifications')),
      },
    }));
  } catch (error) {
    show(!requested);
    alert(control.dataset.errorLabel);
  } finally {
    peers.forEach((peer) => {
      peer.disabled = false;
      peer.closest('label').removeAttribute('aria-busy');
    });
  }
});
