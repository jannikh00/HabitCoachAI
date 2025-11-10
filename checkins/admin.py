# import admin and model
from django.contrib import admin
from .models import CheckIn, HRVReading, HabitAnchor


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


# admin configuration for the HRVReading model, enables staff to view, filter and verify user HRV entries
@admin.register(HRVReading)
class HRVReadingAdmin(admin.ModelAdmin):

    # columns displayed in the admin list view
    list_display = ("user", "measured_at", "rmssd_ms", "sdnn_ms", "resting_hr")

    # filters available in the right sidebar
    list_filter = ("user", "measured_at")


# admin configuration for the HabitAnchor model, allows management of Tiny Habits recipes created by users
@admin.register(HabitAnchor)
class HabitAnchorAdmin(admin.ModelAdmin):

    # columns displayed in the admin list view
    list_display = ("user", "anchor_action", "tiny_behavior", "is_active", "created_at")

    # filter options for quick access to user or activity status
    list_filter = ("user", "is_active")
