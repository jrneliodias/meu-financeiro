// Regroup the monthly page when its own checkbox is saved.
document.addEventListener('expense-payment-saved', event => {
    if (!event.detail?.fromNotifications) window.location.reload();
});
document.addEventListener('payment-notifications-closed', event => {
    if (event.detail?.changed) window.location.reload();
});
