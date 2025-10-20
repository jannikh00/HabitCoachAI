# import admin and model
from django.contrib import admin
from .models import CheckIn


# register CheckIn model in admin with display customizations
@admin.register(CheckIn)
class CheckInAdmin(admin.ModelAdmin):
    # columns shown in admin list view
    list_display = ("user", "local_date", "status", "mood", "checked_in_at", "source")
    # sidebar filters
    list_filter = ("status", "local_date", "source")
    # enable search across related username, notes, and tags
    search_fields = ("user__username", "note", "tags")
    # order newest first
    ordering = ("-checked_in_at",)
