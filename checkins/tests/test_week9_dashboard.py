# imports
from django.urls import reverse
from django.test import Client
import pytest


@pytest.mark.django_db  # mark this test as using the database
def test_about_methods_view_renders_for_logged_in_user(django_user_model):
    """
    Ensure the About & Methods page is accessible to authenticated users
    and contains the expected reference summaries.
    """
    # create a test user using Django's user model
    _ = django_user_model.objects.create_user(
        username="testuser",  # username for the new user
        password="testpassword123",  # password for the new user
    )

    # initialize a Django test client instance
    client = Client()

    # log the user in (returns True on success)
    assert client.login(username="testuser", password="testpassword123")

    # build the URL for the about_methods view using its name
    url = reverse("checkins:about_methods")

    # send a GET request to the constructed URL
    response = client.get(url)

    # assert that the HTTP status code is 200 (OK)
    assert response.status_code == 200

    # decode the response content into a string for inspection
    content = response.content.decode()

    # check that each reference summary appears in the HTML content
    assert "Tiny Habits" in content  # Ref-A: Tiny Habits PDF
    assert "Heart rate variability" in content or "HRV" in content  # Ref-B: HRV paper
    assert "Statistical Learning" in content or "ISL" in content  # Ref-C: ISL PDF
