// Gráfico de gasto diário (aba Gastos). Lê window.DailyChartI18n e #daily-spending-data.
const dc = window.DailyChartI18n;

// Debug function to show data information
function showDebugInfo(data, message) {
  const debugDiv = document.getElementById('debugInfo');
  const debugContent = document.getElementById('debugContent');

  debugDiv.style.display = 'block';
  debugContent.innerHTML = `
    <p><strong>Message:</strong> ${message}</p>
    <p><strong>Data Type:</strong> ${typeof data}</p>
    <p><strong>Data:</strong> <pre>${JSON.stringify(data, null, 2)}</pre></p>
  `;
}

class DailySpendingChart {
  constructor(canvasId, initialData) {
    this.canvasId = canvasId;
    this.chart = null;
    this.data = initialData;
    this.colors = {
      primary: {
        backgroundColor: 'rgba(96, 165, 250, 0.2)',
        borderColor: 'rgba(96, 165, 250, 1)',
        borderWidth: 2
      },
      trend: {
        backgroundColor: 'rgba(255, 99, 132, 0.1)',
        borderColor: 'rgba(255, 99, 132, 1)',
        borderWidth: 1
      }
    };

    this.currentDays = 30;
    this.currentCategory = '';
    this.initializeChart();
    this.setupEventListeners();
  }

