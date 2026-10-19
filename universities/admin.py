from django.contrib import admin

from .models import AdmissionCycle, Program, University

MANUAL_NOTE = "این بخش فقط دستی پر می‌شود؛ هیچ ابزار خودکار یا AI آن را تغییر نمی‌دهد."


class ProgramInline(admin.TabularInline):
    model = Program
    extra = 0
    fields = ("name", "name_fa", "level", "language", "tuition_foreign", "currency", "academic_year", "is_medical")
    show_change_link = True


class AdmissionCycleInline(admin.StackedInline):
    model = AdmissionCycle
    extra = 0


@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = ("name", "name_fa", "ownership", "city", "science_ministry_status", "science_ministry_checked",
                    "is_published")
    list_filter = ("ownership", "city", "science_ministry_status", "is_published")
    search_fields = ("name", "name_fa")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProgramInline]
    fieldsets = (
        (None, {"fields": ("name", "name_fa", "slug", "ownership", "city", "district", "has_dormitory",
                           "official_url", "international_url", "description_fa", "is_published")}),
        ("تأیید وزارت علوم ایران (دستی)", {
            "description": MANUAL_NOTE,
            "fields": ("science_ministry_status", "science_ministry_checked"),
        }),
        ("منبع", {"fields": ("source", "last_checked")}),
    )
    readonly_fields = ("source", "last_checked")


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("name", "name_fa", "university", "level", "language", "tuition_foreign", "is_medical",
                    "health_ministry_status")
    list_filter = ("level", "language", "is_medical", "health_ministry_status", "university")
    search_fields = ("name", "name_fa", "university__name", "university__name_fa")
    autocomplete_fields = ("university",)
    inlines = [AdmissionCycleInline]
    fieldsets = (
        (None, {"fields": ("university", "name", "name_fa", "level", "language", "tuition_foreign", "currency",
                           "academic_year", "is_medical")}),
        ("تأیید وزارت بهداشت — فقط رشته‌های پزشکی (دستی)", {
            "description": MANUAL_NOTE,
            "fields": ("health_ministry_status", "health_ministry_checked"),
        }),
        ("منبع", {"fields": ("source_url", "last_checked")}),
    )
    readonly_fields = ("last_checked",)
