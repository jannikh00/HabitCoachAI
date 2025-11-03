"""
Management command to seed demo data for local testing and demos.
Creates a demo user (demo/demo), a few anchor-based habits (A/B variants),
about 10 days of daily CheckIn entries, 14 days of HabitCheckIn completions,
and a short HRV (BiometricsDaily) series.
"""

from __future__ import annotations

# imports
import random
from datetime import datetime, timedelta, time
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone
from zoneinfo import ZoneInfo
from checkins.models import Habit, CheckIn, BiometricsDaily, HabitCheckIn
from checkins.services.prompts import assign_prompt_variant

# dynamically load the active user model
User = get_user_model()


# define custom management command for seeding demo data
class Command(BaseCommand):
    # short CLI description shown in "python manage.py help"
    help = "Seed demo data: demo user, habits, check-ins, and HRV series."

    def handle(self, *args, **options):
        # 1) create or update demo user
        demo, _ = User.objects.get_or_create(
            username="demo",
            defaults={"email": "demo@example.com", "is_active": True},
        )
        demo.set_password("demo")
        demo.save()

        # 2) create demo habits with anchor texts and A/B prompt variants
        habits_data = [
            dict(
                name="Hydrate: one glass of water",
                anchor_text="After I start the kettle, I will fill my 12-oz water bottle.",
                prompt_type=Habit.PromptType.ACTION_ANCHOR,
                celebration_note="Nice — tiny win!",
            ),
            dict(
                name="1 push-up",
                anchor_text="After I brush my teeth in the morning, I will do 1 push-up.",
                prompt_type=Habit.PromptType.ACTION_ANCHOR,
                celebration_note="Yes! You showed up.",
            ),
            dict(
                name="Open notes app",
                anchor_text="After I sit down for lunch, I will open my notes app and jot 1 line.",
                prompt_type=Habit.PromptType.ACTION_ANCHOR,
                celebration_note="Small step done.",
            ),
        ]

        habits: list[Habit] = []
        for h in habits_data:
            habit, _ = Habit.objects.get_or_create(
                user=demo,
                name=h["name"],
                defaults={
                    "anchor_text": h["anchor_text"],
                    "prompt_type": h["prompt_type"],
                    "celebration_note": h["celebration_note"],
                    "prompt_variant": assign_prompt_variant(),
                },
            )
            habits.append(habit)

        # 3) generate ~14 days of HabitCheckIn completions with slight randomness
        tz = ZoneInfo("America/New_York")
        now = timezone.now().astimezone(tz)
        start = (now - timedelta(days=13)).date()

        for habit in habits:
            for i in range(14):
                day = start + timedelta(days=i)
                # assign completion probability based on A/B variant
                base_p = 0.65 if habit.prompt_variant == Habit.PromptVariant.B else 0.8
                if random.random() < base_p:
                    # pick a realistic completion time based on anchor text
                    lower_anchor = (habit.anchor_text or "").lower()
                    if "kettle" in lower_anchor:
                        t = time(7, 45)
                    elif "teeth" in lower_anchor:
                        t = time(7, 40)
                    elif "lunch" in lower_anchor:
                        t = time(12, 10)
                    else:
                        t = time(9, 0)

                    done_at = timezone.make_aware(datetime.combine(day, t))
                    HabitCheckIn.objects.get_or_create(
                        user=demo,
                        habit=habit,
                        done_at=done_at,
                        defaults={"note": ""},
                    )

        # 4) generate ~10 daily CheckIn records for general tracking
        today = now.date()
        for i in range(10):
            day = today - timedelta(days=i)
            CheckIn.objects.get_or_create(
                user=demo,
                local_date=day,
                defaults={
                    "status": random.choice(["ok", "ok", "warn", "block"]),
                    "mood": random.choice([None, 2, 3, 4, 5]),
                    "hrv_rmssd": random.choice([None, 35.0, 50.0, 70.0]),
                    "source": "seed",
                    "checked_in_at": timezone.now(),
                    "note": "",
                    "tags": "",
                },
            )

        # 5) create ~14 days of HRV biometrics with realistic fluctuations
        for i in range(14):
            day = start + timedelta(days=i)
            rmssd = max(15.0, random.gauss(50.0, 8.0))
            sdnn = max(15.0, random.gauss(55.0, 9.0))
            rhr = max(40.0, random.gauss(60.0, 3.0))
            BiometricsDaily.objects.update_or_create(
                user=demo,
                date=day,
                defaults=dict(rmssd=rmssd, sdnn=sdnn, resting_hr=rhr),
            )

        # final confirmation output in console
        self.stdout.write(
            self.style.SUCCESS(
                "Seed complete: demo user, habits (A/B), habit check-ins, daily check-ins, HRV data."
            )
        )
