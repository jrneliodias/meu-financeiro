/**
 * ExpenseCardRenderer - Reusable component for rendering expense cards and table rows
 *
 * This class provides a centralized way to render expense data in both:
 * - Mobile-friendly card layout
 * - Desktop table row layout
 *
 * Follows DRY principle by eliminating duplicated rendering logic across:
 * - Recent expenses section
 * - Expense list modal
 * - Future features
 */
class ExpenseCardRenderer {
    constructor() {
        this.currencyFormatter = new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        });
        this.dateFormatter = new Intl.DateTimeFormat('pt-BR');
    }

    /**
     * Renders a mobile-friendly expense card
     * Structure matches recent_expenses.js lines 140-162
     *
     * @param {Object} expense - Expense data object
     * @returns {HTMLElement} Card element
     */
    renderCard(expense) {
        const card = document.createElement('div');
        card.className = 'bg-zinc-700/30 rounded-lg p-4 flex flex-col gap-2';
        card.setAttribute('data-expense-id', expense.id);

        const sanitizedDescription = this.sanitizeHtml(expense.description);
        const amountFormatted = expense.amount_formatted || this.currencyFormatter.format(expense.amount);
        const dateFormatted = expense.date_formatted || this.formatDate(expense.date);

        card.innerHTML = `
            <p class="text-white font-semibold text-base">${sanitizedDescription}</p>
            <p class="text-green-400 font-bold text-xl">${amountFormatted}</p>
            <p class="text-gray-400 text-sm">${dateFormatted}</p>
            ${expense.payment_method_name ? `
                <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-600 text-blue-100 w-fit">
                    ${this.sanitizeHtml(expense.payment_method_name)}
                </span>
            ` : ''}
            <div class="grid grid-cols-2 gap-2 mt-2 pt-2 border-t border-zinc-600">
                <a href="/expense/${expense.id}/update/"
                   class="flex items-center justify-center gap-2 bg-yellow-600 hover:bg-yellow-700 text-white py-2 px-4 rounded-lg text-sm transition-colors">
                    <i class="fas fa-edit"></i>Editar
                </a>
                <button type="button"
                        class="delete-expense-btn flex items-center justify-center gap-2 bg-red-600 hover:bg-red-700 text-white py-2 px-4 rounded-lg text-sm transition-colors"
                        data-expense-id="${expense.id}"
                        data-expense-description="${sanitizedDescription}">
                    <i class="fas fa-trash"></i>Excluir
                </button>
            </div>
        `;

        return card;
    }

    /**
     * Renders a desktop table row for expense data
     * Structure matches expense_category_table.html lines 744-788
     *
     * @param {Object} expense - Expense data object
     * @returns {HTMLElement} Table row element
     */
    renderTableRow(expense) {
        const row = document.createElement('tr');
        row.className = 'hover:bg-zinc-600 transition-colors duration-150';
        row.setAttribute('data-expense-id', expense.id);

        const sanitizedDescription = this.sanitizeHtml(expense.description);
        const sanitizedPaymentMethod = this.sanitizeHtml(expense.payment_method_name || '');
        const dateFormatted = expense.date_formatted || this.formatDate(expense.date);
        const amountFormatted = expense.amount_formatted || this.currencyFormatter.format(expense.amount);

        row.innerHTML = `
            <td class="px-4 py-3 text-gray-300 text-sm">${dateFormatted}</td>
            <td class="px-4 py-3">
                <div class="font-medium text-white">${sanitizedDescription}</div>
            </td>
            <td class="px-4 py-3">
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-600 text-blue-100">
                    ${sanitizedPaymentMethod}
                </span>
            </td>
            <td class="px-4 py-3 text-right">
                <span class="font-semibold text-green-400">
                    ${amountFormatted}
                </span>
            </td>
            <td class="px-4 py-3 text-center">
                <div class="flex items-center justify-center gap-3">
                    <a href="/expense/${expense.id}/update/"
                       class="text-yellow-400 hover:text-yellow-300 transition-colors duration-200"
                       title="Editar despesa">
                        <i class="fas fa-edit"></i>
                    </a>
                    <button class="delete-expense-btn text-red-400 hover:text-red-300 transition-colors duration-200"
                            data-expense-id="${expense.id}"
                            data-expense-description="${sanitizedDescription}"
                            title="Excluir despesa">
                        <i class="fas fa-trash-alt"></i>
                    </button>
                </div>
            </td>
        `;

        return row;
    }

    /**
     * Format date to Brazilian format (DD/MM/YYYY)
     *
     * @param {string} dateString - ISO date string (YYYY-MM-DD)
     * @returns {string} Formatted date
     */
    formatDate(dateString) {
        if (!dateString) return '';

        try {
            const date = new Date(dateString + 'T00:00:00');
            return this.dateFormatter.format(date);
        } catch (e) {
            return dateString;
        }
    }

    /**
     * Sanitize HTML content to prevent XSS attacks
     *
     * @param {string} text - Text to sanitize
     * @returns {string} Sanitized HTML
     */
    sanitizeHtml(text) {
        if (!text) return '';

        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}
