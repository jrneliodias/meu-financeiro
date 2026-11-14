// Selo do sino: mostra quantas recorrências estão pendentes/atrasadas no mês.
document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.getElementById('payment-notifications-toggle');
    const count = document.getElementById('payment-notifications-count');
    if (!toggle || !count) return;
    let latestRequest = 0;

    async function refresh() {
        const request = ++latestRequest;
        try {
            const response = await fetch(toggle.dataset.url, {
                headers: {'X-Requested-With': 'XMLHttpRequest'}, cache: 'no-store',
            });
            if (!response.ok) return;
            const data = await response.json();
            if (request !== latestRequest) return;
            count.textContent = data.pending_count;
            count.hidden = data.pending_count === 0;
            count.classList.toggle('notification-count--overdue', data.overdue_count > 0);
            toggle.setAttribute('aria-label', `Pagamentos do mês: ${data.pending_count} pendentes, ${data.overdue_count} atrasadas`);
        } catch (error) { /* o selo é opcional */ }
    }

    document.addEventListener('expense-payment-saved', refresh);
    refresh();
});
