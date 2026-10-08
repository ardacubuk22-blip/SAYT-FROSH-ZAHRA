from django.contrib import admin
from django.urls import include, path

from core import views as core_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("consent/", core_views.consent, name="consent"),
    path("tours/", include("tours.urls")),
    path("", include("events.urls")),
]
