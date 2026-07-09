from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .forms import MotherLoginForm

urlpatterns = [
    path("", views.landing_page, name="landing"),
    # dashboard/ removed -- now handled by apps.pregnancy_dashboard

    # Mother auth
    path("register/", views.register_page, name="register-page"),
    path("login/", auth_views.LoginView.as_view(
        template_name="accounts/login.html",
        authentication_form=MotherLoginForm,
    ), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # Hospital staff auth
    path("staff/login/", views.staff_login_page, name="staff-login"),
    path("staff/register/", views.staff_register_page, name="staff-register"),
]