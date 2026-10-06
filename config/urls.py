from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.accounts.urls")),
    path("api/", include("apps.masters.urls")),
    path("api/", include("apps.inventory.urls")),
    path("api/", include("apps.sales.urls")),
    path("api/reports/", include("apps.reports.urls")),
    path("api/settings/", include("apps.settings_app.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
