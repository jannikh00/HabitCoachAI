from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic import CreateView
from .forms import RegisterForm


# custom user login view extending Django’s built-in LoginView
class UserLoginView(LoginView):

    # specify template used for rendering the login page
    template_name = "users/login.html"

    # define post-login redirect route
    def get_success_url(self):
        return reverse_lazy("checkins:dashboard")


# custom logout view extending Django’s built-in LogoutView
class UserLogoutView(LogoutView):

    # redirect target after successful logout
    template_name = "users/logout.html"


# view handling user registration
class RegisterView(CreateView):

    # specify which HTML template to render
    template_name = "users/register.html"

    # bind the form class to this view
    form_class = RegisterForm

    # redirect destination upon successful registration
    success_url = reverse_lazy("users:login")
