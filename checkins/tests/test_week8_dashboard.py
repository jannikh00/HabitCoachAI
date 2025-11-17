# imports
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from checkins.models import CheckIn, HRVReading

# mark all tests in this module as needing the database
pytestmark = pytest.mark.django_db


# see below
def test_dashboard_context_includes_week8_metrics(client):
    """
    verify that the unified Week 8 dashboard provides:

    - streak.days
    - 7-day trend list
    - risk_count and risk_days
    - readiness (label + description)
    - completion_prob (percentage from logistic model)
    """

    # 1) create a test user and log them in
    # get the Django User model
    User = get_user_model()
    # create a new user in the DB
    user = User.objects.create_user(
        username="bob",
        password="secret123",
    )
    # log in via Django test client
    client.force_login(user)

    # 2) create several check-ins for the last few days with varying moods and statuses
    # current local date
    today = timezone.now().date()
    # create 3 consecutive days
    for i in range(3):
        # for each day compute the date offset
        d = today - timezone.timedelta(days=i)
        # create a check-in entry with distinct mood/status
        CheckIn.objects.create(
            user=user,
            local_date=d,
            # descending mood values: 5,4,3
            mood=5 - i,
            # last one as a "warn" risk day
            status="ok" if i < 2 else "warn",
        )

    # 3) add a recent HRVReading so readiness classification has data
    HRVReading.objects.create(
        user=user,
        # measured "now"
        measured_at=timezone.now(),
        # moderate HRV
        rmssd_ms=55.0,
        # moderate resting HR
        resting_hr=65,
    )

    # 4) call the dashboard view through the URLconf
    # resolve the dashboard URL
    url = reverse("checkins:dashboard")
    # perform a GET request
    response = client.get(url)

    # ensure we got a successful HTTP response
    assert response.status_code == 200

    # 5) extract the context from the response and assert presence of all Week 8 analytics keys
    ctx = response.context

    # streak should be present with a "days" field
    assert "streak" in ctx
    assert "days" in ctx["streak"]
    assert ctx["streak"]["days"] >= 1

    # trend should be a list (created 3 check-ins)
    assert "trend" in ctx
    assert len(ctx["trend"]) >= 3

    # risk analytics
    assert "risk_count" in ctx
    assert "risk_days" in ctx
    # at least one risk day because a "warn" status was added
    assert ctx["risk_count"] >= 1
    assert len(ctx["risk_days"]) == ctx["risk_count"]

    # readiness classification using HRV
    assert "readiness" in ctx
    assert "label" in ctx["readiness"]
    assert "description" in ctx["readiness"]

    # logistic-model forecast (percentage)
    assert "completion_prob" in ctx
    assert isinstance(ctx["completion_prob"], float)
    # probability in sensible bounds [0, 100]
    assert 0.0 <= ctx["completion_prob"] <= 100.0