  initializeChart() {
    const ctx = document.getElementById(this.canvasId);
    if (!ctx) {
      console.error('Canvas element not found:', this.canvasId);
      return;
    }

    // Validate data
    if (!this.data || !this.data.labels || !this.data.dailyExpenses) {
      console.error('Invalid data structure:', this.data);
      showDebugInfo(this.data, 'Invalid data structure');
      return;
    }

    // Store original labels for tooltip access
    this.originalLabels = this.data.labels;

    // Format dates for better display - fix timezone issues
    const formattedLabels = this.data.labels.map(dateStr => {
      try {
        // Parse date string directly to avoid timezone issues
        const [year, month, day] = dateStr.split('-');
        const date = new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
        return date.toLocaleDateString('pt-BR', {
          day: '2-digit',
          month: '2-digit'
        });
      } catch (e) {
        console.warn('Date formatting error for:', dateStr, e);
        return dateStr;
      }
    });

    this.chart = new Chart(ctx.getContext('2d'), {
      type: 'line',
      data: {
        labels: formattedLabels,
        datasets: [{
          label: dc.dailySpending,
          data: this.data.dailyExpenses,
          backgroundColor: this.colors.primary.backgroundColor,
          borderColor: this.colors.primary.borderColor,
          borderWidth: this.colors.primary.borderWidth,
          tension: 0.4,
          fill: true,
          pointRadius: 3,
          pointHoverRadius: 6
        }, {
          label: dc.sevenDayAverage,
          data: this.data.movingAverages || [],
          backgroundColor: this.colors.trend.backgroundColor,
          borderColor: this.colors.trend.borderColor,
          borderWidth: this.colors.trend.borderWidth,
          borderDash: [5, 5],
          tension: 0.4,
          fill: false,
          pointRadius: 2,
          pointHoverRadius: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          intersect: false,
          mode: 'index'
        },
        onClick: (event, elements) => {
          // Handle chart point clicks: abre a lista de despesas do dia
          if (elements.length > 0) {
            const pointIndex = elements[0].index;
            const clickedDate = this.originalLabels[pointIndex]; // Use original date format (YYYY-MM-DD)
            this.showExpenseDetails(clickedDate);
          }
        },
        plugins: {
          legend: {
            display: true,
            position: 'top',
            labels: {
              color: 'white',
              font: { size: 12 },
              usePointStyle: true,
              padding: 20
            }
          },
          tooltip: {
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            titleColor: 'white',
            bodyColor: 'white',
            borderColor: 'rgba(96, 165, 250, 1)',
            borderWidth: 1,
            callbacks: {
              title: function(context) {
                // Simple approach: just show the formatted date from the chart
                return context[0].label || dc.dateLabel;
              },
              label: function(context) {
                return context.dataset.label + ': ' +
                  new Intl.NumberFormat('pt-BR', {
                    style: 'currency',
                    currency: 'BRL'
                  }).format(context.parsed.y);
              }
            }
          }
        },
        scales: {
          x: {
            display: true,
            ticks: {
              color: 'white',
              maxTicksLimit: 10,
              font: { size: 11 }
            },
            grid: {
              color: 'rgba(255, 255, 255, 0.1)'
            }
          },
          y: {
            display: true,
            beginAtZero: true,
            ticks: {
              color: 'white',
              font: { size: 11 },
              callback: function(value) {
                return new Intl.NumberFormat('pt-BR', {
                  style: 'currency',
                  currency: 'BRL',
                  minimumFractionDigits: 0,
                  maximumFractionDigits: 0
                }).format(value);
              }
            },
            grid: {
              color: 'rgba(255, 255, 255, 0.1)'
            }
          }
        }
      }
    });
  }

  setupEventListeners() {
    const periodSelector = document.getElementById('dailyChartPeriod');
    if (periodSelector) {
      periodSelector.addEventListener('change', (e) => {
        this.updateChartPeriod(parseInt(e.target.value));
      });
    }

    const typeSelector = document.getElementById('dailyChartType');
    if (typeSelector) {
      typeSelector.addEventListener('change', (e) => {
        this.updateChartType(e.target.value);
      });
    }

    const scaleSelector = document.getElementById('dailyChartScale');
    if (scaleSelector) {
      scaleSelector.addEventListener('change', (e) => {
        this.updateChartScale(e.target.value);
      });
    }

    const outlierSelector = document.getElementById('outlierHandling');
    if (outlierSelector) {
      outlierSelector.addEventListener('change', (e) => {
        this.updateOutlierHandling(e.target.value);
      });
    }

    const categorySelector = document.getElementById('dailyCategoryFilter');
    if (categorySelector) {
      categorySelector.addEventListener('change', (e) => {
        this.updateChartCategory(e.target.value);
      });
    }
  }

  fetchAndUpdate(days, categoryId = '') {
    const canvas = document.getElementById('dailySpendingChart');
    const loadingDiv = document.createElement('div');
    loadingDiv.id = 'loadingIndicator';
    loadingDiv.className = 'absolute inset-0 bg-zinc-800 bg-opacity-90 flex items-center justify-center text-white z-10';
    loadingDiv.innerHTML = `<div class="text-center"><div class="animate-spin rounded-full h-8 w-8 border-b-2 border-white mx-auto mb-2"></div>${dc.loadingData}</div>`;

    const canvasContainer = canvas.parentElement;
    canvasContainer.style.position = 'relative';
    canvasContainer.appendChild(loadingDiv);

    let url = `/daily-spending-data/?days=${days}`;
    if (categoryId) url += `&category_id=${categoryId}`;

    fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
      }
    })
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .then(newData => {
      const loadingIndicator = document.getElementById('loadingIndicator');
      if (loadingIndicator) loadingIndicator.remove();
      this.updateData(newData);
    })
    .catch(error => {
      console.error('Error fetching new data:', error);
      const loadingIndicator = document.getElementById('loadingIndicator');
      if (loadingIndicator) loadingIndicator.remove();
      alert(dc.errorLoadingData);
    });
  }

  updateChartPeriod(days) {
    this.currentDays = days;
    this.fetchAndUpdate(days, this.currentCategory);
  }

  updateChartCategory(categoryId) {
    this.currentCategory = categoryId;
    this.fetchAndUpdate(this.currentDays, categoryId);
  }

  updateChartType(type) {
    if (!this.chart) return;

    this.chart.config.type = type;

    if (type === 'bar') {
      this.chart.data.datasets[0].tension = 0;
      this.chart.data.datasets[0].fill = false;
      this.chart.data.datasets[0].pointRadius = 0;
      this.chart.data.datasets[1].pointRadius = 0;
    } else {
      this.chart.data.datasets[0].tension = 0.4;
      this.chart.data.datasets[0].fill = true;
      this.chart.data.datasets[0].pointRadius = 3;
      this.chart.data.datasets[1].pointRadius = 2;
    }

    this.chart.update('active');
  }

  updateChartScale(scaleType) {
    if (!this.chart) return;

    // Update the Y-axis scale type
    this.chart.options.scales.y.type = scaleType;

    if (scaleType === 'logarithmic') {
      // Configure logarithmic scale
      this.chart.options.scales.y.min = 1; // Start from 1 to avoid log(0)
      this.chart.options.scales.y.ticks.callback = function(value) {
        // Format logarithmic scale labels
        if (value === 1 || value === 10 || value === 100 || value === 1000 || value === 10000) {
          return new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
          }).format(value);
        }
        return '';
      };
    } else {
      // Reset to linear scale
      this.chart.options.scales.y.min = 0;
      this.chart.options.scales.y.ticks.callback = function(value) {
        return new Intl.NumberFormat('pt-BR', {
          style: 'currency',
          currency: 'BRL',
          minimumFractionDigits: 0,
          maximumFractionDigits: 0
        }).format(value);
      };
    }

    this.chart.update('active');
  }

  updateOutlierHandling(outlierType) {
    if (!this.chart || !this.data) return;

    // Fixed outlier threshold - change this value to adjust what's considered an outlier
    const outlierThreshold = 1000; // R$ 1,000 and above are considered outliers

    if (outlierType === 'highlight') {
      // Create separate datasets for normal and outlier data
      const normalData = [];
      const outlierData = [];

      this.data.dailyExpenses.forEach((value, index) => {
        if (value > outlierThreshold) {
          normalData.push(null);
          outlierData.push(value);
        } else {
          normalData.push(value);
          outlierData.push(null);
        }
      });

      // Update datasets
      this.chart.data.datasets[0].data = normalData;

      // Add or update outlier dataset
      if (this.chart.data.datasets.length < 3) {
        this.chart.data.datasets.push({
          label: dc.outliersLabel,
          data: outlierData,
          backgroundColor: 'rgba(255, 99, 132, 0.3)',
          borderColor: 'rgba(255, 99, 132, 1)',
          borderWidth: 3,
          pointRadius: 6,
          pointHoverRadius: 8,
          tension: 0,
          fill: false
        });
      } else {
        this.chart.data.datasets[2].data = outlierData;
      }

    } else if (outlierType === 'separate') {
      // Filter out outliers from main dataset (both expenses and moving averages)
      const filteredData = this.data.dailyExpenses.map(value =>
        value > outlierThreshold ? null : value
      );
      const filteredMovingAverages = this.data.dailyExpenses.map((value, index) => {
        const movingAvgValue = (this.data.movingAverages || [])[index];
        // Hide if either daily expense OR moving average is above threshold
        return (value > outlierThreshold || movingAvgValue > outlierThreshold) ? null : movingAvgValue;
      });

      this.chart.data.datasets[0].data = filteredData;
      this.chart.data.datasets[1].data = filteredMovingAverages;

      // Remove outlier dataset if it exists
      if (this.chart.data.datasets.length > 2) {
        this.chart.data.datasets.splice(2, 1);
      }

    } else {
      // Show all data normally
      this.chart.data.datasets[0].data = this.data.dailyExpenses;

      // Remove outlier dataset if it exists
      if (this.chart.data.datasets.length > 2) {
        this.chart.data.datasets.splice(2, 1);
      }
    }

    this.chart.update('active');
  }

  updateData(newData) {
    if (!this.chart) {
      console.error('Chart not initialized - cannot update data');
      return;
    }

    if (!newData || !newData.labels || !newData.dailyExpenses) {
      console.error('Invalid data structure received:', newData);
      return;
    }

    try {
      this.data = newData;
      this.originalLabels = newData.labels;

      // Format new labels - fix timezone issues
      const formattedLabels = newData.labels.map(dateStr => {
        try {
          // Parse date string directly to avoid timezone issues
          const [year, month, day] = dateStr.split('-');
          const date = new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
          return date.toLocaleDateString('pt-BR', {
            day: '2-digit',
            month: '2-digit'
          });
        } catch (e) {
          console.warn('Date formatting error for:', dateStr, e);
          return dateStr;
        }
      });

      // Update chart data
      this.chart.data.labels = formattedLabels;
      this.chart.data.datasets[0].data = newData.dailyExpenses;
      this.chart.data.datasets[1].data = newData.movingAverages || [];

      // Reapply current outlier handling after data update
      const outlierSelect = document.getElementById('outlierHandling');
      if (outlierSelect) {
        this.updateOutlierHandling(outlierSelect.value);
      }

      // Force chart update
      this.chart.update('active');

    } catch (error) {
      console.error('Error updating chart data:', error);
    }
  }

  // Os detalhes do dia vivem numa página própria (sem modal).
  showExpenseDetails(dateString) {
    if (!dateString) return;
    const back = encodeURIComponent(location.pathname + location.search);
    location.href = `/despesas/lista/?date=${dateString}&back=${back}`;
  }
}

