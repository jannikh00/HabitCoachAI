from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "", include("checkins.urls", namespace="checkins")
    ),  # dashboard, checkin list, etc.
    path("users/", include("users.urls", namespace="users")),  # custom login/logout
    path("accounts/", include("django.contrib.auth.urls")),  # built-in auth
]
