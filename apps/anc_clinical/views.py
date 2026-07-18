from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render

from apps.hospital_portal.models import PrenatalVisit
from .forms import LabPanelForm, UltrasoundReportForm
from .models import LabResult

DIPSTICK_TEXT = {"negative", "trace", "plus1", "plus2", "plus3"}
REACTIVE_TEXT = {"reactive", "non_reactive"}


def _is_hospital_staff(user):
    return user.is_authenticated and (user.is_hospital_staff() or user.is_hospital_admin())


@login_required
@user_passes_test(_is_hospital_staff)
def record_labs(request, visit_id):
    visit = get_object_or_404(PrenatalVisit, pk=visit_id)

    # Pre-fill from any existing LabResult rows for this visit
    existing = {lr.test_code: lr for lr in visit.lab_results.all()}
    initial = {}
    for field_name, (code, *_rest) in LabPanelForm.FIELD_MAP.items():
        if code in existing:
            lr = existing[code]
            initial[field_name] = lr.value_text if lr.value_text else lr.value_numeric

    if request.method == "POST":
        form = LabPanelForm(request.POST)
        if form.is_valid():
            for field_name, (code, name, unit, is_text) in LabPanelForm.FIELD_MAP.items():
                value = form.cleaned_data.get(field_name)
                if value in (None, ""):
                    continue
                lr, _ = LabResult.objects.get_or_create(
                    visit=visit, test_code=code, defaults={"test_name": name, "unit": unit}
                )
                lr.test_name = name
                lr.unit = unit
                if is_text:
                    lr.value_text = value
                    lr.value_numeric = None
                else:
                    lr.value_numeric = value
                    lr.value_text = ""
                lr.save()  # triggers auto-flagging in LabResult.save()
            return redirect("hospital-visit-detail", visit_id=visit.id)
    else:
        form = LabPanelForm(initial=initial)

    return render(request, "anc_clinical/record_labs.html", {"form": form, "visit": visit})


@login_required
@user_passes_test(_is_hospital_staff)
def record_ultrasound(request, visit_id):
    visit = get_object_or_404(PrenatalVisit, pk=visit_id)

    if request.method == "POST":
        form = UltrasoundReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.visit = visit
            report.save()
            return redirect("hospital-visit-detail", visit_id=visit.id)
    else:
        form = UltrasoundReportForm()

    return render(request, "anc_clinical/record_ultrasound.html", {"form": form, "visit": visit})
