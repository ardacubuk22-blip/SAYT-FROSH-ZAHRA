from django.contrib import admin

from .models import City, District, Venue

admin.site.site_header = "پنل مدیریت Türkiye Discover"
admin.site.site_title = "Türkiye Discover"
admin.site.index_title = "مدیریت"


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name_fa", "name", "slug", "is_active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ("name", "name_fa", "city")
    list_filter = ("city",)
    search_fields = ("name", "name_fa")


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ("name", "district", "city")
    list_filter = ("city",)
    search_fields = ("name",)
