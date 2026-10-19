"""Program / university search: every word of the query must match something about the program."""

import re

from django.db.models import Q

_ARABIC_TO_PERSIAN = str.maketrans({"ي": "ی", "ك": "ک", "ۀ": "ه", "ة": "ه"})


def tokens(query):
    query = (query or "").translate(_ARABIC_TO_PERSIAN)
    return [t for t in re.split(r"[\s‌]+", query) if t]


def _match(token, university_prefix):
    """Q for one word against a university (reached through `university_prefix`, '' for University itself)."""
    p = university_prefix
    fields = ["name", "name_fa", "city__name", "city__name_fa", "district__name", "district__name_fa"]
    q = Q()
    for field in fields:
        q |= Q(**{f"{p}{field}__icontains": token})
    return q


def search_programs(queryset, query):
    for token in tokens(query):
        q = Q(name__icontains=token) | Q(name_fa__icontains=token) | _match(token, "university__")
        queryset = queryset.filter(q)
    return queryset


def search_universities(queryset, query):
    for token in tokens(query):
        queryset = queryset.filter(_match(token, ""))
    return queryset
