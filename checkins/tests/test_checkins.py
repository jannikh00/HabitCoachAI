# import testing tools and model
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from checkins.models import CheckIn

# mark test file as using Django DB
pytestmark = pytest.mark.django_db


def test_one_checkin_per_day():
    # create a test user
    User = get_user_model()
    u = User.objects.create_user(username="alice", password="x")
    today = timezone.now().date()

    # first check-in should work
    CheckIn.objects.create(user=u, local_date=today)

    # second check-in same day should raise integrity error
    with pytest.raises(Exception):
        CheckIn.objects.create(user=u, local_date=today)
