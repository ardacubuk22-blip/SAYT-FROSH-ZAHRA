from django.urls import path

from . import views

app_name = "events"

urlpatterns = [
    path("", views.event_list, name="list"),
    path("events/<int:pk>/", views.event_detail, name="detail"),
    path("events/<int:pk>/whatsapp/", views.event_whatsapp, name="whatsapp"),
]
