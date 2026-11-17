from django.urls import path, reverse_lazy
from accounts import views
from django.contrib.auth import views as auth_views
from accounts.forms import PasswordResetUsernameForm

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name = "login"),
    path("register/", views.register_view, name = "register"),
    path("logout/", views.logout_view, name = "logout"),
    path("password-change/", views.password_change_view, name = "password_change"),
    path(
        "password-reset/",
        views.CustomPasswordResetView.as_view(
            form_class=PasswordResetUsernameForm,
            template_name="accounts/password_reset.html",
            email_template_name="accounts/password_reset_email.html",
            subject_template_name="accounts/password_reset_subject.txt",
            success_url=reverse_lazy("accounts:password_reset_done"),
        ),
        name = "password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="accounts/password_reset_done.html"
        ),
        name = "password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        views.CustomPasswordResetConfirmView.as_view(
            template_name = "accounts/password_reset_confirm.html",
            success_url = reverse_lazy("accounts:password_reset_complete"),
        ),
        name = "password_reset_confirm"
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name = "accounts/password_reset_complete.html",
        ),
        name = "password_reset_complete"
    ),
    path("verify-email/", views.verify_email_view, name = "verify_email"),
    path("resend-verification-otp/", views.resend_verification_otp_view, name="resend_verification_otp"),
    path("profile/", views.profile_view, name="profile"),
    path("profile/edit/", views.profile_edit_view, name="profile_edit"),
    path("email/change/", views.email_change_view, name="email_change"),
    path("email/change/verify", views.verify_email_change_view, name="verify_email_change"),
    path("email/change/resend/", views.resend_email_change_otp_view, name="resend_email_change_otp"),
]
