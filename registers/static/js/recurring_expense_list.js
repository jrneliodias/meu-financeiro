document.addEventListener('DOMContentLoaded', function() {
    // Toggle Buttons
    const toggleButtons = document.querySelectorAll('.toggle-btn');
    toggleButtons.forEach(button => {
        button.addEventListener('click', function() {
            const id = this.getAttribute('data-id');

            fetch(`/recurring-expense/${id}/toggle/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/json',
                },
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update icon
                    const icon = this.querySelector('i');
                    const newState = data.generate_debit;
                    icon.className = `fas fa-toggle-${newState ? 'on' : 'off'} text-2xl ${newState ? 'text-green-500' : 'text-gray-500'}`;
                    this.setAttribute('data-active', newState ? 'True' : 'False');

                    // Display message (you can implement toast notifications)
                    console.log(data.message);
                    alert(data.message);
                } else {
                    alert(data.error);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error toggling recurring expense');
            });
        });
    });

    // View Expenses Buttons
    const viewButtons = document.querySelectorAll('.view-expenses-btn');
    viewButtons.forEach(button => {
        button.addEventListener('click', function() {
            const id = this.getAttribute('data-id');
            showRecurringExpenseModal(id);
        });
    });

    // Delete Buttons
    const deleteButtons = document.querySelectorAll('.delete-btn');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function() {
            const id = this.getAttribute('data-id');
            const description = this.getAttribute('data-description');

            if (confirm(`Are you sure you want to delete "${description}"?`)) {
                fetch(`/recurring-expense/${id}/delete/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken'),
                        'Content-Type': 'application/json',
                    },
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert(data.message);
                        // Reload page after short delay
                        setTimeout(() => window.location.reload(), 500);
                    } else {
                        alert(data.error);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('Error deleting recurring expense');
                });
            }
        });
    });

    // Modal Functions
    function showRecurringExpenseModal(id) {
        const modal = document.getElementById('recurringExpenseModal');
        const loading = document.getElementById('recurringModalLoading');
        const error = document.getElementById('recurringModalError');
        const content = document.getElementById('recurringModalContent');

        // Show modal with loading state
        modal.classList.remove('hidden');
        loading.classList.remove('hidden');
        error.classList.add('hidden');
        content.classList.add('hidden');

        // Fetch data via AJAX
        fetch(`/recurring-expense-details/?id=${id}`, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            },
        })
        .then(response => response.json())
        .then(data => {
            loading.classList.add('hidden');

            if (data.error) {
                error.classList.remove('hidden');
                document.getElementById('recurringModalErrorMessage').textContent = data.error;
            } else {
                content.classList.remove('hidden');

                // Update summary
                document.getElementById('recurringModalTitle').textContent =
                    `${data.recurring_expense.description}`;
                document.getElementById('recurringModalAmount').textContent =
                    formatBRL(data.recurring_expense.total_amount);
                document.getElementById('recurringModalCount').textContent =
                    data.expense_count;
                document.getElementById('recurringModalTotal').textContent =
                    formatBRL(data.total_generated);

                // Update expenses list
                const expensesList = document.getElementById('recurringExpensesList');
                expensesList.innerHTML = '';

                if (data.expenses.length === 0) {
                    expensesList.innerHTML = `
                        <tr>
                            <td colspan="5" class="text-center p-4 text-gray-400">
                                No expenses generated yet.
                            </td>
                        </tr>
                    `;
                } else {
                    data.expenses.forEach(expense => {
                        const row = document.createElement('tr');
                        row.innerHTML = `
                            <td class="px-4 py-3">${formatDate(expense.date)}</td>
                            <td class="px-4 py-3">${expense.description}</td>
                            <td class="px-4 py-3">${expense.category}</td>
                            <td class="px-4 py-3">${expense.payment_method}</td>
                            <td class="px-4 py-3 text-right">${formatBRL(expense.amount)}</td>
                        `;
                        expensesList.appendChild(row);
                    });
                }
            }
        })
        .catch(error => {
            console.error('Error:', error);
            loading.classList.add('hidden');
            error.classList.remove('hidden');
            document.getElementById('recurringModalErrorMessage').textContent =
                'Failed to load expense details.';
        });
    }

    // Modal close buttons
    document.getElementById('recurringModalCloseBtn').addEventListener('click', closeModal);
    document.getElementById('recurringModalCloseFooterBtn').addEventListener('click', closeModal);

    function closeModal() {
        document.getElementById('recurringExpenseModal').classList.add('hidden');
    }

    // Funções utilitárias
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    function formatBRL(value) {
        return new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        }).format(value);
    }

    function formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('pt-BR');
    }

    // Process Recurring Expenses Modal Functions
    window.showProcessRecurringModal = function() {
        // Set default month and year to current
        const now = new Date();
        const currentMonth = now.getMonth() + 1;
        const currentYear = now.getFullYear();

        document.getElementById('processMonth').value = currentMonth;
        document.getElementById('processYear').value = currentYear;

        // Reset result message
        document.getElementById('processResult').classList.add('hidden');

        // Show modal
        document.getElementById('processRecurringModal').classList.remove('hidden');
    }

    window.closeProcessRecurringModal = function() {
        document.getElementById('processRecurringModal').classList.add('hidden');
    }

    window.submitProcessRecurring = function() {
        const month = document.getElementById('processMonth').value;
        const year = document.getElementById('processYear').value;
        const processBtn = document.getElementById('processBtn');
        const resultDiv = document.getElementById('processResult');

        // Disable button and show loading
        processBtn.disabled = true;
        processBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Processando...';

        // AJAX request
        fetch('/process-recurring-expenses/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: `month=${month}&year=${year}`
        })
        .then(response => response.json())
        .then(data => {
            // Re-enable button
            processBtn.disabled = false;
            processBtn.innerHTML = '<i class="fas fa-check mr-2"></i>Processar';

            // Show result
            resultDiv.classList.remove('hidden');

            if (data.success) {
                resultDiv.className = 'mt-4 p-4 rounded-lg bg-green-900/20 border border-green-500 text-green-400';

                let message = `<strong>Sucesso!</strong><br>`;
                message += `${data.created_count} despesa(s) criada(s)<br>`;
                message += `${data.skipped_count} já existente(s)`;

                if (data.errors && data.errors.length > 0) {
                    message += `<br><br><strong>Avisos:</strong><br>${data.errors.join('<br>')}`;
                }

                resultDiv.innerHTML = message;

                // Reload page after 2 seconds
                setTimeout(() => {
                    window.location.reload();
                }, 2000);
            } else {
                resultDiv.className = 'mt-4 p-4 rounded-lg bg-red-900/20 border border-red-500 text-red-400';
                resultDiv.innerHTML = `<strong>Erro:</strong> ${data.error || 'Erro ao processar despesas'}`;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            processBtn.disabled = false;
            processBtn.innerHTML = '<i class="fas fa-check mr-2"></i>Processar';

            resultDiv.classList.remove('hidden');
            resultDiv.className = 'mt-4 p-4 rounded-lg bg-red-900/20 border border-red-500 text-red-400';
            resultDiv.innerHTML = '<strong>Erro:</strong> Erro de comunicação com o servidor';
        });
    }

    // Close modal when clicking outside
    document.getElementById('processRecurringModal')?.addEventListener('click', function(e) {
        if (e.target === this) {
            closeProcessRecurringModal();
        }
    });
});
