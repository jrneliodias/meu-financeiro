/**
 * Recent Expenses Module
 *
 * Gerencia as interacoes da tabela de despesas recentes:
 * - Carregamento via AJAX
 * - Modal de detalhes
 * - Autofill do formulario
 * - Exclusao com confirmacao
 */

const RecentExpenses = {
    // Endpoints da API
    ENDPOINTS: {
        RECENT: '/register/expense/recent/',
        DETAILS: '/register/expense/{id}/details/',
        AUTOFILL: '/register/expense/{id}/autofill/',
        DELETE: '/register/expense/{id}/delete/',
    },

    // Elementos do DOM
    elements: {
        section: null,
        loading: null,
        error: null,
        errorMessage: null,
        content: null,
        list: null,
        empty: null,
        refreshBtn: null,
        modal: null,
        modalCloseBtn: null,
        modalLoading: null,
        modalError: null,
        modalContent: null,
    },

    /**
     * Inicializa o modulo
     */
    init: function () {
        this.cacheElements();
        this.bindEvents();
        this.loadRecentExpenses();
    },

    /**
     * Cacheia referencias aos elementos do DOM
     */
    cacheElements: function () {
        this.elements.section = document.getElementById('recentExpensesSection');
        this.elements.loading = document.getElementById('recentExpensesLoading');
        this.elements.error = document.getElementById('recentExpensesError');
        this.elements.errorMessage = document.getElementById('recentExpensesErrorMessage');
        this.elements.content = document.getElementById('recentExpensesContent');
        this.elements.list = document.getElementById('recentExpensesList');
        this.elements.empty = document.getElementById('recentExpensesEmpty');
        this.elements.refreshBtn = document.getElementById('refreshRecentExpenses');
        this.elements.modal = document.getElementById('expenseDetailsModal');
        this.elements.modalCloseBtn = document.getElementById('expenseModalCloseBtn');
        this.elements.modalLoading = document.getElementById('expenseModalLoading');
        this.elements.modalError = document.getElementById('expenseModalError');
        this.elements.modalContent = document.getElementById('expenseModalContent');
    },

    /**
     * Vincula eventos aos elementos
     */
    bindEvents: function () {
        if (this.elements.refreshBtn) {
            this.elements.refreshBtn.addEventListener('click', () => this.loadRecentExpenses());
        }

        if (this.elements.modalCloseBtn) {
            this.elements.modalCloseBtn.addEventListener('click', () => this.closeModal());
        }

        if (this.elements.modal) {
            this.elements.modal.addEventListener('click', (e) => {
                if (e.target === this.elements.modal) {
                    this.closeModal();
                }
            });
        }

        // Delegate events para botoes dinamicos
        if (this.elements.list) {
            this.elements.list.addEventListener('click', (e) => this.handleRowAction(e));
        }

        if (this.elements.modal) {
            this.elements.modal.addEventListener('click', (e) => this.handleModalAction(e));
        }
    },

    /**
     * Carrega despesas recentes via AJAX
     */
    loadRecentExpenses: function () {
        this.showLoading();

        fetch(this.ENDPOINTS.RECENT, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            },
        })
            .then((response) => response.json())
            .then((data) => {
                if (data.success) {
                    this.renderExpenses(data.expenses);
                } else {
                    this.showError(data.error || 'Erro ao carregar despesas');
                }
            })
            .catch((error) => {
                console.error('Error loading recent expenses:', error);
                this.showError('Erro de conexao ao carregar despesas');
            });
    },

    /**
     * Renderiza lista de despesas
     */
    renderExpenses: function (expenses) {
        if (!expenses || expenses.length === 0) {
            this.showEmpty();
            return;
        }

        this.elements.list.innerHTML = expenses.map((expense) => this.renderExpenseRow(expense)).join('');

        this.hideLoading();
        this.elements.content.classList.remove('hidden');
        this.elements.empty.classList.add('hidden');
        this.elements.error.classList.add('hidden');
    },

    /**
     * Renderiza uma linha da tabela
     */
    renderExpenseRow: function (expense) {
        return `
            <tr class="hover:bg-zinc-700/50 transition-colors">
                <td class="px-4 py-3 text-gray-300 whitespace-nowrap">${expense.date_formatted}</td>
                <td class="px-4 py-3 text-gray-200 truncate max-w-xs" title="${expense.description}">${expense.description}</td>
                <td class="px-4 py-3 text-right text-gray-200 whitespace-nowrap">${expense.amount_formatted}</td>
                <td class="px-4 py-3 text-center">
                    <div class="flex justify-center gap-2">
                        <button
                            type="button"
                            class="action-btn autofill-btn text-blue-400 hover:text-blue-300 p-1"
                            data-id="${expense.id}"
                            data-action="autofill"
                            title="Usar como template"
                        >
                            <i class="fas fa-copy"></i>
                        </button>
                        <button
                            type="button"
                            class="action-btn details-btn text-gray-400 hover:text-gray-300 p-1"
                            data-id="${expense.id}"
                            data-action="details"
                            title="Ver detalhes"
                        >
                            <i class="fas fa-eye"></i>
                        </button>
                        <a
                            href="/expense/${expense.id}/update/"
                            class="action-btn edit-btn text-yellow-400 hover:text-yellow-300 p-1"
                            title="Editar"
                        >
                            <i class="fas fa-edit"></i>
                        </a>
                        <button
                            type="button"
                            class="action-btn delete-btn text-red-400 hover:text-red-300 p-1"
                            data-id="${expense.id}"
                            data-description="${expense.description}"
                            data-action="delete"
                            title="Excluir"
                        >
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    },

    /**
     * Trata acoes nos botoes da tabela
     */
    handleRowAction: function (e) {
        const btn = e.target.closest('.action-btn');
        if (!btn) return;

        const action = btn.dataset.action;
        const id = btn.dataset.id;

        switch (action) {
            case 'autofill':
                this.autofillForm(id);
                break;
            case 'details':
                this.showDetailsModal(id);
                break;
            case 'delete':
                const description = btn.dataset.description;
                this.deleteExpense(id, description);
                break;
        }
    },

    /**
     * Trata acoes nos botoes do modal
     */
    handleModalAction: function (e) {
        const btn = e.target.closest('[data-modal-action]');
        if (!btn) return;

        const action = btn.dataset.modalAction;
        const id = btn.dataset.id;

        switch (action) {
            case 'autofill':
                this.autofillForm(id);
                this.closeModal();
                break;
            case 'delete':
                const description = btn.dataset.description;
                this.deleteExpense(id, description);
                break;
        }
    },

    /**
     * Preenche o formulario com dados de uma despesa
     */
    autofillForm: function (expenseId) {
        const url = this.ENDPOINTS.AUTOFILL.replace('{id}', expenseId);

        fetch(url, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            },
        })
            .then((response) => response.json())
            .then((data) => {
                if (data.success) {
                    this.populateForm(data.form_data);
                    this.scrollToForm();
                } else {
                    alert(data.error || 'Erro ao carregar dados');
                }
            })
            .catch((error) => {
                console.error('Error loading autofill data:', error);
                alert('Erro de conexao');
            });
    },

    /**
     * Popula os campos do formulario
     */
    populateForm: function (formData) {
        const fields = {
            id_description: formData.description,
            id_amount: formData.amount,
            id_date: formData.date,
            id_category: formData.category_id,
            id_payment_method: formData.payment_method_id,
            id_installments: formData.installments,
        };

        for (const [fieldId, value] of Object.entries(fields)) {
            const field = document.getElementById(fieldId);
            if (field && value !== undefined && value !== null && value !== '') {
                field.value = value;
            }
        }
    },

    /**
     * Rola a pagina ate o formulario
     */
    scrollToForm: function () {
        const form = document.querySelector('form');
        if (form) {
            form.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    },

    /**
     * Exibe o modal de detalhes
     */
    showDetailsModal: function (expenseId) {
        if (!this.elements.modal) return;

        this.elements.modal.classList.remove('hidden');
        this.elements.modalLoading.classList.remove('hidden');
        this.elements.modalContent.classList.add('hidden');
        this.elements.modalError.classList.add('hidden');

        const url = this.ENDPOINTS.DETAILS.replace('{id}', expenseId);

        fetch(url, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            },
        })
            .then((response) => response.json())
            .then((data) => {
                if (data.success) {
                    this.renderModalContent(data.expense);
                } else {
                    this.showModalError(data.error || 'Erro ao carregar detalhes');
                }
            })
            .catch((error) => {
                console.error('Error loading expense details:', error);
                this.showModalError('Erro de conexao');
            });
    },

    /**
     * Renderiza o conteudo do modal
     */
    renderModalContent: function (expense) {
        const html = `
            <div class="space-y-4">
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block text-sm text-gray-400">Descricao</label>
                        <p class="text-white">${expense.description}</p>
                    </div>
                    <div>
                        <label class="block text-sm text-gray-400">Valor</label>
                        <p class="text-white text-lg font-semibold">${expense.amount_formatted}</p>
                    </div>
                </div>
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block text-sm text-gray-400">Data</label>
                        <p class="text-white">${expense.date_formatted}</p>
                    </div>
                    <div>
                        <label class="block text-sm text-gray-400">Categoria</label>
                        <p class="text-white">${expense.category_name || '-'}</p>
                    </div>
                </div>
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block text-sm text-gray-400">Forma de Pagamento</label>
                        <p class="text-white">${expense.payment_method_name || '-'}</p>
                    </div>
                    <div>
                        <label class="block text-sm text-gray-400">Tipo</label>
                        <p class="text-white">
                            ${expense.is_installment ? '<span class="text-blue-400">Parcelamento</span>' : ''}
                            ${expense.is_recurring ? '<span class="text-green-400">Recorrente</span>' : ''}
                            ${!expense.is_installment && !expense.is_recurring ? 'Avulso' : ''}
                        </p>
                    </div>
                </div>
                ${
                    expense.installment_info
                        ? `
                <div class="mt-4 p-3 bg-zinc-700/50 rounded">
                    <label class="block text-sm text-gray-400 mb-2">Informacoes do Parcelamento</label>
                    <p class="text-white">${expense.installment_info.description}</p>
                    <p class="text-gray-300 text-sm">
                        Total: ${expense.installment_info.total_amount_formatted} em ${expense.installment_info.total_installments}x
                    </p>
                </div>
                `
                        : ''
                }
            </div>

            <div class="flex justify-between mt-6 pt-4 border-t border-zinc-700">
                <button
                    type="button"
                    class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded transition-colors"
                    data-modal-action="autofill"
                    data-id="${expense.id}"
                >
                    <i class="fas fa-copy mr-2"></i>Usar como Template
                </button>
                <div class="flex gap-2">
                    <a
                        href="/expense/${expense.id}/update/"
                        class="bg-yellow-600 hover:bg-yellow-700 text-white px-4 py-2 rounded transition-colors"
                    >
                        <i class="fas fa-edit mr-2"></i>Editar
                    </a>
                    <button
                        type="button"
                        class="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded transition-colors"
                        data-modal-action="delete"
                        data-id="${expense.id}"
                        data-description="${expense.description}"
                    >
                        <i class="fas fa-trash mr-2"></i>Excluir
                    </button>
                </div>
            </div>
        `;

        this.elements.modalContent.innerHTML = html;
        this.elements.modalLoading.classList.add('hidden');
        this.elements.modalContent.classList.remove('hidden');
    },

    /**
     * Exclui uma despesa com confirmacao
     */
    deleteExpense: function (expenseId, description) {
        if (!confirm(`Deseja realmente excluir a despesa "${description}"?`)) {
            return;
        }

        const url = this.ENDPOINTS.DELETE.replace('{id}', expenseId);

        fetch(url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': this.getCookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest',
            },
        })
            .then((response) => response.json())
            .then((data) => {
                if (data.success) {
                    this.closeModal();
                    this.loadRecentExpenses();
                } else {
                    alert(data.error || 'Erro ao excluir despesa');
                }
            })
            .catch((error) => {
                console.error('Error deleting expense:', error);
                alert('Erro de conexao');
            });
    },

    /**
     * Fecha o modal
     */
    closeModal: function () {
        if (this.elements.modal) {
            this.elements.modal.classList.add('hidden');
        }
    },

    /**
     * Exibe estado de carregamento
     */
    showLoading: function () {
        this.elements.loading.classList.remove('hidden');
        this.elements.content.classList.add('hidden');
        this.elements.empty.classList.add('hidden');
        this.elements.error.classList.add('hidden');
    },

    /**
     * Esconde estado de carregamento
     */
    hideLoading: function () {
        this.elements.loading.classList.add('hidden');
    },

    /**
     * Exibe estado vazio
     */
    showEmpty: function () {
        this.hideLoading();
        this.elements.empty.classList.remove('hidden');
        this.elements.content.classList.add('hidden');
        this.elements.error.classList.add('hidden');
    },

    /**
     * Exibe estado de erro
     */
    showError: function (message) {
        this.hideLoading();
        this.elements.errorMessage.textContent = message;
        this.elements.error.classList.remove('hidden');
        this.elements.content.classList.add('hidden');
        this.elements.empty.classList.add('hidden');
    },

    /**
     * Exibe erro no modal
     */
    showModalError: function (message) {
        this.elements.modalLoading.classList.add('hidden');
        this.elements.modalError.textContent = message;
        this.elements.modalError.classList.remove('hidden');
    },

    /**
     * Obtem valor de um cookie
     */
    getCookie: function (name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === name + '=') {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    },
};

// Inicializa quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', function () {
    RecentExpenses.init();
});
