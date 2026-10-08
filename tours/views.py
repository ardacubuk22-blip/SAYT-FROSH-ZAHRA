from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from core.models import Interaction
from core.web import booking_message, log_interaction, whatsapp_link

from .models import Tour


def _published_tour(pk):
    tour = get_object_or_404(Tour.objects.select_related("agency", "city"), pk=pk)
    if not tour.is_published:
        raise Http404
    return tour


def tour_list(request):
    tours = Tour.objects.filter(is_published=True).select_related("agency")
    return render(request, "tours/list.html", {"tours": tours})


def tour_detail(request, pk):
    tour = _published_tour(pk)
    log_interaction(request, Interaction.Kind.VIEW, "tour", tour.pk)
    return render(request, "tours/detail.html", {
        "tour": tour,
        "stops": tour.stops.all(),
        "dates": tour.upcoming_dates(),
    })


def tour_whatsapp(request, pk):
    tour = _published_tour(pk)
    log_interaction(request, Interaction.Kind.WHATSAPP, "tour", tour.pk)
    return redirect(whatsapp_link(booking_message("تور", tour.code, tour.title)))
