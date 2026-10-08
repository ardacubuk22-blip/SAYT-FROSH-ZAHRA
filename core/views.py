import uuid

from django.http import HttpResponseNotAllowed
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme

from .web import CONSENT_COOKIE, COOKIE_AGE, VISITOR_COOKIE


def consent(request):
    """The visitor answers the notice: yes = anonymous logging with a random id, no = nothing is logged."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    target = request.POST.get("next", "/")
    if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        target = "/"
    response = redirect(target)
    if request.POST.get("choice") == "yes":
        response.set_cookie(CONSENT_COOKIE, "yes", max_age=COOKIE_AGE, samesite="Lax")
        response.set_cookie(VISITOR_COOKIE, str(uuid.uuid4()), max_age=COOKIE_AGE, samesite="Lax", httponly=True)
    else:
        response.set_cookie(CONSENT_COOKIE, "no", max_age=COOKIE_AGE, samesite="Lax")
        response.delete_cookie(VISITOR_COOKIE)
    return response
