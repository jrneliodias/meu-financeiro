/**
 * ExpenseListModal - SOLID Architecture for Expense List Modal
 *
 * Following the SOLID pattern from expense_category_table.html:
 * - Single Responsibility: Each class has one job
 * - Dependency Injection: Dependencies passed to constructors
 * - Separation of Concerns: API / Rendering / State Management
 */

// ==============================================================================
// Class 1: API Client (SRP - Only handles API communication)
// ==============================================================================

class ExpenseListApiClient {
    /**
     * Handles all API communication for expense list details.
     *
     * Single Responsibility: Only makes HTTP requests, no UI manipulation.
     */

    constructor(baseEndpointUrl = '/register/expense/list-details/') {
        this.baseEndpointUrl = baseEndpointUrl;
    }

    async fetchExpenseList(filterType, filterValue, expenseId = null) {
        const queryParameters = new URLSearchParams({
            filter_type: filterType,
            filter_value: filterValue
        });

        if (expenseId) {
            queryParameters.append('expense_id', expenseId);
        }

        const fullEndpointUrl = `${this.baseEndpointUrl}?${queryParameters.toString()}`;

        const apiResponse = await fetch(fullEndpointUrl, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/json',
            }
        });

        if (!apiResponse.ok) {
            throw new Error(`HTTP error! status: ${apiResponse.status}`);
        }

        const expenseListData = await apiResponse.json();

        if (expenseListData.error) {
            throw new Error(expenseListData.error);
        }

        return expenseListData;
    }
}


// ==============================================================================
// Class 2: Data Renderer (SRP - Only renders data to DOM)
// ==============================================================================

class ExpenseListRenderer {
    /**
     * Renders expense data in table and card formats.
     *
     * Single Responsibility: DOM manipulation and rendering only.
     */

    constructor(tableBodyElementId, cardContainerElementId) {
        this.tableBodyElement = document.getElementById(tableBodyElementId);
        this.cardContainerElement = document.getElementById(cardContainerElementId);
        this.cardRenderer = new ExpenseCardRenderer();
    }

    renderExpenseList(expenseDataArray) {
        // Clear existing content
        this.tableBodyElement.innerHTML = '';
        if (this.cardContainerElement) {
            this.cardContainerElement.innerHTML = '';
        }

        if (expenseDataArray.length === 0) {
            this.renderEmptyState();
            return;
        }

        expenseDataArray.forEach(expenseItem => {
            // Desktop table row
            const expenseTableRow = this.cardRenderer.renderTableRow(expenseItem);
            this.tableBodyElement.appendChild(expenseTableRow);

            // Mobile card
            if (this.cardContainerElement) {
                const expenseCard = this.cardRenderer.renderCard(expenseItem);
                this.cardContainerElement.appendChild(expenseCard);
            }
        });

        // Attach action button event listeners
        this.attachActionButtonListeners();
    }

    attachActionButtonListeners() {
        // Attach listeners to table delete buttons
        const tableDeleteButtons = this.tableBodyElement.querySelectorAll('.delete-expense-btn');
        tableDeleteButtons.forEach(button => {
            button.addEventListener('click', async (event) => {
                event.stopPropagation();
                const expenseId = button.getAttribute('data-expense-id');
                const expenseDescription = button.getAttribute('data-expense-description');

                if (confirm(`Tem certeza que deseja excluir "${expenseDescription}"?`)) {
                    await this.deleteExpense(expenseId, button);
                }
            });
        });

        // Attach listeners to card delete buttons
        if (this.cardContainerElement) {
            const cardDeleteButtons = this.cardContainerElement.querySelectorAll('.delete-expense-btn');
            cardDeleteButtons.forEach(button => {
                button.addEventListener('click', async (event) => {
                    event.stopPropagation();
                    const expenseId = button.getAttribute('data-expense-id');
                    const expenseDescription = button.getAttribute('data-expense-description');

                    if (confirm(`Tem certeza que deseja excluir "${expenseDescription}"?`)) {
                        await this.deleteExpense(expenseId, button);
                    }
                });
            });
        }
    }

