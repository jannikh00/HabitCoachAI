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


# HRVReading Model
class HRVReading(models.Model):
    """
    Stores a single HRV-related measurement for a user.

    Scientific basis:
     HRV (Heart-Rate Variability) is used to assess autonomic nervous-system (ANS)
     balance and training adaptation. Research shows that monitoring rMSSD and SDNN
     indices can help adjust workload and recovery in athletes, as ANS shifts toward
     sympathetic dominance under intense training stimuli  [oai_citation:3‡fspor-1-1574087.pdf](file-service://file-3EVASBZjiZtSikC4S7tY8U).
    """

    # Link each reading to a specific user; cascade deletion removes readings on user deletion
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="hrv_readings",
    )

    # Timestamp when measurement was taken (default = current time for convenience in logging)
    measured_at = models.DateTimeField(default=timezone.now)

    # rMSSD (ms) — root mean square of successive differences between RR intervals;
    # reflects short-term parasympathetic activity
    rmssd_ms = models.FloatField(help_text="rMSSD in ms", null=True, blank=True)

    # SDNN (ms) — standard deviation of NN intervals; captures overall HRV variability
    sdnn_ms = models.FloatField(help_text="SDNN in ms", null=True, blank=True)

    # Resting heart rate (bpm); useful for interpreting fatigue and readiness
    resting_hr = models.PositiveIntegerField(
        help_text="Resting heart rate in bpm", null=True, blank=True
    )

    # Optional notes (e.g., context like “post-match morning” or “after recovery day”)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        # Order most recent measurements first for dashboard queries
        ordering = ["-measured_at"]

    def __str__(self) -> str:
        """Readable string representation (e.g., ‘HRV demo @ 2025-11-09 06:30’)."""
        return f"HRV {self.user} @ {self.measured_at:%Y-%m-%d %H:%M}"


# HabitAnchor Model
class HabitAnchor(models.Model):
    """
    Implements the Tiny Habits "After I ..., I will ..." recipe structure.

    Behavioral basis:
     According to B.J. Fogg’s Behavior Model, no behavior occurs without a prompt (MAP = Motivation,
     Ability, Prompt). Action Prompts — or Anchors — attach new tiny behaviors to existing routines,
     dramatically improving habit adherence  [oai_citation:4‡Tiny Habits PDF.pdf](file-service://file-NuAXva6xhrtkyTnQcJKoan).
     Celebration further reinforces positive emotion and habit consolidation  [oai_citation:5‡Tiny Habits PDF.pdf](file-service://file-NuAXva6xhrtkyTnQcJKoan).
    """

    # Each anchor belongs to one user
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="habit_anchors",
    )

    # Existing behavior that serves as the anchor (prompt). E.g., "after I brush my teeth"
    anchor_action = models.CharField(
        max_length=160,
        help_text="Existing action (e.g., ‘after I brush my teeth at night’).",
    )

    # The tiny new behavior attached to the anchor (prompt + action pair)
    tiny_behavior = models.CharField(
        max_length=160,
        help_text="Small behavior (e.g., ‘I will do 3 deep breaths’).",
    )

    # Optional celebration — positive emotion reinforcement (e.g., smile or fist pump)
    celebration = models.CharField(
        max_length=160,
        blank=True,
        help_text="How to celebrate (Fogg: emotions wire habits).",
    )

    # Active flag allows disabling anchors without deletion (UX toggle or archive feature)
    is_active = models.BooleanField(default=True)

    # Auto-timestamp when anchor was created
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Order newest anchors first for quick retrieval in habit dashboards
        ordering = ["-created_at"]

    def __str__(self) -> str:
        # Readable summary in Tiny Habits syntax
        return f"After {self.anchor_action} I will {self.tiny_behavior}"
