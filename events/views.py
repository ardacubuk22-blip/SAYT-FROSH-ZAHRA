from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone

from .models import Event


def event_list(request):
    now = timezone.now()
    events = (
        Event.objects.filter(status=Event.Status.PUBLISHED)
        .filter(Q(end__gte=now) | Q(end__isnull=True, start__gte=now))
        .select_related("venue", "district", "city")
    )
    return render(request, "events/list.html", {"events": events})
