# import helpers for authentication and date handling
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.utils import timezone
from zoneinfo import ZoneInfo
from .models import CheckIn


# view that creates a daily check-in for the logged-in user
@login_required
def check_in_today(request):
    # choose your local timezone
    tz = ZoneInfo("America/New_York")
    # convert current UTC time to local time
    now_local = timezone.now().astimezone(tz)
    # extract local date
    local_date = now_local.date()
    # create or reuse today’s check-in
    obj, created = CheckIn.objects.get_or_create(
        user=request.user,  # current user
        local_date=local_date,  # today
        defaults={  # default fields for creation
            "status": "ok",
            "checked_in_at": timezone.now(),
            "source": "web",
        },
    )
    # redirect user to admin list view after check-in
    return redirect("/admin/checkins/checkin/")
