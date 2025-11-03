from __future__ import annotations

# imports
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, time
from typing import Optional
from django.utils import timezone
from ..models import Habit


# randomly assign a prompt variant (A or B) for A/B testing
def assign_prompt_variant() -> Habit.PromptVariant:
    # balanced random selection between two prompt styles
    return random.choice([Habit.PromptVariant.A, Habit.PromptVariant.B])


# define simple dataclass representing the next scheduled prompt
@dataclass
class ScheduledPrompt:
    next_fire_at: datetime  # exact datetime the prompt should trigger
    reason: str  # explanation for why this time was chosen (e.g., "from_anchor")


# internal helper: infer approximate time of day from anchor text
def _guess_anchor_time(anchor_text: str) -> Optional[time]:
    # return None if no anchor text provided
    if not anchor_text:
        return None

    lowered = anchor_text.lower()

    # morning-related anchors
    if (
        "wake" in lowered
        or "morning" in lowered
        or "breakfast" in lowered
        or "brush my teeth" in lowered
    ):
        return time(hour=7, minute=30)

    # midday anchors
    if "lunch" in lowered or "noon" in lowered or "midday" in lowered:
        return time(hour=12, minute=0)

    # evening anchors
    if (
        "commute home" in lowered
        or "after work" in lowered
        or "dinner" in lowered
        or "evening" in lowered
    ):
        return time(hour=18, minute=30)

    # quick “while waiting” anchors — fire soon after current time
    if "kettle" in lowered or "microwave" in lowered or "boil" in lowered:
        return (datetime.now() + timedelta(minutes=5)).time()

    # fallback: no match found
    return None


# derive a next prompt time from a habit’s anchor text
def schedule_from_anchor(
    habit: Habit, now: Optional[datetime] = None
) -> ScheduledPrompt:
    # use current time if no explicit reference time provided
    now = now or timezone.now()

    # attempt to infer time from anchor text
    t = _guess_anchor_time(habit.anchor_text or "")
    if t is not None:
        # construct datetime for the inferred time today
        candidate = now.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
        # if that time has already passed, schedule for tomorrow
        if candidate <= now:
            candidate += timedelta(days=1)
        return ScheduledPrompt(next_fire_at=candidate, reason="from_anchor")

    # fallback: schedule for 09:00 next day if no anchor time recognized
    candidate = now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(
        days=1
    )
    return ScheduledPrompt(next_fire_at=candidate, reason="fallback_morning")
