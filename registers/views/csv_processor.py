import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from registers.csv import processor, read, records
from registers.forms import CSVProcessorForm
from utils.http import json_object

SESSION_KEY = 'processed_csv_data'


def _process(form):
    """(processed DataFrame, warnings), or (None, errors) when the CSV can't be read or mapped."""
    df, errors = read(form.source(), form.cleaned_data['separator'])
    if df is None:
        return None, errors
    columns = form.column_mapping() or processor.detect_columns(df)
    if columns is None:
        return None, [_("Could not auto-detect Nubank format. Available columns: %(columns)s") % {
            'columns': ', '.join(df.columns.tolist())}]
    return processor.process(df, columns)


@login_required
def csv_processor(request):
    """Turn a Nubank CSV into the import format and show it for editing/download (no database writes)."""
    form = CSVProcessorForm(request.POST or None, request.FILES or None)
    if request.method == 'POST':
        if not form.is_valid():
            return render(request, 'register/csv_processor.html', {'form': form})
        processed, warnings = _process(form)
        if processed is None or processed.empty:
            messages.error(request, _("Processing failed. No data to display."))
            for problem in warnings:
                messages.error(request, problem)
            return render(request, 'register/csv_processor.html', {'form': form})
        for warning in warnings:
            messages.warning(request, warning)

        rows = records(processed)
        request.session[SESSION_KEY] = {'csv_string': processor.to_csv_string(processed)}
        return render(request, 'register/csv_processor_preview.html', {
            'processed_data': rows,
            'row_count': len(rows),
        })
    return render(request, 'register/csv_processor.html', {'form': form})


@login_required
def csv_processor_download(request):
    processed = request.session.get(SESSION_KEY)
    if not processed:
        messages.error(request, _("No processed data found. Please upload and process a file first."))
        return redirect('csv_processor')
    response = HttpResponse(processed['csv_string'], content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="processed_nubank.csv"'
    response['Cache-Control'] = 'no-cache'
    return response


@login_required
@require_http_methods(["POST"])
def csv_processor_update_data(request):
    """Replace the processed rows in the session after edits in the preview table."""
    data = json_object(request)
    if data is None:
        return JsonResponse({'success': False, 'error': _('Invalid JSON data')}, status=400)
    rows = data.get('rows')
    if not rows:
        return JsonResponse({'success': False, 'error': _('No row data provided')}, status=400)
    request.session[SESSION_KEY] = {'csv_string': processor.to_csv_string(pd.DataFrame(rows))}
    return JsonResponse({'success': True, 'message': _('Data updated successfully'), 'row_count': len(rows)})
