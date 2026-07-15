# apps/pdf_insight/views.py
import logging

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from .models import MedicalReport
from .forms import MedicalReportUploadForm
from .pdf_summarizer import extract_text_from_pdf, summarize_report
from .chunking import chunk_text
from .vector_store import ingest_report_chunks
from .report_chat import ask_about_reports

logger = logging.getLogger(__name__)


@login_required
def report_list_page(request):
    reports = MedicalReport.objects.filter(user=request.user)
    return render(request, "pdf_insight/list.html", {
        "reports": reports,
        "header_title": "Health Reports",
        "header_subtitle": "View and manage your medical reports",
    })


@login_required
def report_upload_page(request):
    if request.method == "POST":
        form = MedicalReportUploadForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save(commit=False)
            report.user = request.user
            report.save()

            raw_text = ""
            try:
                raw_text = extract_text_from_pdf(report.file.path)
                result = summarize_report(raw_text)
                report.summary_text = result.get("summary", "")
                report.flagged_values = result.get("flagged_values", [])
                report.status = MedicalReport.Status.DONE
            except Exception:
                logger.exception("PDF summarization failed for report %s", report.id)
                report.status = MedicalReport.Status.FAILED
            report.save()

            if report.status == MedicalReport.Status.DONE:
                try:
                    text_chunks = chunk_text(raw_text)
                    # Fold the flagged values in as short, precise chunks too,
                    # so direct lookups ("what was my hemoglobin?") retrieve
                    # cleanly alongside the longer prose chunks.
                    value_lines = [
                        f"{fv.get('test')}: {fv.get('value')} ({fv.get('note')})"
                        for fv in report.flagged_values
                    ]
                    all_chunks = text_chunks + value_lines
                    if all_chunks:
                        ingest_report_chunks(request.user.id, report.id, all_chunks)
                except Exception:
                    logger.exception("Failed to index report %s into vector store", report.id)

                messages.success(request, "Report uploaded, summarized, and ready for questions.")
            else:
                messages.error(request, "Uploaded, but summarizing failed. You can still view the original PDF.")

            return redirect("report-detail", pk=report.pk)
    else:
        form = MedicalReportUploadForm()

    return render(request, "pdf_insight/upload.html", {
        "form": form,
        "header_title": "Health Reports",
        "header_subtitle": "View and manage your medical reports",
    })


@login_required
def report_detail_page(request, pk):
    report = get_object_or_404(MedicalReport, pk=pk, user=request.user)
    return render(request, "pdf_insight/detail.html", {
        "report": report,
        "header_title": "Health Reports",
        "header_subtitle": "View and manage your medical reports",
    })


@login_required
@require_POST
def ask_about_report(request):
    question = request.POST.get("question", "").strip()
    if not question:
        return JsonResponse({"error": "Please enter a question."}, status=400)

    answer = ask_about_reports(request.user, question)
    return JsonResponse(answer)