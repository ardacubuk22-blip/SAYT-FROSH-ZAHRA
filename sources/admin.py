from django.contrib import admin
from django.utils.html import format_html

from .models import ApiUsage, PageSnapshot, Source, SourceRun


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("name", "health", "access_method", "terms_status", "is_active", "last_run",
                    "last_success", "items_found_last_run")
    list_filter = ("is_active", "type", "access_method", "terms_status")
    readonly_fields = ("last_run", "last_success", "items_found_last_run", "last_error")

    @admin.display(description="سلامت")
    def health(self, obj):
        if obj.last_run is None:
            return "—"
        if obj.needs_attention:
            reason = "خطا" if obj.last_error else "صفر نتیجه"
            return format_html('<b style="color:#c0392b">⚠ {}</b>', reason)
        return format_html('<span style="color:#27ae60">{}</span>', "✔ سالم")


@admin.register(SourceRun)
class SourceRunAdmin(admin.ModelAdmin):
    list_display = ("source", "started_at", "links_found", "created", "updated", "unchanged",
                    "sent_to_review", "failed", "has_error")
    list_filter = ("source",)

    @admin.display(boolean=True, description="خطا")
    def has_error(self, obj):
        return bool(obj.error)


@admin.register(PageSnapshot)
class PageSnapshotAdmin(admin.ModelAdmin):
    list_display = ("url", "source", "last_checked", "last_changed")
    list_filter = ("source",)
    search_fields = ("url",)


@admin.register(ApiUsage)
class ApiUsageAdmin(admin.ModelAdmin):
    list_display = ("created_at", "purpose", "model", "is_batch", "input_tokens", "output_tokens", "cost_usd")
    list_filter = ("purpose", "model", "is_batch")
    date_hierarchy = "created_at"

    def changelist_view(self, request, extra_context=None):
        extra_context = {**(extra_context or {}), "title": f"مصرف API — جمع این ماه: {ApiUsage.month_total():.4f} دلار"}
        return super().changelist_view(request, extra_context)
