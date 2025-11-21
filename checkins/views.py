from __future__ import annotations

# imports
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render, get_object_or_404
from django.utils import timezone
from zoneinfo import ZoneInfo
from datetime import timedelta
from .models import CheckIn, Habit, HRVReading, HabitAnchor
from .forms import CheckInForm, HabitForm, HRVReadingForm, HabitAnchorForm
from .services.prompts import assign_prompt_variant
from .services.scoring import predict_habit_completion_probability
from types import SimpleNamespace


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


# edit an existing check-in for the logged-in user
@login_required
def checkin_edit_view(request, pk: int):

    checkin = get_object_or_404(CheckIn, pk=pk, user=request.user)

    if request.method == "POST":
        form = CheckInForm(request.POST, instance=checkin)
        if form.is_valid():
            form.save()
            return redirect("checkins:checkin_list")
    else:
        form = CheckInForm(instance=checkin)

    return render(request, "checkins/form.html", {"form": form})


# delete an existing check-in for the logged-in user
@login_required
def checkin_delete_view(request, pk: int):

    checkin = get_object_or_404(CheckIn, pk=pk, user=request.user)

    if request.method == "POST":
        checkin.delete()

    return redirect("checkins:checkin_list")


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
        return "After getting up in the morning: take one deep breath + one sip of water. (tiny, instant, anchored)"
    return "After breakfast: 10-second shoulder stretch. (small & consistent)"


# helper: build a short HRV tip based on the latest reading (Ref-B)
def _hrv_tip_from_last(latest_hrv: HRVReading | None) -> str:
    """
    Create a short, user-facing explanation for the HRV card.

    - if no HRV data is available yet, explain what HRV/RMSSD are
      and how the user can measure them
    - if we have a recent RMSSD value, give a simple interpretation
      (high / moderate / lower) plus optional resting HR context
    """

    # case 1: no data yet → explain HRV and how to measure it
    if latest_hrv is None or latest_hrv.rmssd_ms is None:
        return (
            "Heart Rate Variability (HRV) describes how much the time between your "
            "heartbeats changes from beat to beat. A simple way to track it is to "
            "measure RMSSD once each morning with a wearable or HRV app while you "
            "sit or lie still for about 60 seconds. Once you have a few days of "
            "data, this card will show how today's value compares to your usual range."
        )

    # we have at least one RMSSD reading
    rmssd = latest_hrv.rmssd_ms
    resting_hr = latest_hrv.resting_hr

    # start with the numeric fact for transparency
    tip = f"Today's RMSSD is about {rmssd:.0f} ms."

    # very simple, coarse interpretation ranges (educational, not clinical)
    if rmssd >= 60:
        tip += (
            " That is relatively high for most people and usually reflects good "
            "parasympathetic recovery."
        )
    elif rmssd >= 40:
        tip += (
            " That sits in a moderate range and often reflects normal day-to-day "
            "variation."
        )
    else:
        tip += (
            " That is on the lower side and can appear when stress, poor sleep, or "
            "training load are higher. Consider keeping today's habit especially "
            "small and recovery-friendly."
        )

    # add resting HR context when available
    if resting_hr:
        tip += f" Your resting heart rate was around {resting_hr:.0f} bpm."

    return tip


# helper: simple moving average for smoothing mood data (Ref-C)
def _smooth(values, k=3):
    res = []
    for i in range(len(values)):
        win = values[max(0, i - k + 1) : i + 1]
        win = [v for v in win if v is not None]
        res.append(sum(win) / len(win) if win else None)
    return res


