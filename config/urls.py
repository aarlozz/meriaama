from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    # Web pages (Django templates, session auth) -- this is what mothers actually browse
    path("", include("apps.accounts.urls")),
    # We'll add each line below back in as we build that app together:
    path("mood/", include("apps.mood.urls")),
    
    path("psychometric/", include("apps.psychometric.urls")),
    path("tracker/", include("apps.tracker.urls")),
    path("health_profile/", include('apps.health_profile.urls')),
    path("forum/", include("apps.forum.urls")),
    path("wellness/", include("apps.wellness_rag.urls")),
    path("reports/", include("apps.pdf_insight.urls")),
    path("daily-plan/", include("apps.daily_wellness.urls")),
    path("insights/", include("apps.insights.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)