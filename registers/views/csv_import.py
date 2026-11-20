import io

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _, ngettext
from django.views.decorators.http import require_http_methods

from registers.csv import importer
from registers.forms import CSVImportForm

SESSION_KEY = 'csv_import_data'
MESSAGES_SHOWN = 5


def _import(request, df, auto_create_categories, auto_create_payment_methods):
    result = importer.import_rows(df, request.user, auto_create_categories, auto_create_payment_methods)
    imported = result['stats']['imported']
    messages.success(request, ngettext(
        "Import completed! %(count)s record imported successfully.",
        "Import completed! %(count)s records imported successfully.",
        imported,
    ) % {'count': imported})
    for error in result['errors'][:MESSAGES_SHOWN]:
        messages.error(request, error)
    return redirect('csv_import')


@login_required
def csv_import(request):
    """Upload or paste a CSV; preview it (kept in the session for csv_import_confirm) or import it now."""
    form = CSVImportForm(request.POST or None, request.FILES or None)
    if request.method == 'POST':
        if not form.is_valid():
            return render(request, 'register/csv_import.html', {'form': form})
        options = form.cleaned_data
        df, problems = importer.read_csv(form.source(), options['separator'])
        if df is None:
            for error in problems:
                messages.error(request, error)
            return render(request, 'register/csv_import.html', {'form': form})
        for warning in problems:
            messages.warning(request, warning)

        if not options['preview_mode']:
            return _import(request, df, options['auto_create_categories'], options['auto_create_payment_methods'])
        request.session[SESSION_KEY] = {
            'csv_data': df.to_csv(index=False),
            'auto_create_categories': options['auto_create_categories'],
            'auto_create_payment_methods': options['auto_create_payment_methods'],
        }
        return render(request, 'register/csv_import_preview.html', {'preview_data': importer.preview(df), 'form': form})
    return render(request, 'register/csv_import.html', {'form': form})


@login_required
@require_http_methods(["POST"])
def csv_import_confirm(request):
    """Import the CSV previewed by csv_import."""
    stored = request.session.pop(SESSION_KEY, None)
    if not stored:
        messages.error(request, _("No import data found. Please upload a file again."))
        return redirect('csv_import')
    df, problems = importer.read_csv(io.StringIO(stored['csv_data']))
    if df is None:
        for error in problems:
            messages.error(request, error)
        return redirect('csv_import')
    return _import(request, df, stored['auto_create_categories'], stored['auto_create_payment_methods'])