// Initialize the chart with proper JSON handling
try {
  // Use Django's json_script filter for safe JSON handling
  const dailySpendingDataElement = document.getElementById('daily-spending-data');
  if (!dailySpendingDataElement) {
    throw new Error('Daily spending data script element not found');
  }
  const dailySpendingData = JSON.parse(dailySpendingDataElement.textContent);

  // Validate data structure
  if (!dailySpendingData) {
    throw new Error('No data received from Django');
  }

  if (typeof dailySpendingData !== 'object') {
    throw new Error('Data is not an object: ' + typeof dailySpendingData);
  }

  if (!dailySpendingData.labels) {
    throw new Error('Missing labels in data');
  }

  if (!dailySpendingData.dailyExpenses) {
    throw new Error('Missing dailyExpenses in data');
  }

  console.log('Data validation passed, initializing chart...');
  const dailyChart = new DailySpendingChart('dailySpendingChart', dailySpendingData);
  window.showExpenseDetailsForDate = (date) => dailyChart.showExpenseDetails(date);

  // On mobile (< 768px), default to 7 days instead of 30
  if (window.innerWidth < 768) {
    const periodSelector = document.getElementById('dailyChartPeriod');
    if (periodSelector) {
      periodSelector.value = '7';
    }
    dailyChart.updateChartPeriod(7);
  }

} catch (error) {
  console.error('Error initializing daily spending chart:', error);

  {
    showDebugInfo({
      error: error.message,
      stack: error.stack,
      elementFound: !!document.getElementById('daily-spending-data'),
      elementContent: document.getElementById('daily-spending-data')?.textContent || 'No content'
    }, 'Chart initialization error');

    // Show error message to user
    const chartContainer = document.getElementById('dailySpendingChart').parentElement;
    chartContainer.innerHTML = `
      <div class="text-center text-red-400 p-8">
        <h3 class="text-lg font-bold mb-2">${dc.errorLoadingChart}</h3>
        <p class="text-sm">${error.message}</p>
        <p class="text-xs mt-2">${dc.checkConsole}</p>
        <button onclick="document.getElementById('debugInfo').style.display='block'" class="mt-2 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700">
          ${dc.showDebugInfo}
        </button>
      </div>
    `;
  }
}
