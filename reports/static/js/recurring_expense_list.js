// Recurring expenses list: keep "Pending this month" in step with payments saved from the bell pop-up.
document.addEventListener('expense-payment-saved', (event) => {
  const pendingCount = document.querySelector('[data-pending-count]');
  if (pendingCount) pendingCount.textContent = Number(pendingCount.textContent) + (event.detail.isPaid ? -1 : 1);
});
