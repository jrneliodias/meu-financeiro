// Editable preview of the processed CSV (register/csv_processor_preview.html). Edits are saved to the
// session (csv_processor_update_data), which is what "Download CSV" serves.
document.addEventListener('DOMContentLoaded', () => {
  const COLUMNS = ['date', 'amount', 'payment_method', 'description'];
  const rows = JSON.parse(document.getElementById('processed-data').textContent);
  const tableBody = document.getElementById('tableBody');
  const editCountElement = document.getElementById('editCount');
  const copyButton = document.getElementById('copyToClipboardBtn');
  const copyIcon = document.getElementById('copyIcon');
  const copyText = document.getElementById('copyText');
  const downloadButton = document.getElementById('downloadBtn');
  const syncError = document.getElementById('syncError');
  const labels = downloadButton.dataset;
  let editCount = 0;
  let syncTimer = null;

  // Rejects (after showing the error) unless the server stored the rows.
  function sync() {
    clearTimeout(syncTimer);
    return App.post(downloadButton.dataset.updateUrl, { rows })
      .then((response) => response.json())
      .then((data) => {
        if (!data.success) throw new Error(data.error);
        syncError.hidden = true;
      })
      .catch((error) => {
        syncError.textContent = labels.syncError;
        syncError.hidden = false;
        throw error;
      });
  }

  tableBody.addEventListener('blur', (event) => {
    const cell = event.target;
    if (!cell.hasAttribute('contenteditable')) return;
    const row = rows[Number(cell.closest('tr').dataset.rowIndex)];
    const field = cell.dataset.field;
    const value = cell.textContent.trim();
    // Loose on purpose: the amount 50 is displayed as "50.0".
    if (!row || (row[field] ?? '') == value) return;
    row[field] = value;
    editCountElement.textContent = ++editCount;
    cell.classList.add('bg-blue-900');
    setTimeout(() => cell.classList.remove('bg-blue-900'), 500);
    clearTimeout(syncTimer);
    syncTimer = setTimeout(() => sync().catch(() => {}), 1000);
  }, true);

  tableBody.addEventListener('keydown', (event) => {
    if (event.target.hasAttribute('contenteditable') && event.key === 'Enter') {
      event.preventDefault();
      event.target.blur();
    }
  }, true);

  function toCSV() {
    const quote = (value) => {
      const text = String(value ?? '').replace(/"/g, '""');
      return /[",\n]/.test(text) ? `"${text}"` : text;
    };
    return [COLUMNS, ...rows.map((row) => COLUMNS.map((column) => row[column]))]
      .map((values) => values.map(quote).join(','))
      .join('\n') + '\n';
  }

  // execCommand fallback: navigator.clipboard only exists on secure origins (https, localhost).
  function copyWithTextarea(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    let copied = false;
    try {
      copied = document.execCommand('copy');
    } catch (error) {
      copied = false;
    }
    textArea.remove();
    if (copied) showCopied();
    else alert(labels.copyFailed);
  }

  function showCopied() {
    copyButton.classList.remove('bg-purple-600', 'hover:bg-purple-700');
    copyButton.classList.add('bg-green-600');
    copyIcon.className = 'fas fa-check mr-2';
    copyText.textContent = labels.copied;
    setTimeout(() => {
      copyButton.classList.remove('bg-green-600');
      copyButton.classList.add('bg-purple-600', 'hover:bg-purple-700');
      copyIcon.className = 'fas fa-clipboard mr-2';
      copyText.textContent = labels.copy;
    }, 2000);
  }

  copyButton.addEventListener('click', () => {
    const csv = toCSV();
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(csv).then(showCopied, () => copyWithTextarea(csv));
    } else {
      copyWithTextarea(csv);
    }
  });

  // The download only starts once the session holds the current rows.
  downloadButton.addEventListener('click', (event) => {
    event.preventDefault();
    const originalHtml = downloadButton.innerHTML;
    downloadButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>' + labels.preparingDownload;
    downloadButton.classList.add('opacity-75', 'cursor-not-allowed');
    sync()
      .then(() => { window.location.href = downloadButton.href; })
      .catch(() => {})
      .finally(() => {
        downloadButton.innerHTML = originalHtml;
        downloadButton.classList.remove('opacity-75', 'cursor-not-allowed');
      });
  });
});
