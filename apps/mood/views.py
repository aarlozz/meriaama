from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import MoodEntry
from .forms import MoodEntryForm


@login_required
def mood_checkin_page(request):
    """GET/POST /mood/ -- log today's mood + see recent history."""
    if request.method == "POST":
        form = MoodEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.user = request.user
            entry.save()
            messages.success(request, "Mood logged. Thank you for checking in.")
            return redirect("mood-checkin")
    else:
        form = MoodEntryForm()

    history = MoodEntry.objects.filter(user=request.user)[:14]
    return render(request, "mood/checkin.html", {"form": form, "history": history})