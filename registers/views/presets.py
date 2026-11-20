from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from registers.forms import QuickFillPresetForm
from registers.models import QuickFillPreset
from utils.http import delete_owned


@login_required
def quick_fill_preset_list(request):
    return render(request, 'register/quick_fill_preset_list.html', {
        'presets': QuickFillPreset.objects.filter(user=request.user).select_related('category', 'payment_method'),
    })


def _edit(request, preset, success_message):
    form = QuickFillPresetForm(request.POST or None, instance=preset)
    if request.method == 'POST':
        if form.is_valid():
            preset = form.save(commit=False)
            preset.user = request.user
            preset.save()
            messages.success(request, success_message % {'name': preset.name})
            return redirect('quick_fill_preset_list')
    return render(request, 'register/quick_fill_preset_form.html', {'form': form, 'is_editing': preset is not None})


@login_required
def quick_fill_preset_create(request):
    return _edit(request, None, _("Preset '%(name)s' created successfully."))


@login_required
def quick_fill_preset_edit(request, pk):
    preset = get_object_or_404(QuickFillPreset, pk=pk, user=request.user)
    return _edit(request, preset, _("Preset '%(name)s' updated successfully."))


@login_required
@require_http_methods(["POST"])
def quick_fill_preset_delete(request, pk):
    return delete_owned(request, QuickFillPreset.objects, pk,
                        _('Preset deleted successfully.'), _('Preset not found'))
