import logging
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import MedicalReport
from .forms import MedicalReportUploadForm
from .pdf_summarizer import summarize_report
from apps.wellness_rag.vector_store import ingest_report_chunks

logger = logging.getLogger(__name__)


@login_required
def report_list_page(request):
    reports = MedicalReport.objects.filter(user=request.user)
    return render(request, "pdf_insight/list.html", {"reports": reports,"header_title": "Health Reports",
"header_subtitle": "View and manage your medical reports",})


@login_required
def report_upload_page(request):
    if request.method == "POST":
        form = MedicalReportUploadForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save(commit=False)
            report.user = request.user
            report.save()

            try:
                result = summarize_report(report.file.path)
                report.summary_text = result.get("summary", "")
                report.flagged_values = result.get("flagged_values", [])
                report.extracted_data = result.get("extracted_data", [])
                report.status = MedicalReport.Status.DONE
            except Exception:
                logger.exception("PDF summarization failed for report %s", report.id)
                report.status = MedicalReport.Status.FAILED
            report.save()

            # Feed the extracted data points into this mother's own private
            # knowledge base so "Ask Meri Aama" can later answer questions
            # like "what did my last report say about my hemoglobin?"
            if report.status == MedicalReport.Status.DONE and report.extracted_data:
                try:
                    ingest_report_chunks(request.user.id, report.id, report.extracted_data)
                except Exception:
                    logger.exception("Failed to index report %s into vector store", report.id)

            if report.status == MedicalReport.Status.DONE:
                messages.success(request, "Report uploaded, summarized, and added to your wellness knowledge base.")
            else:
                messages.error(request, "Uploaded, but summarizing failed. You can still view the original PDF.")
            return redirect("report-list")
    else:
        form = MedicalReportUploadForm()

    return render(request, "pdf_insight/upload.html", {"form": form,"header_title": "Health Reports",
"header_subtitle": "View and manage your medical reports",})