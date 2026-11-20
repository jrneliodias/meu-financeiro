// Draws every <canvas data-bar-chart="<json_script id>"> as a horizontal bar chart (Resumo tab).
document.querySelectorAll('canvas[data-bar-chart]').forEach((canvas) => {
  const data = JSON.parse(document.getElementById(canvas.dataset.barChart).textContent);
  const palette = canvas.dataset.palette.split(' ');
  const isMobile = window.matchMedia('(max-width: 767px)').matches;
  new Chart(canvas, {
    type: 'bar',
    data: {
      labels: data.labels,
      datasets: data.datasets.map((dataset, index) => {
        const rgb = palette[index % palette.length];
        return {
          label: dataset.label,
          data: dataset.data,
          backgroundColor: `rgba(${rgb}, 0.2)`,
          borderColor: `rgba(${rgb}, 1)`,
          borderWidth: 1,
        };
      }),
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: 'y',
      layout: { padding: { top: 10, right: isMobile ? 70 : 100, bottom: 2, left: 0 } },
      plugins: {
        legend: {
          display: 'legend' in canvas.dataset && !isMobile,
          position: 'top',
          labels: { color: 'white', font: { size: 12 }, boxWidth: 14 },
        },
        datalabels: {
          anchor: 'end',
          align: 'right',
          formatter: (value) => {
            if (value <= 0) return '';
            return isMobile ? `${App.brl(value / 1000, 1)}k` : App.brl(value);
          },
          color: 'white',
          font: { weight: 'bold', size: isMobile ? 9 : 12 },
        },
      },
      scales: {
        y: { ticks: { font: { size: isMobile ? 10 : 12 }, color: 'white' } },
        x: { display: false, beginAtZero: true },
      },
    },
    plugins: [ChartDataLabels],
  });
});
