from django.contrib import admin
from apps.screener.models import WhitelistUser, Screenshot, AnalysisResult


@admin.register(WhitelistUser)
class WhitelistUserAdmin(admin.ModelAdmin):
    list_display = ("telegram_id", "name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("telegram_id", "name")
    list_editable = ("is_active",)


class AnalysisResultInline(admin.StackedInline):
    model = AnalysisResult
    readonly_fields = ("answer", "model_used", "created_at")
    can_delete = False
    extra = 0


@admin.register(Screenshot)
class ScreenshotAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "created_at")
    list_filter = ("status",)
    readonly_fields = ("created_at",)
    inlines = [AnalysisResultInline]


@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    list_display = ("id", "screenshot", "model_used", "created_at")
    readonly_fields = ("screenshot", "answer", "model_used", "created_at")
    search_fields = ("answer",)