    async deleteExpense(expenseId, buttonElement) {
        // Find both the table row and card for this expense
        const tableRow = this.tableBodyElement.querySelector(`tr[data-expense-id="${expenseId}"]`);
        const card = this.cardContainerElement?.querySelector(`div[data-expense-id="${expenseId}"]`);

        try {
            // Disable button during deletion
            buttonElement.disabled = true;
            buttonElement.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

            const response = await fetch(`/register/expense/${expenseId}/delete/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCsrfToken(),
                    'Content-Type': 'application/json',
                }
            });

            const data = await response.json();

            if (data.success) {
                // Remove both table row and card with animation
                [tableRow, card].forEach(element => {
                    if (element) {
                        element.style.opacity = '0';
                        element.style.transition = 'opacity 0.3s ease-out';
                    }
                });

                setTimeout(() => {
                    tableRow?.remove();
                    card?.remove();

                    // Update expense count
                    const countElement = document.getElementById('expenseListExpenseCount');
                    const currentCount = parseInt(countElement.textContent);
                    countElement.textContent = currentCount - 1;

                    // Check if table is now empty
                    const remainingRows = this.tableBodyElement.querySelectorAll('tr').length;
                    if (remainingRows === 0) {
                        this.renderEmptyState();
                    }
                }, 300);

                console.log(data.message);
            } else {
                alert(data.error || 'Falha ao excluir despesa');
                buttonElement.disabled = false;
                buttonElement.innerHTML = '<i class="fas fa-trash-alt"></i>';
            }
        } catch (error) {
            console.error('Error deleting expense:', error);
            alert('Ocorreu um erro ao excluir a despesa');
            buttonElement.disabled = false;
            buttonElement.innerHTML = '<i class="fas fa-trash-alt"></i>';
        }
    }

    getCsrfToken() {
        const cookieName = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, cookieName.length + 1) === (cookieName + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(cookieName.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    renderEmptyState() {
        this.tableBodyElement.innerHTML = `
            <tr>
                <td colspan="5" class="px-4 py-8 text-center text-gray-400">
                    <i class="fas fa-info-circle mr-2"></i>
                    Nenhuma despesa encontrada.
                </td>
            </tr>
        `;
        if (this.cardContainerElement) {
            this.cardContainerElement.innerHTML = `
                <div class="text-center text-gray-400 py-8">
                    <i class="fas fa-info-circle mr-2"></i>
                    Nenhuma despesa encontrada.
                </div>
            `;
        }
    }
}


// ==============================================================================
// Class 3: Modal State Manager (SRP - Only manages modal visibility and state)
// ==============================================================================

class ExpenseListModalManager {
    /**
     * Manages modal display states (loading, error, content).
     *
     * Single Responsibility: UI state management only.
     */

    constructor(modalElementId) {
        this.modalElement = document.getElementById(modalElementId);
        this.loadingStateElement = document.getElementById('expenseModalLoading');
        this.errorStateElement = document.getElementById('expenseModalError');
        this.contentStateElement = document.getElementById('expenseModalContent');
        this.errorMessageElement = document.getElementById('expenseModalErrorMessage');
        this.modalTitleElement = document.getElementById('expenseListModalTitle');
        this.totalAmountElement = document.getElementById('expenseListTotalAmount');
        this.expenseCountElement = document.getElementById('expenseListExpenseCount');

        this.currencyFormatter = new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        });
    }

    openModal() {
        this.modalElement.classList.remove('hidden');
        // Prevent body scroll when modal is open
        document.body.style.overflow = 'hidden';
    }

    closeModal() {
        this.modalElement.classList.add('hidden');
        // Restore body scroll
        document.body.style.overflow = '';
    }

    setModalTitle(titleText) {
        this.modalTitleElement.textContent = titleText;
    }

    showLoadingState() {
        this.loadingStateElement.classList.remove('hidden');
        this.errorStateElement.classList.add('hidden');
        this.contentStateElement.classList.add('hidden');
    }

    showErrorState(errorMessage) {
        this.loadingStateElement.classList.add('hidden');
        this.contentStateElement.classList.add('hidden');
        this.errorStateElement.classList.remove('hidden');
        this.errorMessageElement.textContent = errorMessage;
    }

    showContentState(totalAmount, expenseCount) {
        this.loadingStateElement.classList.add('hidden');
        this.errorStateElement.classList.add('hidden');
        this.contentStateElement.classList.remove('hidden');

        this.totalAmountElement.textContent = this.currencyFormatter.format(totalAmount);
        this.expenseCountElement.textContent = expenseCount;
    }
}


// ==============================================================================
// Class 4: Main Modal Controller (Coordinates all components)
// ==============================================================================

class ExpenseListModal {
    /**
     * Main controller that coordinates API client, renderer, and state manager.
     *
     * Single Responsibility: Orchestration of components.
     * Dependency Inversion: Depends on abstractions (injected dependencies).
     */

    constructor(apiClient, stateManager, renderer) {
        this.apiClient = apiClient;
        this.stateManager = stateManager;
        this.renderer = renderer;
        this.setupEventListeners();
    }

    setupEventListeners() {
        const closeButtonElement = document.getElementById('expenseModalCloseBtn');
        const closeFooterButtonElement = document.getElementById('expenseModalCloseFooterBtn');

        closeButtonElement?.addEventListener('click', () => this.close());
        closeFooterButtonElement?.addEventListener('click', () => this.close());

        // Close on background click
        this.stateManager.modalElement?.addEventListener('click', (clickEvent) => {
            if (clickEvent.target === this.stateManager.modalElement) {
                this.close();
            }
        });

        // Close on ESC key
        document.addEventListener('keydown', (keyboardEvent) => {
            if (keyboardEvent.key === 'Escape' &&
                !this.stateManager.modalElement.classList.contains('hidden')) {
                this.close();
            }
        });
    }

    async open(filterType, filterValue, expenseId = null) {
        // Open modal and show loading state
        this.stateManager.openModal();
        this.stateManager.showLoadingState();

        try {
            // Fetch data from API
            const expenseListData = await this.apiClient.fetchExpenseList(
                filterType,
                filterValue,
                expenseId
            );

            // Update modal title with filter info
            if (expenseListData.filter_info && expenseListData.filter_info.title) {
                this.stateManager.setModalTitle(expenseListData.filter_info.title);
            }

            // Display the data
            this.displayExpenseData(expenseListData);

        } catch (fetchError) {
            console.error('Error fetching expense list:', fetchError);
            this.stateManager.showErrorState(
                fetchError.message || 'Falha ao carregar lista de despesas'
            );
        }
    }

    displayExpenseData(expenseListData) {
        // Show content state with summary
        this.stateManager.showContentState(
            expenseListData.total_amount,
            expenseListData.count
        );

        // Render expense list
        this.renderer.renderExpenseList(expenseListData.expenses);
    }

    close() {
        this.stateManager.closeModal();
    }
}
