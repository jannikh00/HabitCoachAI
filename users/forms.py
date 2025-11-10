from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm


# custom user registration form
class RegisterForm(UserCreationForm):

    # additional required email field for registration
    email = forms.EmailField(required=True)

    class Meta:
        # specify model used for registration
        model = User

        # fields to include in the registration form
        fields = ["username", "email", "password1", "password2"]
