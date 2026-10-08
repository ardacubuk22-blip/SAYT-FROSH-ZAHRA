from django.contrib import admin

from .models import Event, EventChange


class EventChangeInline(admin.TabularInline):
    model = EventChange
    extra = 0
    can_delete = False
    readonly_fields = ("field", "old_value", "new_value", "changed_at")


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "title_fa", "category", "start", "venue", "status", "confidence", "source")
    list_filter = ("status", "category", "city", "is_free", "source")
    search_fields = ("title", "title_fa", "venue__name")
    date_hierarchy = "start"
    autocomplete_fields = ("venue", "district")
    readonly_fields = ("source", "source_url", "first_seen", "last_checked", "last_updated", "confidence",
                       "content_hash", "review_reason")
    inlines = [EventChangeInline]
    actions = ["publish", "reject"]

    @admin.action(description="انتشار رویدادهای انتخاب‌شده")
    def publish(self, request, queryset):
        queryset.update(status=Event.Status.PUBLISHED)

    @admin.action(description="رد کردن رویدادهای انتخاب‌شده")
    def reject(self, request, queryset):
        queryset.update(status=Event.Status.REJECTED)
