from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Q, Count
from .models import DoctorAssignment, ChatMessage
from .forms import AssignDoctorForm, ChatMessageForm
from .decorators import data_entry_or_admin_required, doctor_required

User = get_user_model()


@data_entry_or_admin_required
def assign_doctor(request, mother_id):
    """GET/POST /doctor-chat/assign/<mother_id>/ -- data entry assigns/reassigns a doctor."""
    mother = get_object_or_404(User, id=mother_id, role="mother")
    current = DoctorAssignment.objects.filter(mother=mother, is_active=True).first()

    if request.method == "POST":
        form = AssignDoctorForm(request.POST)
        if form.is_valid():
            if current:
                current.is_active = False
                current.save(update_fields=["is_active"])
            DoctorAssignment.objects.create(
                mother=mother, doctor=form.cleaned_data["doctor"], assigned_by=request.user,
            )
            messages.success(request, f"Dr. {form.cleaned_data['doctor'].username} assigned to {mother.username}.")
            return redirect("hospital-mother-detail", mother_id=mother.id)
    else:
        form = AssignDoctorForm(initial={"doctor": current.doctor_id if current else None})

    return render(request, "doctor_chat/assign_doctor.html", {"form": form, "mother": mother, "current": current})


@doctor_required
def doctor_dashboard(request):
    """GET /doctor-chat/ -- doctor's list of assigned mothers, with unread counts."""
    assignments = DoctorAssignment.objects.filter(
        doctor=request.user, is_active=True
    ).annotate(
        unread_count=Count("messages", filter=Q(messages__is_read=False) & ~Q(messages__sender=request.user))
    ).select_related("mother")

    return render(request, "doctor_chat/doctor_dashboard.html", {"assignments": assignments})


@login_required
def mother_chat_entry(request):
    """GET /doctor-chat/my-doctor/ -- mother's entry point; redirects to her active thread."""
    assignment = DoctorAssignment.objects.filter(mother=request.user, is_active=True).first()
    if not assignment:
        return render(request, "doctor_chat/no_doctor.html")
    return redirect("chat-thread", assignment_id=assignment.id)

@login_required
def chat_thread(request, assignment_id):
    """GET/POST /doctor-chat/thread/<id>/ -- shared chat view, usable by either party."""
    assignment = get_object_or_404(DoctorAssignment, id=assignment_id)
    if request.user.id not in (assignment.mother_id, assignment.doctor_id):
        return HttpResponseForbidden("You don't have access to this conversation.")

    if request.method == "POST":
        form = ChatMessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.assignment = assignment
            message.sender = request.user
            message.save()
            return redirect("chat-thread", assignment_id=assignment.id)
    else:
        form = ChatMessageForm()

    ChatMessage.objects.filter(assignment=assignment, is_read=False).exclude(sender=request.user).update(is_read=True)

    is_doctor_view = request.user.id == assignment.doctor_id
    other_party = assignment.doctor if request.user.id == assignment.mother_id else assignment.mother
    chat_messages = assignment.messages.select_related("sender")

    return render(request, "doctor_chat/chat_thread.html", {
        "assignment": assignment, "form": form, "other_party": other_party,
        "chat_messages": chat_messages, "is_doctor_view": is_doctor_view,
        # picks the sidebar that matches whoever's actually looking at the thread
        "base_template": "hospital_portal/staff_base.html" if is_doctor_view else "pregnancy_dashboard/dashboard_layout.html",
    })


@login_required
def chat_poll(request, assignment_id):
    """GET /doctor-chat/thread/<id>/poll/?after=<id> -- JSON of new messages since <id>."""
    assignment = get_object_or_404(DoctorAssignment, id=assignment_id)
    if request.user.id not in (assignment.mother_id, assignment.doctor_id):
        return HttpResponseForbidden()

    after_id = request.GET.get("after", 0)
    new_messages = assignment.messages.filter(id__gt=after_id).exclude(sender=request.user)
    new_messages.filter(is_read=False).update(is_read=True)

    data = [
        {"id": m.id, "sender": m.sender.username, "text": m.text, "time": m.created_at.strftime("%I:%M %p")}
        for m in new_messages
    ]
    return JsonResponse({"messages": data})