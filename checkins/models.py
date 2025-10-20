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
    note = models.TextField(blank=True)

    # optional 1–5 mood rating
    mood = models.PositiveSmallIntegerField(null=True, blank=True)

    # optional text to identify data source (web, api, cron, etc.)
    source = models.CharField(max_length=32, blank=True)

    # optional comma-separated tags
    tags = models.CharField(max_length=128, blank=True)

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
