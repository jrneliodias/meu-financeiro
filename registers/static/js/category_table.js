// Tabela por categoria (aba Categorias): mapa de calor, lista mobile e links para a lista de despesas.
// Lê window.CategoryTableConfig definido no template.
const CFG = window.CategoryTableConfig;
// JavaScript to handle the mobile view functionality and enhanced statistics heatmap
document.addEventListener('DOMContentLoaded', function() {
    // Utility functions
    const utils = {
        // Convert currency string to number
        currencyToNumber: function(currencyStr) {
            return parseFloat(currencyStr.replace('R$ ', '').replace('.', '').replace(',', '.'));
        },
        
        // Get statistical metrics from an array of values
        getStatistics: function(values) {
            if (values.length === 0) return { min: 0, max: 0, range: 0, mean: 0, stdDev: 0, q1: 0, q3: 0, iqr: 0 };
            
            // Basic stats
            const min = Math.min(...values);
            const max = Math.max(...values);
            const range = max - min;
            
            // Mean calculation
            const sum = values.reduce((acc, val) => acc + val, 0);
            const mean = sum / values.length;
            
            // Standard deviation
            const variance = values.reduce((acc, val) => acc + Math.pow(val - mean, 2), 0) / values.length;
            const stdDev = Math.sqrt(variance);
            
            // Quartiles for IQR (Interquartile Range)
            const sortedValues = [...values].sort((a, b) => a - b);
            const q1Index = Math.floor(sortedValues.length * 0.25);
            const q3Index = Math.floor(sortedValues.length * 0.75);
            const q1 = sortedValues[q1Index];
            const q3 = sortedValues[q3Index];
            const iqr = q3 - q1;
            
            return { min, max, range, mean, stdDev, q1, q3, iqr };
        },
        
        // Detect if a value is an outlier using IQR method
        isOutlier: function(value, stats) {
            if (stats.iqr === 0) return false;
            const lowerBound = stats.q1 - 1.5 * stats.iqr;
            const upperBound = stats.q3 + 1.5 * stats.iqr;
            return value < lowerBound || value > upperBound;
        },
        
        // Calculate intensity based on statistical position
        calculateIntensity: function(value, stats) {
            // Z-score based intensity (how many standard deviations from the mean)
            if (stats.stdDev === 0) return 0;
            
            const zScore = (value - stats.mean) / stats.stdDev;
            // Normalize z-score to a 0-1 scale for intensity
            // Using sigmoid function to transform z-score
            return 1 / (1 + Math.exp(-zScore));
        }
    };
    
    // Heatmap configuration
    const heatmapConfig = {
        colors: {
            normal: {
                r: 255,
                g: 193,
                b: 7
            },
            outlier: {
                r: 220,
                g: 53,
                b: 69
            },
            belowMean: {
                r: 40,
                g: 167,
                b: 69
            }
        },
        maxOpacity: 0.7,
        intensityThreshold: 0.6
    };
    
    // Heatmap generator object
    const heatmap = {
        // Apply color to a single cell
        applyColorToCell: function(cell, value, stats) {
            // Determine if this is an outlier
            const isOutlier = utils.isOutlier(value, stats);
            
            // Choose appropriate color based on value and outlier status
            let color;
            if (isOutlier) {
                color = heatmapConfig.colors.outlier;
            } else if (value < stats.mean) {
                color = heatmapConfig.colors.belowMean;
            } else {
                color = heatmapConfig.colors.normal;
            }
            
            // Calculate intensity
            const intensity = utils.calculateIntensity(value, stats);
            
            // Apply background color with appropriate opacity
            const opacity = Math.min(intensity * heatmapConfig.maxOpacity, heatmapConfig.maxOpacity);
            cell.style.backgroundColor = `rgba(${color.r}, ${color.g}, ${color.b}, ${opacity})`;
            
            // Add data attributes for tooltip/explanation
            cell.setAttribute('data-is-outlier', isOutlier);
            cell.setAttribute('data-z-score', ((value - stats.mean) / stats.stdDev).toFixed(2));
            cell.setAttribute('data-vs-mean', value > stats.mean ? 'above' : 'below');
            
            // Adjust text color for better contrast
            cell.style.color = intensity > heatmapConfig.intensityThreshold ? '#000' : 'inherit';
            
            // Add outlier indicator
            if (isOutlier) {
                cell.style.fontWeight = 'bold';
            }
        },
        
        // Process cells for heatmap generation
        processCells: function(cells) {
            // Extract and filter values
            const values = Array.from(cells)
                .map(cell => utils.currencyToNumber(cell.textContent))
                .filter(value => value > 0);
                
            if (values.length === 0) return; // No valid values to create a heatmap
            
            // Get statistical metrics
            const stats = utils.getStatistics(values);
            if (stats.range === 0) return; // All values are the same, no heatmap needed
            
            // Display statistics in console for debugging
            console.log('Expense Statistics:', stats);
            
            // Apply color to each cell
            cells.forEach(cell => {
                const value = utils.currencyToNumber(cell.textContent);
                if (value === 0) return; // Skip zero values
                
                this.applyColorToCell(cell, value, stats);
            });
        },
        
        // Apply heatmap to desktop view (excluding totals row)
        applyToDesktop: function() {
            const cells = document.querySelectorAll('tr:not(:first-child) .heatmap-cell');
            this.processCells(cells);
        },
        
        // Apply heatmap to mobile view (excluding totals row)
        applyToMobile: function() {
            const cells = document.querySelectorAll('#mobileCategoryTableBody tr:not(:first-child) .heatmap-cell');
            this.processCells(cells);
        },
        
        // Add a legend to explain the coloring
        addLegend: function() {
            const legend = document.createElement('div');
            legend.className = "mt-4 text-xs bg-zinc-800 p-3 rounded";
            legend.innerHTML = `
                <p class="font-semibold mb-2">Color Legend:</p>
                <div class="flex flex-wrap gap-3">
                    <div>
                        <span class="inline-block w-3 h-3 mr-1" style="background-color: rgba(255, 193, 7, 0.6);"></span>
                        Above average expense
                    </div>
                    <div>
                        <span class="inline-block w-3 h-3 mr-1" style="background-color: rgba(40, 167, 69, 0.6);"></span>
                        Below average expense
                    </div>
                    <div>
                        <span class="inline-block w-3 h-3 mr-1" style="background-color: rgba(220, 53, 69, 0.6);"></span>
                        Outlier (unusual value)
                    </div>
                </div>
                <p class="mt-2">Intensity indicates how far from the average.</p>
            `;
            
            // Add to both desktop and mobile views
            const desktopTable = document.querySelector('.expense-category-table');
            const mobileTable = document.getElementById('mobileCategoryTable');
            
            if (desktopTable) {
                desktopTable.parentNode.insertBefore(legend.cloneNode(true), desktopTable.nextSibling);
            }
            
            if (mobileTable) {
                mobileTable.parentNode.insertBefore(legend, mobileTable.nextSibling);
            }
        }
    };
    
    // Mobile view manager
    const mobileView = {
        // DOM elements
        elements: {
            selector: null,
            header: null,
            tableBody: null,
            totalCell: null,
            statsDisplay: null
        },
        
        // Data storage
        data: {
            months: [],
            categories: {},
            totals: []
        },
        
        // Initialize mobile view
        init: function() {
            // Only run on mobile screens
            if (window.innerWidth >= 768) return false;

            // Get DOM elements
            this.elements.selector = document.getElementById('monthSelector');
            this.elements.header = document.getElementById('selectedMonthHeader');
            this.elements.tableBody = document.getElementById('mobileCategoryTableBody');
            this.elements.totalCell = document.getElementById('selectedMonthTotal');

            // Format data for JavaScript
            this.data.months = CFG.months;
            this.data.categories = CFG.categories;
            this.data.totals = CFG.totals;

            // Pre-select the month from the top filter
            if (this.data.months.length > 0) {
                const selectedMonthNum = this.elements.selector.dataset.selectedMonth;

                if (selectedMonthNum) {
                    // Convert month number (1-12) to array index (0-11)
                    const monthIndex = parseInt(selectedMonthNum) - 1;

                    // Check if this index is valid for our months array
                    if (monthIndex >= 0 && monthIndex < this.data.months.length) {
                        this.elements.selector.selectedIndex = monthIndex;
                    } else {
                        // Fallback: select the last month
                        this.elements.selector.selectedIndex = this.data.months.length - 1;
                    }
                } else {
                    // Fallback: select the last month
                    this.elements.selector.selectedIndex = this.data.months.length - 1;
                }
            }

            // Add event listeners
            this.elements.selector.addEventListener('change', () => this.updateTable());

            // Create stats display area
            this.createStatsDisplay();

            // Initial load
            this.updateTable();
            return true;
        },
        
        // Create statistics display
        createStatsDisplay: function() {
            const statsDisplay = document.createElement('div');
            statsDisplay.id = 'mobileStatsDisplay';
            statsDisplay.className = 'mt-3 text-xs bg-zinc-800 p-2 rounded';
            statsDisplay.innerHTML = '<h4 class="font-semibold">Monthly Statistics</h4><div id="statsContent"></div>';
            
            this.elements.statsDisplay = statsDisplay;
            this.elements.selector.parentNode.insertBefore(statsDisplay, this.elements.selector.nextSibling);
        },
        
        // Update statistics display
        updateStats: function(selectedIndex) {
            // Collect all values for the selected month
            const values = Object.values(this.data.categories)
                .map(categoryValues => utils.currencyToNumber(categoryValues[selectedIndex]))
                .filter(value => value > 0);
            
            if (values.length === 0) {
                this.elements.statsDisplay.style.display = 'none';
                return;
            }
            
            // Calculate statistics
            const stats = utils.getStatistics(values);
            
            // Format currency values
            const formatCurrency = (value) => 'R$ ' + value.toLocaleString('pt-BR', {minimumFractionDigits: 2});
            
            // Update stats display
            const statsContent = document.getElementById('statsContent');
            statsContent.innerHTML = `
                <div class="grid grid-cols-2 gap-1">
                    <div>Média: ${formatCurrency(stats.mean)}</div>
                    <div>Mediana: ${formatCurrency(values.sort((a,b) => a-b)[Math.floor(values.length/2)])}</div>
                    <div>Mínimo: ${formatCurrency(stats.min)}</div>
                    <div>Máximo: ${formatCurrency(stats.max)}</div>
                    <div>Total: ${this.data.totals[selectedIndex]}</div>
                </div>
            `;
            
            this.elements.statsDisplay.style.display = 'block';
        },
        
        // Update the table based on selected month
        updateTable: function() {
            const selectedIndex = parseInt(this.elements.selector.value);
            
            // Update header
            this.elements.header.textContent = this.data.months[selectedIndex];
            
            // Update total
            this.elements.totalCell.textContent = this.data.totals[selectedIndex];
            this.elements.totalCell.setAttribute('data-value', this.data.totals[selectedIndex]);
            
            // Update statistics
            this.updateStats(selectedIndex);
            
            // Clear existing category rows (except the total row)
            const totalRow = this.elements.tableBody.querySelector('tr');
            this.elements.tableBody.innerHTML = '';
            this.elements.tableBody.appendChild(totalRow);
            
            // Add category rows for selected month
            for (const [category, values] of Object.entries(this.data.categories)) {
                const value = values[selectedIndex];
                this.addCategoryRow(category, value);
            }
            
            // Apply heatmap
            heatmap.applyToMobile();
        },
        
        // Add a new category row to the table
        addCategoryRow: function(category, value) {
            const row = document.createElement('tr');
            row.className = "*:p-2 border-b border-zinc-700";
            
            // Create category cell
            const categoryCell = document.createElement('td');
            categoryCell.className = "font-medium";
            categoryCell.textContent = category;
            
            // Create value cell
            const valueCell = document.createElement('td');
            valueCell.className = value === 'R$ 0,00' ? "text-left text-zinc-600 heatmap-cell" : "text-left heatmap-cell";
            valueCell.textContent = value;
            valueCell.setAttribute('data-value', value);
            
            // Add cells to row
            row.appendChild(categoryCell);
            row.appendChild(valueCell);
            
            // Add row to table
            this.elements.tableBody.appendChild(row);
        }
    };
    
    // Initialize views based on screen size
    if (!mobileView.init()) {
        // Desktop view - apply heatmap directly
        heatmap.applyToDesktop();
        
        // Create stats display for desktop
        const desktopTable = document.querySelector('.expense-category-table');
        if (desktopTable) {
            // Calculate stats for desktop view (all visible cells)
            const cells = document.querySelectorAll('tr:not(:first-child) .heatmap-cell');
            const values = Array.from(cells)
                .map(cell => utils.currencyToNumber(cell.textContent))
                .filter(value => value > 0);
            
            if (values.length > 0) {
                const stats = utils.getStatistics(values);
                
                // Format currency values
                const formatCurrency = (value) => 'R$ ' + value.toLocaleString('pt-BR', {minimumFractionDigits: 2});
                
                // Create stats display
                const statsDisplay = document.createElement('div');
                statsDisplay.className = 'mt-3 text-xs bg-zinc-800 p-2 rounded';
                statsDisplay.innerHTML = `
                    <h4 class="font-semibold">Estatísticas Gerais</h4>
                    <div class="grid grid-cols-5 gap-2 mt-1">
                        <div>Média: ${formatCurrency(stats.mean)}</div>
                        <div>Mediana: ${formatCurrency(values.sort((a,b) => a-b)[Math.floor(values.length/2)])}</div>
                        <div>Mínimo: ${formatCurrency(stats.min)}</div>
                        <div>Máximo: ${formatCurrency(stats.max)}</div>
                        <div>Desvio Padrão: ${formatCurrency(stats.stdDev)}</div>
                    </div>
                `;
                
                desktopTable.parentNode.insertBefore(statsDisplay, desktopTable);
            }
        }
    }
    
    // Add legend to explain colors
    heatmap.addLegend();
});

