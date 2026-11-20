// Daily spending chart (Gastos tab). URLs, labels and the outlier threshold come from data-* on
// #daily-spending-chart; the page ships the series for the period <option> marked `selected`.
(() => {
  const root = document.getElementById('daily-spending-chart');
  const period = document.getElementById('dailyChartPeriod');
  const category = document.getElementById('dailyCategoryFilter');
  const type = document.getElementById('dailyChartType');
  const scale = document.getElementById('dailyChartScale');
  const outlierMode = document.getElementById('outlierHandling');
  const loading = root.querySelector('[data-loading]');
  const error = root.querySelector('[data-error]');
  const threshold = Number(root.dataset.outlierThreshold);
  const isOutlier = (value) => value > threshold;
  const dayMonth = (isoDate) => { const [, month, day] = isoDate.split('-'); return `${day}/${month}`; };
  const LOG_TICKS = [1, 10, 100, 1000, 10000];
  let data = JSON.parse(document.getElementById('daily-spending-data').textContent);

  const daily = {
    label: root.dataset.labelDaily,
    backgroundColor: 'rgba(96, 165, 250, 0.2)', borderColor: 'rgba(96, 165, 250, 1)', borderWidth: 2,
    pointHoverRadius: 6,
  };
  const average = {
    label: root.dataset.labelAverage,
    backgroundColor: 'rgba(255, 99, 132, 0.1)', borderColor: 'rgba(255, 99, 132, 1)', borderWidth: 1,
    borderDash: [5, 5], tension: 0.4, fill: false, pointHoverRadius: 4,
  };
  const outliers = {
    label: `${root.dataset.labelOutliers} (>${App.brl(threshold, 0)})`,
    backgroundColor: 'rgba(255, 99, 132, 0.3)', borderColor: 'rgba(255, 99, 132, 1)', borderWidth: 3,
    pointRadius: 6, pointHoverRadius: 8, tension: 0, fill: false,
  };
  const white = { color: 'white', font: { size: 11 } };
  const grid = { color: 'rgba(255, 255, 255, 0.1)' };

  const chart = new Chart(root.querySelector('canvas'), {
    type: type.value,
    data: { labels: [], datasets: [] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { intersect: false, mode: 'index' },
      onClick: (event, elements) => {
        if (!elements.length) return;
        const query = new URLSearchParams({
          date: data.labels[elements[0].index], back: location.pathname + location.search,
        });
        location.href = `${root.dataset.dayUrl}?${query}`;
      },
      plugins: {
        legend: { position: 'top', labels: { color: 'white', font: { size: 12 }, usePointStyle: true, padding: 20 } },
        tooltip: {
          backgroundColor: 'rgba(0, 0, 0, 0.8)', titleColor: 'white', bodyColor: 'white',
          borderColor: 'rgba(96, 165, 250, 1)', borderWidth: 1,
          callbacks: { label: (item) => `${item.dataset.label}: ${App.brl(item.parsed.y)}` },
        },
      },
      scales: {
        x: { ticks: { ...white, maxTicksLimit: 10 }, grid },
        y: {
          grid,
          ticks: {
            ...white,
            // `this` is the scale; a log axis would otherwise label every minor step.
            callback(value) { return this.type === 'logarithmic' && !LOG_TICKS.includes(value) ? '' : App.brl(value, 0); },
          },
        },
      },
    },
  });

  // Rebuilds the chart from `data` and the current state of every selector.
  function draw() {
    const bar = type.value === 'bar';
    const mode = outlierMode.value;
    chart.config.type = type.value;
    chart.data.labels = data.labels.map(dayMonth);
    Object.assign(daily, bar ? { tension: 0, fill: false, pointRadius: 0 } : { tension: 0.4, fill: true, pointRadius: 3 });
    daily.data = mode === 'show' ? data.dailyExpenses : data.dailyExpenses.map((v) => (isOutlier(v) ? null : v));
    average.pointRadius = bar ? 0 : 2;
    average.data = mode === 'separate'
      ? data.movingAverages.map((v, i) => (isOutlier(v) || isOutlier(data.dailyExpenses[i]) ? null : v))
      : data.movingAverages;
    outliers.data = data.dailyExpenses.map((v) => (isOutlier(v) ? v : null));
    chart.data.datasets = mode === 'highlight' ? [daily, average, outliers] : [daily, average];
    chart.options.scales.y.type = scale.value;
    chart.options.scales.y.min = scale.value === 'logarithmic' ? 1 : 0;
    chart.update('active');
  }

  function load() {
    loading.hidden = false;
    error.hidden = true;
    const query = new URLSearchParams({ days: period.value, category_id: category.value });
    fetch(`${root.dataset.url}?${query}`)
      .then((response) => (response.ok ? response.json() : Promise.reject(response)))
      .then((json) => { data = json; draw(); }, () => { error.hidden = false; })
      .finally(() => { loading.hidden = true; });
  }

  period.addEventListener('change', load);
  category.addEventListener('change', load);
  [type, scale, outlierMode].forEach((select) => select.addEventListener('change', draw));

  // Phones start on the shortest period. Back/forward navigation can also restore other choices
  // into the selects; anything but the shipped series is fetched instead of drawn twice.
  if (matchMedia('(max-width: 767px)').matches) period.value = period.options[0].value;
  if (period.selectedOptions[0].defaultSelected && !category.value) draw();
  else load();
})();
