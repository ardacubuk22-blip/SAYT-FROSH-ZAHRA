from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from core.models import Interaction
from core.web import log_interaction, whatsapp_link

from .models import Program, University
from .search import search_programs, search_universities

PAGE_SIZE = 24


def university_list(request):
    q = request.GET.get("q", "").strip()
    level = request.GET.get("level") if request.GET.get("level") in Program.Level.values else ""
    language = request.GET.get("language") if request.GET.get("language") in Program.Language.values else ""
    searching = bool(q or level or language)

    universities = University.objects.filter(is_published=True).select_related("city", "district")
    context = {
        "q": q, "level": level, "language": language, "searching": searching,
        "levels": Program.Level.choices, "languages": Program.Language.choices,
    }
    if not searching:
        context["universities"] = universities
        return render(request, "universities/list.html", context)

    programs = Program.objects.filter(university__is_published=True).select_related(
        "university", "university__city"
    )
    programs = search_programs(programs, q)
    if level:
        programs = programs.filter(level=level)
    if language:
        programs = programs.filter(language=language)
    page = Paginator(programs, PAGE_SIZE).get_page(request.GET.get("page"))
    query = request.GET.copy()
    query.pop("page", None)
    context.update({
        "page": page,
        "query": query.urlencode(),
        # Universities that match the words but may have no program entered yet.
        "universities": search_universities(universities, q) if q and not (level or language) else [],
    })
    return render(request, "universities/list.html", context)


def _published_university(slug):
    university = get_object_or_404(University.objects.select_related("city", "district"), slug=slug)
    if not university.is_published:
        raise Http404
    return university


def university_detail(request, slug):
    university = _published_university(slug)
    log_interaction(request, Interaction.Kind.VIEW, "university", university.pk)
    programs = university.programs.prefetch_related("cycles")
    return render(request, "universities/detail.html", {"university": university, "programs": programs})


def university_whatsapp(request, slug):
    university = _published_university(slug)
    log_interaction(request, Interaction.Kind.WHATSAPP, "university", university.pk)
    message = (
        "سلام، برای مشاوره درباره‌ی تحصیل در دانشگاه زیر پیام می‌دهم:\n"
        f"کد: {university.code}\nدانشگاه: {university.name_fa or university.name}"
    )
    return redirect(whatsapp_link(message))
