from django.urls import path

from . import views

app_name = "tours"

urlpatterns = [
    path("", views.tour_list, name="list"),
    path("<int:pk>/", views.tour_detail, name="detail"),
    path("<int:pk>/whatsapp/", views.tour_whatsapp, name="whatsapp"),
]
