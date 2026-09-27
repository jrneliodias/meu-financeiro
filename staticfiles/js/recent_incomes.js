/**
 * Recent Incomes Module
 *
 * Gerencia as interacoes da lista de entradas recentes:
 * - Carregamento via AJAX
 * - Autofill do formulario
 * - Exclusao com confirmacao
 */

const incomeI18n = window.RecentIncomesI18n || {};

const RecentIncomes = {
    ENDPOINTS: {
        RECENT: '/register/income/recent/',
        AUTOFILL: '/register/income/{id}/autofill/',
        DELETE: '/register/income/{id}/delete/',
    },

    elements: {
        loading: null,
        error: null,
        errorMessage: null,
        content: null,
        cardList: null,
        empty: null,
        refreshBtn: null,
    },

    init: function () {
        this.cacheElements();
        this.bindEvents();
        this.loadRecentIncomes();
    },

    cacheElements: function () {
        this.elements.loading = document.getElementById('recentIncomesLoading');
        this.elements.error = document.getElementById('recentIncomesError');
        this.elements.errorMessage = document.getElementById('recentIncomesErrorMessage');
        this.elements.content = document.getElementById('recentIncomesContent');
        this.elements.cardList = document.getElementById('recentIncomesCardList');
        this.elements.empty = document.getElementById('recentIncomesEmpty');
        this.elements.refreshBtn = document.getElementById('refreshRecentIncomes');
    },

    bindEvents: function () {
        if (this.elements.refreshBtn) {
            this.elements.refreshBtn.addEventListener('click', () => this.loadRecentIncomes());
        }

        if (this.elements.cardList) {
            this.elements.cardList.addEventListener('click', (e) => this.handleCardAction(e));
        }
    },

    loadRecentIncomes: function () {
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
                    this.renderIncomes(data.incomes);
                } else {
                    this.showError(data.error || incomeI18n.loadError || 'Erro ao carregar entradas');
                }
            })
            .catch((error) => {
                console.error('Error loading recent incomes:', error);
                this.showError(incomeI18n.connectionError || 'Erro de conexao ao carregar entradas');
            });
    },

    renderIncomes: function (incomes) {
        if (!incomes || incomes.length === 0) {
            this.showEmpty();
            return;
        }

        this.elements.cardList.innerHTML = incomes.map((income) => this.renderIncomeCard(income)).join('');

        this.hideLoading();
        this.elements.content.classList.remove('hidden');
        this.elements.empty.classList.add('hidden');
        this.elements.error.classList.add('hidden');
    },

    renderIncomeCard: function (income) {
        const subtitle = income.category_name
            ? `${income.date_formatted} &middot; ${income.category_name}`
            : income.date_formatted;

        return `
            <div class="bg-zinc-700/30 rounded-lg p-4 flex flex-col gap-2">
                <p class="text-white font-semibold text-base">${income.description}</p>
                <p class="text-green-400 font-bold text-xl">${income.amount_formatted}</p>
                <p class="text-gray-400 text-sm">${subtitle}</p>
                <div class="grid grid-cols-2 gap-2 mt-2 pt-2 border-t border-zinc-600">
                    <button type="button" class="action-btn flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded-lg text-sm transition-colors" data-id="${income.id}" data-action="autofill">
                        <i class="fas fa-copy"></i>${incomeI18n.use || 'Usar'}
                    </button>
                    <button type="button" class="action-btn flex items-center justify-center gap-2 bg-red-600 hover:bg-red-700 text-white py-2 px-4 rounded-lg text-sm transition-colors" data-id="${income.id}" data-description="${income.description}" data-action="delete">
                        <i class="fas fa-trash"></i>${incomeI18n.delete || 'Excluir'}
                    </button>
                </div>
            </div>
        `;
    },

    handleCardAction: function (e) {
        const btn = e.target.closest('.action-btn');
        if (!btn) return;

        const action = btn.dataset.action;
        const id = btn.dataset.id;

        switch (action) {
            case 'autofill':
                this.autofillForm(id);
                break;
            case 'delete':
                this.deleteIncome(id, btn.dataset.description);
                break;
        }
    },

    autofillForm: function (incomeId) {
        const url = this.ENDPOINTS.AUTOFILL.replace('{id}', incomeId);

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
                    alert(data.error || incomeI18n.autofillError || 'Erro ao carregar dados');
                }
            })
            .catch((error) => {
                console.error('Error loading autofill data:', error);
                alert(incomeI18n.connectionError || 'Erro de conexao');
            });
    },

    populateForm: function (formData) {
        const fields = {
            id_description: formData.description,
            id_amount: formData.amount,
            id_date: formData.date,
        };

        for (const [fieldId, value] of Object.entries(fields)) {
            const field = document.getElementById(fieldId);
            if (field && value !== undefined && value !== null && value !== '') {
                field.value = value;
            }
        }

        const categorySelect = document.getElementById('id_category');
        if (categorySelect && formData.category_id) {
            categorySelect.value = formData.category_id;
        }
    },

    scrollToForm: function () {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    },

    deleteIncome: function (incomeId, description) {
        const msg = `${incomeI18n.confirmDelete || 'Deseja realmente excluir a entrada'} "${description}"?`;
        if (!confirm(msg)) {
            return;
        }

        const url = this.ENDPOINTS.DELETE.replace('{id}', incomeId);

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
                    this.loadRecentIncomes();
                } else {
                    alert(data.error || incomeI18n.deleteError || 'Erro ao excluir entrada');
                }
            })
            .catch((error) => {
                console.error('Error deleting income:', error);
                alert(incomeI18n.connectionError || 'Erro de conexao');
            });
    },

    showLoading: function () {
        this.elements.loading.classList.remove('hidden');
        this.elements.content.classList.add('hidden');
        this.elements.empty.classList.add('hidden');
        this.elements.error.classList.add('hidden');
    },

    hideLoading: function () {
        this.elements.loading.classList.add('hidden');
    },

    showEmpty: function () {
        this.hideLoading();
        this.elements.empty.classList.remove('hidden');
        this.elements.content.classList.add('hidden');
        this.elements.error.classList.add('hidden');
    },

    showError: function (message) {
        this.hideLoading();
        this.elements.errorMessage.textContent = message;
        this.elements.error.classList.remove('hidden');
        this.elements.content.classList.add('hidden');
        this.elements.empty.classList.add('hidden');
    },

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

document.addEventListener('DOMContentLoaded', function () {
    RecentIncomes.init();
});
