# imports
import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from zoneinfo import ZoneInfo
from checkins.models import CheckIn


# test that creating a new check-in on the same day updates the existing one
@pytest.mark.django_db  # ensures test runs with a real database transaction
def test_create_updates_existing_today(client):
    # create and log in a test user
    u = User.objects.create_user(username="u", password="p")
    client.login(username="u", password="p")

    # resolve the check-in creation URL
    url = reverse("checkin_create")

    # first POST request – should create a new entry
    resp = client.post(url, {"status": "ok", "mood": 3})
    assert resp.status_code == 302  # redirect after successful creation
    assert CheckIn.objects.filter(user=u).count() == 1  # one check-in in DB

    # second POST request – same day, should update the existing entry
    resp = client.post(url, {"status": "warn", "mood": 2})
    c = CheckIn.objects.get(user=u)
    assert c.status == "warn"  # status updated
    assert c.mood == 2  # mood updated


# test that streak calculation counts consecutive check-in days correctly
@pytest.mark.django_db
def test_streak_counts_consecutive_days(client):
    # create a test user
    u = User.objects.create_user(username="u", password="p")

    # define timezone and current local date
    tz = ZoneInfo("America/New_York")
    today = timezone.now().astimezone(tz).date()

    # create two consecutive daily check-ins (today + yesterday)
    for d in [today, today - timezone.timedelta(days=1)]:
        CheckIn.objects.create(user=u, local_date=d, status="ok")

    # log in the user and access dashboard
    client.login(username="u", password="p")
    resp = client.get(reverse("dashboard"))
    assert resp.status_code == 200  # dashboard loads successfully
