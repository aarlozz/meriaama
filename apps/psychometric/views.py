from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404
from .models import PsychometricTest
from .forms import build_test_form, extract_answers, QUESTIONS


@login_required
def select_test_page(request):
    """GET /psychometric/ -- choose which scale to take, plus recent results."""
    history = PsychometricTest.objects.filter(user=request.user).order_by("-taken_at")[:10]
    return render(request, "psychometric/select.html", {
        "test_types": PsychometricTest.TestType.choices,
        "history": history,
        "header_title": "Psychometric Test",
"header_subtitle": "Assess your emotional and mental wellbeing",
    })


@login_required
def take_test_page(request, test_type):
    """GET/POST /psychometric/take/<test_type>/ -- answer all questions for one scale."""
    if test_type not in QUESTIONS:
        raise Http404("Unknown test type")

    if request.method == "POST":
        form = build_test_form(test_type, data=request.POST)
        if form.is_valid():
            answers = extract_answers(form, test_type)
            test = PsychometricTest.objects.create(user=request.user, test_type=test_type, answers=answers)
            return redirect("psychometric-result", test_id=test.id)
    else:
        form = build_test_form(test_type)

    return render(request, "psychometric/take_test.html", {
        "form": form,
        "test_type": test_type,
        "test_type_label": dict(PsychometricTest.TestType.choices)[test_type],
        "header_title": "Psychometric Test",
"header_subtitle": "Assess your emotional and mental wellbeing",        
    })


@login_required
def test_result_page(request, test_id):
    """GET /psychometric/result/<id>/ -- score + risk level after submitting."""
    test = get_object_or_404(PsychometricTest, id=test_id, user=request.user)
    return render(request, "psychometric/result.html", {"test": test,"header_title": "Psychometric Test",
"header_subtitle": "Assess your emotional and mental wellbeing",})


@login_required
def test_history_page(request):
    """
    GET /psychometric/history/ -- full history + a trend chart per test type.
    Each scale (PSS-10/EPDS/GAD-7) has its own scoring range, so they're
    charted separately rather than combined onto one axis.
    """
    all_tests = PsychometricTest.objects.filter(user=request.user).order_by("taken_at")

    charts = []
    for value, label in PsychometricTest.TestType.choices:
        tests_of_type = [t for t in all_tests if t.test_type == value]
        if not tests_of_type:
            continue

        cutoffs = PsychometricTest.CUTOFFS[value]
        charts.append({
            "test_type": value,
            "label": label,
            "labels": [t.taken_at.strftime("%b %d, %Y") for t in tests_of_type],
            "scores": [t.total_score for t in tests_of_type],
            "moderate_cutoff": cutoffs["moderate"],
            "high_cutoff": cutoffs["high"],
            "latest_risk": tests_of_type[-1].risk_level,
            "attempt_count": len(tests_of_type),
        })

    return render(request, "psychometric/history.html", {
        "charts": charts,
        "all_tests": list(reversed(all_tests)),  # newest first for the table
        "has_data": all_tests.exists(),
    })