# see description below
def _classify_readiness(latest_hrv: HRVReading | None) -> dict[str, str]:
    """
    Map the most recent HRV reading into a coarse readiness category.

    - uses RMSSD (ms) only, with simple thresholds:
        * >= 60 ms  → High readiness
        * 40–59 ms  → Moderate readiness
        * < 40 ms   → Low readiness
    - this keeps the logic aligned with the HRV note shown on the dashboard
      and avoids contradictions like "RMSSD is high" + "Low readiness".
    """

    # no HRV reading at all or missing RMSSD: supportive fallback
    rmssd = getattr(latest_hrv, "rmssd_ms", None) if latest_hrv is not None else None
    if rmssd is None:
        return {
            "label": "No HRV data yet",
            "description": (
                "We don't have HRV data for today. "
                "Use this as a chance to keep your habit tiny "
                "and celebrate one small win."
            ),
        }

    # high readiness: RMSSD clearly in a higher range
    if rmssd >= 60.0:
        return {
            "label": "High readiness",
            "description": (
                "Your HRV suggests good recovery. "
                "This is a good day to keep your tiny habits and, if you like, "
                "slightly increase the challenge."
            ),
        }

    # moderate readiness: normal day-to-day variation
    if rmssd >= 40.0:
        return {
            "label": "Moderate readiness",
            "description": (
                "Your HRV is in a moderate range, which often reflects normal "
                "day-to-day variation. Stay consistent with small, "
                "manageable habits."
            ),
        }

    # low readiness: RMSSD clearly on the lower side
    return {
        "label": "Low readiness",
        "description": (
            "Your current HRV pattern suggests higher load or incomplete "
            "recovery. Keep habits very small today and focus on easy wins "
            "and celebration."
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

    # 5) fetch HRV only for today (strict mode)
    tz = ZoneInfo("America/New_York")
    today = timezone.now().astimezone(tz).date()

    # try to find a dedicated HRVReading entry measured today
    latest_hrv = (
        HRVReading.objects.filter(
            user=request.user, measured_at__date=today  # strict: only today's date
        )
        .order_by("-measured_at")
        .first()
    )

    # fallback: if no HRVReading exists for today, try CheckIn.hrv_rmssd for today
    if latest_hrv is None:
        today_checkin = CheckIn.objects.filter(
            user=request.user, local_date=today, hrv_rmssd__isnull=False
        ).first()

        if today_checkin:
            # create a lightweight object to mimic HRVReading
            latest_hrv = SimpleNamespace(
                rmssd_ms=today_checkin.hrv_rmssd,
                resting_hr=None,
                measured_at=today_checkin.local_date,
            )

    # classify readiness using our helper (Ref-B)
    readiness_info = _classify_readiness(latest_hrv)

    # build a short HRV note for the dashboard card (Ref-B)
    hrv_tip = _hrv_tip_from_last(latest_hrv)

    # 6) compute the predicted adherence probability for the next habit
    completion_probability = predict_habit_completion_probability(request.user)

    # default values when probability is missing or outside expected range
    completion_probability_percent = 0.0
    completion_explanation = (
        "We were not able to compute a reliable forecast today. "
        "Use your own judgment and keep your next habit small."
    )

    # only proceed if the model actually returned a numeric probability
    if completion_probability is not None:
        # convert to a percentage with one decimal place for display
        completion_probability_percent = round(completion_probability * 100.0, 1)

        # check that the value lies within the expected probability range [0, 1]
        if 0.0 <= completion_probability <= 1.0:
            # convert the fraction (e.g., 0.58) into a percentage (e.g., 58%)
            completion_percent = int(round(completion_probability * 100))

            # base explanation shown to the user, describing what the number means
            completion_explanation = (
                f"This percentage is a simple estimate of how likely "
                f"you are to complete your next habit today ({completion_percent}%)."
            )

            # low forecast: <33% -> emphasize making the habit tiny and easy
            if completion_probability < 0.33:
                completion_explanation += (
                    " It looks like today might be challenging. "
                    "Shrink your habit and celebrate any small success."
                )

            # medium forecast: 33–67% -> neutral guidance
            elif completion_probability < 0.67:
                completion_explanation += (
                    " Your odds are moderate. A clear plan and a tiny habit can help."
                )

            # high forecast: >67% -> positive momentum but still framed as probability, not certainty
            else:
                completion_explanation += (
                    " Today looks favorable. Stick to your plan and enjoy the momentum."
                )

    # if probability is None: fallback to 0%
    else:
        completion_probability_percent = 0.0

    # generates a personalized suggestion based on the last 7 days
    # helper _tiny_prompt_from_last(trend) already existed from earlier iteration
    tiny_prompt = _tiny_prompt_from_last(trend)

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
        # logistic-model forecast explanation (Step 6)
        "completion_explanation": completion_explanation,
        # tiny habit suggestion
        "tiny_prompt": tiny_prompt,
        # HRV tip
        "hrv_tip": hrv_tip,
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

    anchors = HabitAnchor.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "checkins/habit_anchor_list.html", {"anchors": anchors})


# toggle the 'is_active' flag for a single habit anchor
@login_required
def habit_anchor_toggle_active_view(request, pk: int):

    anchor = get_object_or_404(HabitAnchor, pk=pk, user=request.user)

    if request.method == "POST":
        anchor.is_active = not anchor.is_active
        anchor.save()

    return redirect("checkins:habit-anchor-list")


# edit an existing Tiny Habits–style anchor
@login_required
def habit_anchor_edit_view(request, pk: int):

    anchor = get_object_or_404(HabitAnchor, pk=pk, user=request.user)

    if request.method == "POST":
        form = HabitAnchorForm(request.POST, instance=anchor)
        if form.is_valid():
            form.save()
            return redirect("checkins:habit-anchor-list")
    else:
        form = HabitAnchorForm(instance=anchor)

    return render(
        request,
        "checkins/habit_anchor_form.html",
        {"form": form},
    )


# delete an existing habit anchor
@login_required
def habit_anchor_delete_view(request, pk: int):

    anchor = get_object_or_404(HabitAnchor, pk=pk, user=request.user)

    if request.method == "POST":
        anchor.delete()

    return redirect("checkins:habit-anchor-list")


# render an 'About & Methods' page that explains:
@login_required
def about_methods_view(request):
    # create a dictionary containing the high-level description of each reference
    context = {
        # short explanation of Tiny Habits (Ref-A) for the template
        "tiny_habits_summary": (
            "This app uses B.J. Fogg's Tiny Habits method by pairing small, "
            "easy behaviors with existing daily 'anchors' and celebrating each success."
        ),
        # short explanation of HRV readiness (Ref-B) for the template
        "hrv_summary": (
            "Heart rate variability (HRV) metrics like RMSSD and resting heart rate "
            "are used as readiness signals, following current sports science research "
            "on training load and recovery."
        ),
        # short explanation of ISL-inspired modeling (Ref-C) for the template
        "isl_summary": (
            "Inspired by 'An Introduction to Statistical Learning', "
            "the app combines recent check-in trends and HRV data into a simple, "
            "interpretable probability score instead of a black-box model."
        ),
    }

    # render the 'checkins/about_methods.html' template with the context
    return render(request, "checkins/about_methods.html", context)
