document.addEventListener('DOMContentLoaded', () => {
    const controls = [...document.querySelectorAll('.expense-payment-checkbox')];
    const csrfToken = document.cookie.split('; ')
        .find(cookie => cookie.startsWith('csrftoken='))?.split('=').slice(1).join('=');

    controls.forEach(control => {
        control.addEventListener('change', async () => {
            const requestedState = control.checked;
            const previousState = !requestedState;
            const peers = controls.filter(peer => peer.dataset.expenseId === control.dataset.expenseId);
            peers.forEach(peer => { peer.disabled = true; });
            try {
                const response = await fetch(control.dataset.url, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': decodeURIComponent(csrfToken || ''),
                    },
                    body: JSON.stringify({is_paid: requestedState}),
                });
                if (!response.ok) throw new Error('Payment could not be saved');
                const data = await response.json();
                if (data.success !== true || typeof data.is_paid !== 'boolean') {
                    throw new Error('Invalid payment response');
                }
                const pendingCount = document.querySelector('[data-pending-count]');
                if (pendingCount && previousState !== data.is_paid) {
                    pendingCount.textContent = Number(pendingCount.textContent) + (data.is_paid ? -1 : 1);
                }
                peers.forEach(peer => {
                    peer.checked = data.is_paid;
                    const label = peer.closest('label').querySelector('.payment-label');
                    label.textContent = data.is_paid ? peer.dataset.paidLabel : peer.dataset.pendingLabel;
                    label.classList.toggle('text-green-400', data.is_paid);
                    label.classList.toggle('text-yellow-400', !data.is_paid);
                });
            } catch (error) {
                control.checked = !requestedState;
                alert(control.dataset.errorLabel);
            } finally {
                peers.forEach(peer => { peer.disabled = false; });
            }
        });
    });
});
