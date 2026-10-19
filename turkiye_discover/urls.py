from django.contrib import admin
from django.urls import include, path

from core import views as core_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz/", core_views.healthz, name="healthz"),
    path("consent/", core_views.consent, name="consent"),
    path("tours/", include("tours.urls")),
    path("universities/", include("universities.urls")),
    path("", include("events.urls")),
]
