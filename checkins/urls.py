from django.urls import path
from . import views

app_name = "checkins"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("checkin/today/", views.check_in_today, name="checkin_today"),
    path("checkins/", views.checkin_list, name="checkin_list"),
    path("checkins/new/", views.checkin_create, name="checkin_create"),
    path("hrv/new/", views.hrv_create_view, name="hrv-create"),
    path("hrv/", views.hrv_list_view, name="hrv-list"),
    path(
        "habits/anchors/new/",
        views.habit_anchor_create_view,
        name="habit-anchor-create",
    ),
    path("habits/anchors/", views.habit_anchor_list_view, name="habit-anchor-list"),
]
