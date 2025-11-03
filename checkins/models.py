from __future__ import annotations

# import Django ORM helpers
from django.conf import settings
from django.db import models
from django.utils import timezone


# define CheckIn model representing a user’s daily check-in
class CheckIn(models.Model):
    # possible status values with human-readable labels
    STATUS_CHOICES = [
        ("ok", "OK / On Track"),
        ("warn", "At Risk"),
        ("block", "Blocked"),
    ]

    # link each check-in to a specific user (foreign key to Django User model)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # dynamic reference to current user model
        on_delete=models.CASCADE,  # delete check-ins if user is deleted
        related_name="checkins",  # reverse name for user.checkins
    )

    # store the exact UTC timestamp of the check-in
    checked_in_at = models.DateTimeField(
        default=timezone.now,  # default to current time
        db_index=True,  # add index for faster queries
    )

    # store user’s local calendar day (for enforcing one-per-day)
    local_date = models.DateField(db_index=True)

    # short status indicator (choice field)
    status = models.CharField(
        max_length=8,
        choices=STATUS_CHOICES,
        default="ok",
        db_index=True,
    )

    # optional free-text note
    note = models.TextField(blank=True, default="")

    # optional 1–5 mood rating
    mood = models.PositiveSmallIntegerField(null=True, blank=True)

    # optional text to identify data source (web, api, cron, etc.)
    source = models.CharField(max_length=16, default="web")

    # optional comma-separated tags
    tags = models.CharField(max_length=255, blank=True, default="")

    # optional HRV RMSSD (ms)
    hrv_rmssd = models.FloatField(null=True, blank=True)

    class Meta:
        # ensure one check-in per user per date
        constraints = [
            models.UniqueConstraint(
                fields=["user", "local_date"],
                name="uniq_checkin_per_user_per_day",
            )
        ]
        # create indexes for common queries
        indexes = [
            models.Index(fields=["user", "checked_in_at"]),
            models.Index(fields=["user", "status", "local_date"]),
        ]

    def __str__(self):
        # human-readable string representation
        return f"{self.user} @ {self.local_date} ({self.status})"


# define Habit model representing user-defined habits with prompts and celebrations
class Habit(models.Model):
    # define prompt types for habit anchoring
    class PromptType(models.TextChoices):
        ACTION_ANCHOR = "ACTION_ANCHOR", "Action-Anchor"
        CONTEXT = "CONTEXT", "Context (time/location)"
        PERSON = "PERSON", "Person (social)"

    # define prompt variants for A/B testing of prompt wording
    class PromptVariant(models.TextChoices):
        A = "A", "Anchor wording"
        B = "B", "Generic reminder"

    # link each habit to a specific user
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # dynamic reference to user model
        on_delete=models.CASCADE,  # delete habits if user is deleted
    )

    # name of the habit (e.g., “Stretch after brushing teeth”)
    name = models.CharField(max_length=120)

    # optional anchor phrase describing the trigger action (e.g., “After I brush my teeth…”)
    anchor_text = models.CharField(
        max_length=200,
        blank=True,
        help_text="“After I [existing action], I will [tiny behavior] …”",
    )

    # type of prompt (action-anchor, context, or person)
    prompt_type = models.CharField(
        max_length=20,
        choices=PromptType.choices,
        default=PromptType.ACTION_ANCHOR,
    )

    # short positive message reinforcing success (Tiny Habits “celebration”)
    celebration_note = models.CharField(
        max_length=120,
        blank=True,
        help_text="Short positive phrase to reinforce success (e.g., “Nice!”).",
    )

    # randomized prompt variant for A/B testing (Ref-A: Fogg’s MAP Model)
    prompt_variant = models.CharField(
        max_length=1,
        choices=PromptVariant.choices,
        default=PromptVariant.A,
        help_text="Randomized wording variant for A/B analysis.",
    )

    # auto timestamp when the habit was created
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        # human-readable representation for admin and logs
        return self.name


# define HabitCheckIn model representing a single completion event for a habit
class HabitCheckIn(models.Model):
    # link each check-in to a specific habit
    habit = models.ForeignKey(
        Habit,  # reference to the related Habit model
        on_delete=models.CASCADE,  # delete check-ins if the habit is deleted
        related_name="checkins",  # reverse relation: habit.checkins.all()
    )

    # link each check-in to the user who completed it
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # dynamic reference to current user model
        on_delete=models.CASCADE,  # delete check-ins if user is deleted
    )

    # exact timestamp of when the habit was completed
    done_at = models.DateTimeField()

    # optional short note for reflections or context
    note = models.CharField(max_length=200, blank=True)

    def __str__(self):
        # human-readable string representation
        return f"{self.user} - {self.habit} @ {self.done_at}"


# define BiometricsDaily model storing per-day HRV metrics for readiness tracking
class BiometricsDaily(models.Model):
    # link each biometric record to a specific user
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # reference to user model
        on_delete=models.CASCADE,  # cascade delete if user is removed
    )

    # local date of measurement
    date = models.DateField(db_index=True)

    # RMSSD metric (Root Mean Square of Successive Differences) in ms — HRV indicator
    rmssd = models.FloatField(null=True, blank=True)

    # SDNN metric (Standard Deviation of NN intervals) in ms — HRV variability context
    sdnn = models.FloatField(null=True, blank=True)

    # resting heart rate for contextual reference
    resting_hr = models.FloatField(null=True, blank=True)

    class Meta:
        # ensure only one biometric record per user per date
        unique_together = ("user", "date")

    def __str__(self) -> str:
        # human-readable string for debugging/admin
        return f"{self.user} biometrics on {self.date}"
