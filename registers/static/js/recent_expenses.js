/**
 * Recent Expenses Module
 *
 * Gerencia as interacoes da tabela de despesas recentes:
 * - Carregamento via AJAX
 * - Modal de detalhes
 * - Autofill do formulario
 * - Exclusao com confirmacao
 */

const i18n = window.RecentExpensesI18n || {};

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
        this.elements.cardList = document.getElementById('recentExpensesCardList');
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
        if (this.elements.cardList) {
            this.elements.cardList.addEventListener('click', (e) => this.handleRowAction(e));
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
                    this.showError(data.error || i18n.loadError || 'Erro ao carregar despesas');
                }
            })
            .catch((error) => {
                console.error('Error loading recent expenses:', error);
                this.showError(i18n.connectionError || 'Erro de conexao ao carregar despesas');
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

        this.elements.cardList.innerHTML = expenses.map((expense) => this.renderExpenseCard(expense)).join('');

        this.hideLoading();
        this.elements.content.classList.remove('hidden');
        this.elements.empty.classList.add('hidden');
        this.elements.error.classList.add('hidden');
    },

    /**
     * Renderiza um card de despesa
     */
    renderExpenseCard: function (expense) {
        return `
            <div class="bg-zinc-700/30 rounded-lg p-4 flex flex-col gap-2">
                <p class="text-white font-semibold text-base">${expense.description}</p>
                <p class="text-green-400 font-bold text-xl">${expense.amount_formatted}</p>
                <p class="text-gray-400 text-sm">${expense.date_formatted}</p>
                <div class="grid grid-cols-2 gap-2 mt-2 pt-2 border-t border-zinc-600">
                    <button type="button" class="action-btn flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded-lg text-sm transition-colors" data-id="${expense.id}" data-action="autofill">
                        <i class="fas fa-copy"></i>${i18n.use || 'Usar'}
                    </button>
                    <button type="button" class="action-btn flex items-center justify-center gap-2 bg-gray-600 hover:bg-gray-700 text-white py-2 px-4 rounded-lg text-sm transition-colors" data-id="${expense.id}" data-action="details">
                        <i class="fas fa-eye"></i>${i18n.viewDetails || 'Ver detalhes'}
                    </button>
                    <a href="/expense/${expense.id}/update/" class="flex items-center justify-center gap-2 bg-yellow-600 hover:bg-yellow-700 text-white py-2 px-4 rounded-lg text-sm transition-colors">
                        <i class="fas fa-edit"></i>${i18n.edit || 'Editar'}
                    </a>
                    <button type="button" class="action-btn flex items-center justify-center gap-2 bg-red-600 hover:bg-red-700 text-white py-2 px-4 rounded-lg text-sm transition-colors" data-id="${expense.id}" data-description="${expense.description}" data-action="delete">
                        <i class="fas fa-trash"></i>${i18n.delete || 'Excluir'}
                    </button>
                </div>
            </div>
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
                // Find the expense to get its category_id
                const expense = this.expenses.find(exp => exp.id == id);
                if (expense && expense.category_id && window.expenseListModal) {
                    // Open new modal with category filter
                    window.expenseListModal.open('category', expense.category_id, id);
                } else {
                    console.error('Could not open expense list modal - expense or category not found');
                }
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
                    alert(data.error || i18n.autofillError || 'Erro ao carregar dados');
                }
            })
            .catch((error) => {
                console.error('Error loading autofill data:', error);
                alert(i18n.connectionError || 'Erro de conexao');
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
            id_payment_method: formData.payment_method_id,
            id_installments: formData.installments,
        };

        for (const [fieldId, value] of Object.entries(fields)) {
            const field = document.getElementById(fieldId);
            if (field && value !== undefined && value !== null && value !== '') {
                field.value = value;
            }
        }

        if (formData.category_id && formData.category_name && typeof CategoryAutocomplete !== 'undefined') {
            CategoryAutocomplete.selectCategory(formData.category_id, formData.category_name);
        }
    },

    /**
     * Rola a pagina ate o formulario
     */
    scrollToForm: function () {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    },


    /**
     * Exclui uma despesa com confirmacao
     */
    deleteExpense: function (expenseId, description) {
        const msg = `${i18n.confirmDelete || 'Deseja realmente excluir a despesa'} "${description}"?`;
        if (!confirm(msg)) {
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
                    alert(data.error || i18n.deleteError || 'Erro ao excluir despesa');
                }
            })
            .catch((error) => {
                console.error('Error deleting expense:', error);
                alert(i18n.connectionError || 'Erro de conexao');
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
