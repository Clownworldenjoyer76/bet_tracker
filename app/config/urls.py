from django.contrib import admin
from django.urls import include, path, re_path

from siteapp.views import frontend_file, healthz, readyz

urlpatterns = [
    path("healthz", healthz, name="healthz"),
    path("readyz", readyz, name="readyz"),
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("", frontend_file, {"path": ""}, name="frontend-home"),
    re_path(r"^(?P<path>.*)$", frontend_file, name="frontend-file"),
]