// ================================================================================
// Clique numa célula (categoria x mês) abre a página de lista de despesas
// ================================================================================
class CategoryTableClickHandler {
    /**
     * Handles click events on category table cells.
     *
     * Single Responsibility: Event handling and delegation only.
     */

    constructor(selectedYear, monthNamesArray, categoryIds) {
        this.selectedYear = selectedYear;
        this.monthNamesArray = monthNamesArray;
        this.categoryIds = categoryIds;
    }

    openExpenseList(categoryName, monthName) {
        const categoryId = this.categoryIds[categoryName];
        const month = this.monthNamesArray.indexOf(monthName) + 1;
        if (!categoryId || !month) return;
        const back = encodeURIComponent(location.pathname + location.search);
        location.href = `/despesas/lista/?category_id=${categoryId}&month=${month}&year=${this.selectedYear}&back=${back}`;
    }

    attachDesktopTableClickHandlers() {
        const desktopTableRows = document.querySelectorAll('table.hidden.md\\:table tbody tr');

        desktopTableRows.forEach(categoryRow => {
            const categoryNameCell = categoryRow.querySelector('td:first-child');
            if (!categoryNameCell) return;

            const categoryName = categoryNameCell.textContent.trim();
            if (categoryName === 'Total') return; // Skip total row

            const monthlyCells = categoryRow.querySelectorAll('td:not(:first-child)');
            monthlyCells.forEach((monthlyAmountCell, monthIndex) => {
                this.makeClickableIfHasValue(
                    monthlyAmountCell,
                    categoryName,
                    this.monthNamesArray[monthIndex]
                );
            });
        });
    }

