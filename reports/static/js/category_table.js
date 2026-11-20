// Categorias tab: heat-map colours from each cell's data-amount, and the mobile month switcher.
(() => {
  const root = document.querySelector('[data-category-table]');
  if (!root) return;

  const COLORS = { normal: '255, 193, 7', outlier: '220, 53, 69', belowMean: '40, 167, 69' };
  const MAX_OPACITY = 0.7;
  const DARK_TEXT_INTENSITY = 0.6;

  function statistics(values) {
    const sorted = [...values].sort((a, b) => a - b);
    const mean = values.reduce((sum, v) => sum + v, 0) / values.length;
    const stdDev = Math.sqrt(values.reduce((sum, v) => sum + (v - mean) ** 2, 0) / values.length);
    const q1 = sorted[Math.floor(sorted.length * 0.25)];
    const q3 = sorted[Math.floor(sorted.length * 0.75)];
    return {
      mean, stdDev, q1, q3, iqr: q3 - q1,
      min: sorted[0], max: sorted[sorted.length - 1], median: sorted[Math.floor(sorted.length / 2)],
    };
  }

  // Colour each non-zero amount cell by how far it is from the others (IQR outliers in red).
  function paint(container) {
    const cells = [...container.querySelectorAll('.heatmap-cell')]
      .map((cell) => ({ cell, value: parseFloat(cell.dataset.amount) }))
      .filter(({ value }) => value > 0);
    if (!cells.length) return null;
    const stats = statistics(cells.map(({ value }) => value));
    if (stats.max === stats.min) return stats;
    cells.forEach(({ cell, value }) => {
      const outlier = stats.iqr !== 0 && (value < stats.q1 - 1.5 * stats.iqr || value > stats.q3 + 1.5 * stats.iqr);
      const color = outlier ? COLORS.outlier : value < stats.mean ? COLORS.belowMean : COLORS.normal;
      const intensity = stats.stdDev === 0 ? 0 : 1 / (1 + Math.exp(-(value - stats.mean) / stats.stdDev));
      cell.style.backgroundColor = `rgba(${color}, ${Math.min(intensity * MAX_OPACITY, MAX_OPACITY)})`;
      cell.style.color = intensity > DARK_TEXT_INTENSITY ? '#000' : 'inherit';
      if (outlier) cell.style.fontWeight = 'bold';
    });
    return stats;
  }

  root.querySelectorAll('table[data-heatmap]').forEach(paint);

  const selector = root.querySelector('#monthSelector');
  const statsBox = root.querySelector('#mobileStatsDisplay');
  function showMonth() {
    root.querySelectorAll('tbody[data-month]').forEach((tbody) => {
      tbody.hidden = tbody.dataset.month !== selector.value;
    });
    const tbody = root.querySelector(`tbody[data-month="${selector.value}"]`);
    const stats = paint(tbody);
    statsBox.hidden = !stats;
    if (!stats) return;
    const total = parseFloat(tbody.querySelector('[data-total]').dataset.total);
    root.querySelector('#statsContent').innerHTML = `
      <div>Média: ${App.brl(stats.mean)}</div><div>Mediana: ${App.brl(stats.median)}</div>
      <div>Mínimo: ${App.brl(stats.min)}</div><div>Máximo: ${App.brl(stats.max)}</div>
      <div>Total: ${App.brl(total)}</div>`;
  }
  selector.addEventListener('change', showMonth);
  showMonth();
})();
