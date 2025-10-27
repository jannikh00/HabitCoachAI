"""
Management command to seed demo check-ins for local testing and demos.
Creates a demo user (demo/demo) and about 10 days of randomized CheckIn entries.
"""

# imports
from __future__ import annotations
from datetime import timedelta
import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from zoneinfo import ZoneInfo
from checkins.models import CheckIn


class Command(BaseCommand):
    """Seeds demo data for development or demo purposes."""

    help = "Creates a demo user and populates about 10 recent check-ins."

    def handle(self, *args, **kwargs) -> None:
        # Create or update demo user
        user, _ = User.objects.get_or_create(
            username="demo", defaults={"is_active": True}
        )
        user.set_password("demo")
        user.save()

        # Get current date in local timezone
        tz = ZoneInfo("America/New_York")
        today = timezone.now().astimezone(tz).date()

        # Generate ~10 check-ins with randomized fields
        for i in range(10):
            day = today - timedelta(days=i)
            CheckIn.objects.get_or_create(
                user=user,
                local_date=day,
                defaults={
                    "status": random.choice(["ok", "ok", "warn", "block"]),
                    "mood": random.choice([None, 2, 3, 4, 5]),
                    "hrv_rmssd": random.choice([None, 35.0, 50.0, 70.0]),
                    "source": "seed",
                },
            )

        # Output confirmation in console
        self.stdout.write(self.style.SUCCESS("Seeded demo data for user demo/demo"))
