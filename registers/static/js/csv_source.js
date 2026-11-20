// Upload-or-paste CSV input (register/components/csv_source_fields.html): one source at a time,
// and the form's submit button shows a spinner once the form is sent.
document.addEventListener('DOMContentLoaded', () => {
  const root = document.getElementById('csvSource');
  if (!root) return;
  const form = root.closest('form');
  const fileInput = root.querySelector('input[type="file"]');
  const textInput = root.querySelector('textarea');
  const fileLabel = root.querySelector(`label[for="${fileInput.id}"]`);
  const fileLabelText = fileLabel.textContent;

  function showFileName() {
    const file = fileInput.files[0];
    fileLabel.textContent = file ? `${root.dataset.selectedLabel} ${file.name}` : fileLabelText;
  }

  // Switching source clears the other one: the form accepts a file or a text, not both.
  function use(source) {
    root.querySelectorAll('[data-source]').forEach((button) => {
      button.classList.toggle('bg-blue-600', button.dataset.source === source);
      button.classList.toggle('bg-gray-600', button.dataset.source !== source);
    });
    root.querySelectorAll('[data-section]').forEach((section) => {
      section.hidden = section.dataset.section !== source;
    });
    if (source === 'file') {
      textInput.value = '';
    } else {
      fileInput.value = '';
      showFileName();
    }
  }

  root.querySelectorAll('[data-source]').forEach((button) => {
    button.addEventListener('click', () => use(button.dataset.source));
  });
  fileInput.addEventListener('change', showFileName);
  use(root.querySelector('[data-section]:not([hidden])').dataset.section);

  form.addEventListener('submit', (event) => {
    if (!fileInput.files.length && !textInput.value.trim()) {
      event.preventDefault();
      alert(root.dataset.emptyMessage);
      return;
    }
    const button = form.querySelector('button[type="submit"]');
    button.disabled = true;
    button.classList.remove('hover:bg-blue-700');
    button.classList.add('opacity-75', 'cursor-not-allowed');
    button.querySelector('i').className = 'fas fa-spinner fa-spin mr-2';
    button.querySelector('span').textContent = root.dataset.processingLabel;
  });
});
