from django.urls import path

from . import views
from .chat_views import ChatView
from .profile_photo import ProfilePhotoView
from .auth_extra import GoogleConfigView, GoogleLoginView, PasswordResetConfirmView, PasswordResetRequestView
from .billing import BillingStatusView, CheckoutView, ConfirmCheckoutView, webhook
from .push import (
    NotificationCountView, NotificationListView, NotificationReadView, PushConfigView, PushTestView, SubscriptionView,
)

urlpatterns = [
    path("billing/status/", BillingStatusView.as_view()),
    path("billing/checkout/", CheckoutView.as_view()),
    path("billing/confirm/", ConfirmCheckoutView.as_view()),
    path("billing/webhook/", webhook),
    path("push/config/", PushConfigView.as_view()),
    path("push/subscriptions/", SubscriptionView.as_view()),
    path("push/test/", PushTestView.as_view()),
    path("notifications/", NotificationListView.as_view()),
    path("notifications/count/", NotificationCountView.as_view()),
    path("notifications/<int:pk>/read/", NotificationReadView.as_view()),
    path("chat/", ChatView.as_view()),
    path("csrf/", views.csrf),
    path("auth/register/", views.RegisterView.as_view()),
    path("auth/login/", views.LoginView.as_view()),
    path("auth/logout/", views.LogoutView.as_view()),
    path("auth/google/config/", GoogleConfigView.as_view()),
    path("auth/google/", GoogleLoginView.as_view()),
    path("auth/password-reset/", PasswordResetRequestView.as_view()),
    path("auth/password-reset/confirm/", PasswordResetConfirmView.as_view()),
    path("me/", views.MeView.as_view()),
    path("me/photo/", ProfilePhotoView.as_view()),
    path("careers/", views.CareerListView.as_view()),
    path("careers/<slug:slug>/", views.CareerDetailView.as_view()),
    path("careers/<slug:slug>/assessment/", views.CareerAssessmentView.as_view()),
    path("career-assessments/", views.CareerAssessmentListView.as_view()),
    path("courses/<int:pk>/", views.CourseView.as_view()),
    path("courses/", views.CourseListView.as_view()),
    path("courses/<int:pk>/complete/", views.CompleteCourseView.as_view()),
    path("labs/<int:pk>/start/", views.StartLabView.as_view()),
    path("labs/<int:pk>/", views.LabDetailView.as_view()),
    path("labs/", views.LabListView.as_view()),
    path("attempts/<int:pk>/submit/", views.SubmitAttemptView.as_view()),
    path("results/<int:pk>/", views.ResultView.as_view()),
    path("progress/", views.ProgressView.as_view()),
    path("recommendations/", views.RecommendationsView.as_view()),
]
