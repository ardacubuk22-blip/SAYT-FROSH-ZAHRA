from django.contrib import admin

from .models import Event, EventChange, ReviewQueueEvent


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
                       "content_hash", "review_reason", "duplicate_of")
    inlines = [EventChangeInline]
    actions = ["publish", "reject"]

    @admin.action(description="انتشار رویدادهای انتخاب‌شده")
    def publish(self, request, queryset):
        queryset.update(status=Event.Status.PUBLISHED)

    @admin.action(description="رد کردن رویدادهای انتخاب‌شده")
    def reject(self, request, queryset):
        queryset.update(status=Event.Status.REJECTED)


@admin.register(ReviewQueueEvent)
class ReviewQueueAdmin(EventAdmin):
    """The manual review queue: low confidence or validation problems, with the reason shown."""

    list_display = ("title", "category", "start", "venue", "confidence", "review_reason", "source")
    list_filter = ("category", "source")
    actions = ["publish", "reject"]

    def get_queryset(self, request):
        return super().get_queryset(request).filter(status=Event.Status.NEEDS_REVIEW).order_by("confidence", "start")

    def has_add_permission(self, request):
        return False
