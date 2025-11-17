from __future__ import annotations

# Service layer providing analytical logic for HRV-informed habit prediction
# Combines physiological (HRV) and behavioral (check-ins) signals using a simplified
# logistic regression model as described in *James et al., ISL (2021)*.

# imports
import math
from datetime import timedelta
from django.utils import timezone
from checkins.models import HRVReading, CheckIn


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


def _sigmoid(x: float) -> float:
    """
    Numerically safe sigmoid transformation.

    Formula:
        sigmoid(x) = 1 / (1 + e^(-x))

    Used to convert linear logits into probabilities (0–1 range).
    Handles overflow gracefully for extreme x values.
    """
    try:
        return 1.0 / (1.0 + math.exp(-x))
    except OverflowError:
        return 0.0 if x < 0 else 1.0


# ---------------------------------------------------------------------------
# Predictive Scoring Function
# ---------------------------------------------------------------------------


def predict_habit_completion_probability(user):
    """
    Estimate the probability that a user will complete their next habit check-in.

    Model rationale:
      - Behavioral feature: recent check-in frequency (proxy for consistency)
      - Physiological feature: HRV level (rMSSD) and resting HR (proxy for recovery/readiness)
      - Inspired by logistic regression modeling and feature weighting
        from *An Introduction to Statistical Learning* (James et al., 2021)

    Note:
      This is a hand-tuned placeholder model — not statistically fitted
      I'm aware a real version would be trained using collected data and validated
      with k-fold cross-validation
    """

    # current timestamp and 7-day lookback window
    now = timezone.now()
    week_ago = now - timedelta(days=7)

    # 1) Behavioral feature: number of check-ins in the past week
    recent_checkins = CheckIn.objects.filter(user=user, local_date__gte=week_ago)
    n_recent = recent_checkins.count()

    # 2) Physiological feature: latest HRV metrics (if available)
    latest_hrv = HRVReading.objects.filter(user=user).order_by("-measured_at").first()
    rmssd = latest_hrv.rmssd_ms if latest_hrv and latest_hrv.rmssd_ms else 0.0
    resting_hr = latest_hrv.resting_hr if latest_hrv and latest_hrv.resting_hr else 70

    # 3) Linear logit model:
    #    logit(p) = b0 + b1*n_recent + b2*(rmssd/100) + b3*(-resting_hr/100)
    # Coefficients are illustrative only (not fitted):
    b0 = -0.5  # baseline intercept
    b1 = 0.25  # weight for recent behavior
    b2 = 0.4  # weight for HRV (positive influence)
    b3 = 0.6  # weight for resting HR (negative influence)

    # compute logit value
    logit = (
        b0 + b1 * n_recent + b2 * (rmssd / 100.0) + b3 * (-(resting_hr - 60) / 100.0)
    )

    # transform to probability via sigmoid
    prob = _sigmoid(logit)
    return prob
