document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.getElementById('payment-notifications-toggle');
    const dialog = document.getElementById('payment-notifications');
    if (!toggle || !dialog) return;
    const content = document.getElementById('payment-notifications-content');
    const count = document.getElementById('payment-notifications-count');
    let latestRequest = 0;
    let changed = false;

    async function refresh() {
        const request = ++latestRequest;
        content.setAttribute('aria-busy', 'true');
        try {
            const response = await fetch(toggle.dataset.url, {
                headers: {'X-Requested-With': 'XMLHttpRequest'}, cache: 'no-store',
            });
            if (!response.ok) throw new Error('Notifications unavailable');
            const data = await response.json();
            if (request !== latestRequest) return;
            content.innerHTML = data.html;
            count.textContent = data.pending_count;
            count.hidden = data.pending_count === 0;
            count.classList.toggle('notification-count--overdue', data.overdue_count > 0);
            toggle.setAttribute('aria-label', `Notificações: ${data.pending_count} pendentes, ${data.overdue_count} atrasadas neste mês`);
        } catch (error) {
            if (request !== latestRequest) return;
            content.replaceChildren();
            const message = document.createElement('p');
            message.textContent = 'Não foi possível carregar os pagamentos.';
            const retry = document.createElement('button');
            retry.type = 'button';
            retry.className = 'text-blue-300 underline';
            retry.textContent = 'Tentar novamente';
            retry.addEventListener('click', refresh);
            content.append(message, retry);
        } finally {
            if (request === latestRequest) content.removeAttribute('aria-busy');
        }
    }

    toggle.addEventListener('click', () => {
        dialog.showModal();
        if (!content.childElementCount) content.textContent = 'Carregando pagamentos…';
        refresh();
    });
    document.getElementById('payment-notifications-close').addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', event => {
        const bounds = dialog.getBoundingClientRect();
        if (event.target === dialog && (event.clientX < bounds.left || event.clientX > bounds.right ||
            event.clientY < bounds.top || event.clientY > bounds.bottom)) dialog.close();
    });
    dialog.addEventListener('close', () => {
        toggle.focus();
        document.dispatchEvent(new CustomEvent('payment-notifications-closed', {detail: {changed}}));
        changed = false;
    });
    document.addEventListener('expense-payment-saved', event => {
        if (event.detail?.fromNotifications) changed = true;
        refresh();
    });
    refresh();
});
