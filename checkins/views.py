from __future__ import annotations

# imports
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from zoneinfo import ZoneInfo
from datetime import timedelta
from .models import CheckIn, Habit, HRVReading, HabitAnchor
from .forms import CheckInForm, HabitForm, HRVReadingForm, HabitAnchorForm
from .services.prompts import assign_prompt_variant
from .services.scoring import predict_habit_completion_probability


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


# create new daily check-in (or update existing one for today)
@login_required
def checkin_create(request):
    if request.method == "POST":
        # bind POST data to form
        form = CheckInForm(request.POST)
        if form.is_valid():
            # use fixed timezone (EST)
            tz = ZoneInfo("America/New_York")
            today = timezone.now().astimezone(tz).date()

            # create or update check-in for today
            obj, created = CheckIn.objects.get_or_create(
                user=request.user,
                local_date=today,
                defaults={
                    **form.cleaned_data,
                    "checked_in_at": timezone.now(),
                    "source": "web",
                },
            )

            # if check-in already exists, update its fields
            if not created:
                for f, v in form.cleaned_data.items():
                    setattr(obj, f, v)
                obj.save()

            # redirect to list view after saving
            return redirect("checkin_list")
    else:
        # display empty form for GET requests
        form = CheckInForm()

    # render check-in form template
    return render(request, "checkins/form.html", {"form": form})


# list all recent check-ins (max 60) for logged-in user
@login_required
def checkin_list(request):
    qs = CheckIn.objects.filter(user=request.user).order_by("-local_date")[:60]
    return render(request, "checkins/list.html", {"checkins": qs})


# helper: compute current streak (consecutive check-ins up to today)
def _compute_streak(user):
    dates = set(CheckIn.objects.filter(user=user).values_list("local_date", flat=True))
    if not dates:
        return 0
    tz = ZoneInfo("America/New_York")
    d = timezone.now().astimezone(tz).date()
    streak = 0
    while d in dates:
        streak += 1
        d = d - timedelta(days=1)
    return streak


# helper: get last n days of mood/status data
def _last_n_days(user, n=7):
    tz = ZoneInfo("America/New_York")
    today = timezone.now().astimezone(tz).date()
    qs = CheckIn.objects.filter(
        user=user,
        local_date__gte=today - timedelta(days=n - 1),
        local_date__lte=today,
    ).order_by("local_date")
    by_date = {c.local_date: c for c in qs}
    out = []
    for i in range(n):
        d = today - timedelta(days=(n - 1 - i))
        c = by_date.get(d)
        out.append(
            {
                "date": d,
                "mood": getattr(c, "mood", None) if c else None,
                "status": c.status if c else "miss",
            }
        )
    return out


# helper: generate Tiny Habit suggestion based on recent data (Ref-A)
def _tiny_prompt_from_last(out):
    # heuristic: suggest new habit if last 3 entries show risk or low mood
    risky = any(
        (p["status"] in ("warn", "block")) or (p["mood"] and p["mood"] <= 2)
        for p in out[-3:]
    )
    if risky:
        # based on B=MAP: attach to routine, immediate, simple
        return "After brushing your teeth: take one deep breath + one sip of water. (tiny, instant, anchored)"
    return "After breakfast: 10-second shoulder stretch. (small & consistent)"


# helper: show HRV tip (Ref-B)
def _hrv_tip_from_last(out, user):
    # HRV (RMSSD) interpretation note — one low value ≠ low recovery
    return (
        "When measuring RMSSD, keep the time of day consistent. "
        "A single low value means little without a 7-day trend."
    )


# helper: simple moving average for smoothing mood data (Ref-C)
def _smooth(values, k=3):
    res = []
    for i in range(len(values)):
        win = values[max(0, i - k + 1) : i + 1]
        win = [v for v in win if v is not None]
        res.append(sum(win) / len(win) if win else None)
    return res


# render main dashboard view
@login_required
def dashboard(request):
    # compute user streak
    streak = _compute_streak(request.user)

    # get 7-day check-in history
    trend = _last_n_days(request.user, n=7)

    # apply simple mood smoothing (3-day moving average)
    smoothed = _smooth([p["mood"] for p in trend], k=3)
    for p, s in zip(trend, smoothed):
        p["mood_smooth"] = s

    # context for template rendering
    ctx = {
        "streak": {"days": streak},
        "trend": trend,
        "tiny_prompt": _tiny_prompt_from_last(trend),  # Ref-A: Tiny Habits
        "hrv_tip": _hrv_tip_from_last(trend, request.user),  # Ref-B: HRV insights
    }

    # render dashboard template
    return render(request, "checkins/dashboard.html", ctx)


# create new habit (Tiny Habits–style) for the logged-in user
@login_required
def habit_create(request):
    # handle form submission
    if request.method == "POST":
        form = HabitForm(request.POST)
        if form.is_valid():
            # create Habit instance but delay saving to add user and variant
            habit: Habit = form.save(commit=False)
            habit.user = request.user
            # assign randomized A/B prompt variant at creation
            habit.prompt_variant = assign_prompt_variant()
            habit.save()
            # redirect to detail page after successful creation
            return redirect("checkins:habit_detail", pk=habit.pk)
    else:
        # display blank form for GET requests
        form = HabitForm()

    # render habit creation template with bound or unbound form
    return render(request, "checkins/habit_form.html", {"form": form})


# allow the authenticated user to manually record a new HRV (Heart Rate Variability) reading
@login_required
def hrv_create_view(request):

    # handle form submission
    if request.method == "POST":
        form = HRVReadingForm(request.POST)
        if form.is_valid():
            # assign reading to current user before saving
            hrv = form.save(commit=False)
            hrv.user = request.user
            hrv.save()
            # redirect to HRV list after successful save
            return redirect("checkins:hrv-list")
    else:
        # display empty form for GET request
        form = HRVReadingForm()

    # render HRV entry template
    return render(
        request,
        "checkins/hrv_form.html",
        {"form": form},
    )


# display the most recent HRV readings for the current user
@login_required
def hrv_list_view(request):

    readings = HRVReading.objects.filter(user=request.user)[:30]
    return render(request, "checkins/hrv_list.html", {"readings": readings})


# create a new Tiny Habits–style anchor for the current user
@login_required
def habit_anchor_create_view(request):

    # handle form submission
    if request.method == "POST":
        form = HabitAnchorForm(request.POST)
        if form.is_valid():
            # assign anchor to current user before saving
            anchor = form.save(commit=False)
            anchor.user = request.user
            anchor.save()
            # redirect to list view after successful creation
            return redirect("checkins:habit-anchor-list")
    else:
        # display blank form for GET requests
        form = HabitAnchorForm()

    # render Tiny Habits form template
    return render(
        request,
        "checkins/habit_anchor_form.html",
        {"form": form},
    )


# display a list of all active habit anchors for the current user
@login_required
def habit_anchor_list_view(request):

    anchors = HabitAnchor.objects.filter(user=request.user, is_active=True)
    return render(request, "checkins/habit_anchor_list.html", {"anchors": anchors})


# render the main user dashboard, extended for Week 7 with predictive analytics
@login_required
def dashboard_view(request):

    # compute personalized habit completion probability
    completion_prob = predict_habit_completion_probability(request.user)

    # build dashboard context dictionary
    context = {
        # display probability as a percentage rounded to one decimal place
        "completion_prob": round(completion_prob * 100, 1),
        # TODO: merge with other Week 6 context keys (e.g., streaks, trends)
    }

    # render dashboard template with predictive metric included
    return render(request, "checkins/dashboard.html", context)
