from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import Notification, PushSubscription, User
from .push import welcome_once


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class WelcomeTests(TestCase):
    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)
        self.user = User.objects.create_user("welcome@example.test", "Welcome-test-932!", name="Student")

    def auth(self, mode="login", language="fr", password="Welcome-test-932!"):
        self.client.get("/api/csrf/")
        payload = {"email": self.user.email, "password": password}
        if mode == "register":
            payload.update(email="new-welcome@example.test", name="New student")
        return self.client.post(
            f"/api/auth/{mode}/", payload, format="json",
            HTTP_X_CSRFTOKEN=self.client.cookies["csrftoken"].value,
            HTTP_ACCEPT_LANGUAGE=language,
        )

    def test_first_login_creates_private_localized_welcome_once_even_after_delete(self):
        self.assertEqual(self.auth(password="Wrong").status_code, 400)
        self.assertFalse(Notification.objects.exists())
        self.assertEqual(self.auth().status_code, 200)
        notification = Notification.objects.get(user=self.user)
        self.assertEqual(notification.title, "Bienvenue sur CareerVerse !")
        self.assertEqual(notification.path, "/careers")
        self.assertFalse(notification.read)
        self.assertFalse(notification.deliveries.exists())
        self.assertEqual(self.auth().status_code, 200)
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 1)
        self.assertEqual(self.client.delete(
            "/api/notifications/", HTTP_X_CSRFTOKEN=self.client.cookies["csrftoken"].value
        ).status_code, 204)
        self.assertEqual(self.auth().status_code, 200)
        self.assertFalse(Notification.objects.filter(user=self.user).exists())
        self.user.refresh_from_db()
        self.assertTrue(self.user.welcome_notified)

    def test_registration_auto_login_welcomes_only_once(self):
        self.assertEqual(self.auth("register", "ar").status_code, 201)
        user = User.objects.get(email="new-welcome@example.test")
        self.assertTrue(user.welcome_notified)
        self.assertEqual(Notification.objects.get(user=user).title, "مرحباً بك في CareerVerse!")
        welcome_once(user, "fr")
        self.assertEqual(Notification.objects.filter(user=user).count(), 1)
        self.assertFalse(Notification.objects.filter(user=self.user).exists())

    def test_existing_welcomed_user_and_unsupported_language(self):
        self.user.welcome_notified = True
        self.user.save(update_fields=["welcome_notified"])
        self.assertEqual(self.auth().status_code, 200)
        self.assertFalse(Notification.objects.exists())
        self.user.welcome_notified = False
        self.user.save(update_fields=["welcome_notified"])
        self.assertEqual(self.auth(language="de-DE").status_code, 200)
        self.assertEqual(Notification.objects.get().title, "Welcome to CareerVerse!")

    def test_failed_enqueue_rolls_back_marker_and_subscription_queues_delivery(self):
        with patch("academy.push.enqueue_notification", side_effect=RuntimeError("Unavailable")):
            with self.assertRaises(RuntimeError):
                welcome_once(self.user, "en")
        self.user.refresh_from_db()
        self.assertFalse(self.user.welcome_notified)
        subscription = PushSubscription.objects.create(
            user=self.user, endpoint="https://fcm.googleapis.com/welcome-test",
            p256dh="test", auth="test", language="ar",
        )
        welcome_once(self.user, "fr")
        notification = Notification.objects.get(user=self.user)
        self.assertEqual(notification.title, "Bienvenue sur CareerVerse !")
        self.assertEqual(notification.deliveries.get(subscription=subscription).title, "مرحباً بك في CareerVerse!")
