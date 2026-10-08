from datetime import datetime, time, timedelta

from django.core.paginator import Paginator
from django.conf import settings
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.models import City, Interaction
from core.web import booking_message, log_interaction, whatsapp_link

from .models import Category, Event

PAGE_SIZE = 24

TIME_CHOICES = [("today", "امروز"), ("week", "این هفته"), ("weekend", "آخر هفته")]


def _day_start(day):
    return timezone.make_aware(datetime.combine(day, time.min))


def time_window(choice, now=None):
    """Return (from, until) for the time filter. Weekend is Saturday + Sunday (Turkey)."""
    now = now or timezone.localtime()
    today = now.date()
    if choice == "today":
        return now, _day_start(today + timedelta(days=1))
    if choice == "week":
        return now, _day_start(today + timedelta(days=7))
    if choice == "weekend":
        if today.weekday() >= 5:  # already Saturday or Sunday
            saturday = today - timedelta(days=today.weekday() - 5)
        else:
            saturday = today + timedelta(days=5 - today.weekday())
        return max(now, _day_start(saturday)), _day_start(saturday + timedelta(days=2))
    return None


def upcoming(queryset, window_from, window_until=None):
    """Events still going on or starting after window_from (and starting before window_until)."""
    queryset = queryset.filter(Q(end__gte=window_from) | Q(end__isnull=True, start__gte=window_from))
    if window_until:
        queryset = queryset.filter(start__lt=window_until)
    return queryset


def event_list(request):
    now = timezone.localtime()
    cities = list(City.objects.filter(is_active=True))
    default_city = next((c for c in cities if c.slug == settings.DEFAULT_CITY_SLUG), cities[0] if cities else None)
    city = next((c for c in cities if c.slug == request.GET.get("city")), default_city)
    time_choice = request.GET.get("time") if request.GET.get("time") in dict(TIME_CHOICES) else ""
    category = request.GET.get("category") if request.GET.get("category") in Category.values else ""
    only_free = request.GET.get("free") == "1"

    events = Event.objects.filter(status=Event.Status.PUBLISHED).select_related("venue", "district", "city")
    if city:
        events = events.filter(city=city)
    window = time_window(time_choice, now) if time_choice else (now, None)
    events = upcoming(events, *window)
    if category:
        events = events.filter(category=category)
    if only_free:
        events = events.filter(is_free=True)

    page = Paginator(events, PAGE_SIZE).get_page(request.GET.get("page"))
    query = request.GET.copy()
    query.pop("page", None)
    return render(request, "events/list.html", {
        "page": page,
        "cities": cities,
        "city": city,
        "time_choices": TIME_CHOICES,
        "time_choice": time_choice,
        "categories": Category.choices,
        "category": category,
        "only_free": only_free,
        "has_filters": bool(time_choice or category or only_free),
        "query": query.urlencode(),
    })


def _published_event(pk):
    event = get_object_or_404(Event.objects.select_related("venue", "district", "city"), pk=pk)
    if event.status != Event.Status.PUBLISHED:
        raise Http404
    return event


def event_detail(request, pk):
    event = _published_event(pk)
    log_interaction(request, Interaction.Kind.VIEW, "event", event.pk)
    return render(request, "events/detail.html", {"event": event})


def event_whatsapp(request, pk):
    event = _published_event(pk)
    log_interaction(request, Interaction.Kind.WHATSAPP, "event", event.pk)
    message = booking_message("رویداد", event.code, event.title_fa or event.title)
    return redirect(whatsapp_link(message))
