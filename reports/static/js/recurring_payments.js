// Month's payments page: re-render after a payment changes so it moves between "pending" and "paid".
// Changes made inside the bell pop-up wait until the pop-up closes.
document.addEventListener('expense-payment-saved', (event) => {
  if (!event.detail.fromNotifications) window.location.reload();
});
document.addEventListener('payment-notifications-closed', (event) => {
  if (event.detail.changed) window.location.reload();
});