    attachMobileTableClickHandlers() {
        const mobileTableRows = document.querySelectorAll('#mobileCategoryTableBody tr');
        const monthSelectorElement = document.getElementById('monthSelector');
        const selectedMonthIndex = parseInt(monthSelectorElement?.value || 0);
        const currentMonthName = this.monthNamesArray[selectedMonthIndex];

        mobileTableRows.forEach(categoryRow => {
            const categoryNameCell = categoryRow.querySelector('td:first-child');
            const monthlyAmountCell = categoryRow.querySelector('td:last-child');

            if (!categoryNameCell || !monthlyAmountCell) return;

            const categoryName = categoryNameCell.textContent.trim();
            if (categoryName === 'Total') return;

            // Clone cell to remove old event listeners
            const freshAmountCell = monthlyAmountCell.cloneNode(true);
            monthlyAmountCell.parentNode.replaceChild(freshAmountCell, monthlyAmountCell);

            this.makeClickableIfHasValue(freshAmountCell, categoryName, currentMonthName);
        });
    }

    makeClickableIfHasValue(tableCellElement, categoryName, monthName) {
        const cellDisplayValue = tableCellElement.textContent.trim();
        const ZERO_VALUE_DISPLAY = 'R$ 0,00';

        if (cellDisplayValue && cellDisplayValue !== ZERO_VALUE_DISPLAY) {
            tableCellElement.style.cursor = 'pointer';
            tableCellElement.classList.add(
                'hover:bg-blue-900/30',
                'hover:scale-105',
                'hover:shadow-lg',
                'hover:shadow-blue-500/20',
                'transition-all',
                'duration-200',
                'rounded',
                'relative',
                'group'
            );
            tableCellElement.title = 'Click to view expense details';

            // Add visual indicator icon
            const currentText = tableCellElement.innerHTML;
            tableCellElement.innerHTML = `
                <span class="inline-flex items-center gap-1">
                    ${currentText}
                    <i class="fas fa-eye text-xs text-blue-400 opacity-0 group-hover:opacity-100 transition-opacity duration-200"></i>
                </span>
            `;

            tableCellElement.addEventListener('click', () => {
                this.openExpenseList(categoryName, monthName);
            });
        }
    }

    initializeMobileHandlers() {
        const MOBILE_BREAKPOINT_WIDTH = 768;
        const DEBOUNCE_DELAY_MS = 100;

        if (window.innerWidth < MOBILE_BREAKPOINT_WIDTH) {
            setTimeout(() => this.attachMobileTableClickHandlers(), DEBOUNCE_DELAY_MS);

            const monthSelectorElement = document.getElementById('monthSelector');
            monthSelectorElement?.addEventListener('change', () => {
                setTimeout(() => this.attachMobileTableClickHandlers(), DEBOUNCE_DELAY_MS);
            });
        }
    }
}


// ================================================================================
// Initialization
// ================================================================================

// Wait for DOM to be fully loaded before initializing
document.addEventListener('DOMContentLoaded', () => {
    const categoryIds = JSON.parse(document.getElementById('category-ids').textContent);
    const categoryTableClickHandler = new CategoryTableClickHandler(CFG.year, CFG.months, categoryIds);

    // Attach event handlers
    categoryTableClickHandler.attachDesktopTableClickHandlers();
    categoryTableClickHandler.initializeMobileHandlers();
});
