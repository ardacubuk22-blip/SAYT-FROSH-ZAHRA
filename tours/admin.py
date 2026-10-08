from django.contrib import admin

from .models import Agency, Tour, TourDate, TourStop


class TourStopInline(admin.StackedInline):
    model = TourStop
    extra = 1


class TourDateInline(admin.TabularInline):
    model = TourDate
    extra = 1


@admin.register(Agency)
class AgencyAdmin(admin.ModelAdmin):
    list_display = ("name", "license_number")
    search_fields = ("name", "license_number")


@admin.register(Tour)
class TourAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "agency", "price", "capacity", "is_published")
    list_filter = ("kind", "is_published", "city")
    search_fields = ("title",)
    inlines = [TourStopInline, TourDateInline]
