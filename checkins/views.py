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
            return redirect("checkins:checkin_list")
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


# map the most recent HRV reading into a coarse readiness category
def _classify_readiness(latest_hrv: HRVReading | None) -> dict[str, str]:

    # if we don't have any HRV reading yet, we fall back to a neutral state
    if latest_hrv is None:
        return {
            "label": "Unknown",
            "description": (
                "No HRV data yet. Consider adding a morning measurement to "
                "better tune your training and habit load."
            ),
        }

    # extract rMSSD (in milliseconds); if missing, treat as 0.0 to avoid crashes
    rmssd = latest_hrv.rmssd_ms or 0.0
    # extract resting heart rate; if missing, assume 70 bpm as a neutral baseline
    resting_hr = latest_hrv.resting_hr or 70

    # --- Simple heuristics inspired by Ref-B --------------------------------
    # higher rMSSD and lower resting HR are generally associated with better recovery
    # I use rough thresholds to keep this understandable by users
    # NOTE: these are not clinical thresholds, just educational examples
    # -------------------------------------------------------------------------

    # Case 1: Strong recovery signal (green) – good day to push habits/training
    if rmssd >= 60 and resting_hr <= 60:
        return {
            "label": "High readiness",
            "description": (
                "Your HRV suggests good recovery and low resting heart rate. "
                "This is a great day to aim for a slightly more challenging habit."
            ),
        }

    # Case 2: Moderate recovery signal (yellow) – keep habits tiny and sustainable
    if 40 <= rmssd < 60 and 60 < resting_hr <= 70:
        return {
            "label": "Moderate readiness",
            "description": (
                "Your HRV is in a moderate range. Stay consistent with tiny habits, "
                "but avoid large jumps in difficulty."
            ),
        }

    # Case 3: Lower recovery signal (red) – lean heavily on Tiny Habits principles
    # (Ref-A: emphasize shrinking the behavior and celebrating completion)
    return {
        "label": "Low readiness",
        "description": (
            "Your current HRV pattern suggests higher load or incomplete recovery. "
            "Keep habits very small today and focus on easy wins and celebration."
        ),
    }


# see description below
@login_required
def dashboard(request):
    """
    unified dashboard view that combines:

    - streak and 7-day trend (Week 5 analytics, Tiny Habits framing – Ref-A)
    - risk-day summary (status warn/block or low mood)
    - HRV-informed readiness classification (Ref-B)
    - logistic-style adherence forecast (Ref-C)
    """

    # 1) compute the user's current streak of consecutive check-in days
    streak_days = _compute_streak(request.user)

    # 2) retrieve the last 7 days of check-ins for the trend visualization
    trend = _last_n_days(request.user, n=7)

    # 3) apply simple 3-day moving average smoothing to the mood values
    raw_moods = [point["mood"] for point in trend]
    smoothed_moods = _smooth(raw_moods, k=3)

    # attach the smoothed values back onto each trend point for the template
    for point, smooth_value in zip(trend, smoothed_moods):
        # store as `mood_smooth` so the template can access it explicitly
        point["mood_smooth"] = smooth_value

    # 4) compute "risk days" in the last week
    risk_days = []
    for point in trend:
        # extract daily status and mood from the point dictionary
        status = point.get("status")
        mood = point.get("mood")

        # check if day should be counted as "risky"
        if status in {"warn", "block"} or (mood is not None and mood <= 2):
            risk_days.append(point)

    # precompute the count for easier template rendering
    risk_count = len(risk_days)

    # 5) fetch the most recent HRV reading for the current user
    latest_hrv = (
        HRVReading.objects.filter(user=request.user)
        .order_by("-measured_at")  # assuming `measured_at` datetime field exists
        .first()
    )

    # classify readiness using our helper (Ref-B)
    readiness_info = _classify_readiness(latest_hrv)

    # 6) compute the predicted adherence probability for the next habit
    completion_probability = predict_habit_completion_probability(request.user)

    # convert to a percentage with one decimal place for display
    completion_probability_percent = round(completion_probability * 100.0, 1)

    # 7) Build the context dictionary for the template
    context = {
        # streak information in a nested structure (keeps template simple)
        "streak": {"days": streak_days},
        # 7-day trend including smoothed mood values
        "trend": trend,
        # risk-day analytics (count and detailed list)
        "risk_count": risk_count,
        "risk_days": risk_days,
        # HRV-based readiness classification from Step 5
        "readiness": readiness_info,
        # logistic-model forecast percentage (Step 6)
        "completion_prob": completion_probability_percent,
    }

    # 8) Render the dashboard template with the full analytics context
    return render(request, "checkins/dashboard.html", context)


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
