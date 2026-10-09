from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Notification, PushDelivery, PushSubscription, User


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class NotificationDeleteTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("notification-delete@example.test", "Test-only-932!", name="Student")
        self.other = User.objects.create_user("other-notification@example.test", "Test-only-932!", name="Other")
        self.notification = Notification.objects.create(user=self.user, title="Update", body="Ready", path="/labs")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_delete_own_notification_and_pending_deliveries_preserves_subscription(self):
        subscription = PushSubscription.objects.create(user=self.user, endpoint="https://fcm.googleapis.com/test",
                                                       p256dh="test", auth="test", language="en")
        PushDelivery.objects.create(notification=self.notification, subscription=subscription,
                                    title="Update", body="Ready", next_attempt_at=timezone.now())
        Notification.objects.bulk_create([
            Notification(user=self.user, title="Older", body="Ready", path="/labs", read=index % 2 == 0)
            for index in range(55)
        ])
        foreign = Notification.objects.create(user=self.other, title="Private", body="Other", path="/labs")
        self.assertEqual(len(self.client.get("/api/notifications/").json()), 50)
        response = self.client.delete("/api/notifications/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Notification.objects.filter(user=self.user).exists())
        self.assertTrue(Notification.objects.filter(pk=foreign.pk).exists())
        self.assertFalse(PushDelivery.objects.exists())
        self.assertTrue(PushSubscription.objects.exists())
        self.assertEqual(self.client.get("/api/notifications/").json(), [])
        self.assertEqual(self.client.delete("/api/notifications/").status_code, 204)

    def test_other_owner_and_anonymous_cannot_delete(self):
        path = "/api/notifications/"
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.delete(path).status_code, 204)
        self.assertTrue(Notification.objects.filter(pk=self.notification.pk).exists())
        self.client.force_authenticate(None)
        self.assertEqual(self.client.delete(path).status_code, 403)
        self.assertTrue(Notification.objects.filter(pk=self.notification.pk).exists())

    def test_session_delete_requires_csrf(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.delete("/api/notifications/").status_code, 403)
