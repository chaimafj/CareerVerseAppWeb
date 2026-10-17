import base64
import hashlib
import hmac
import json
import time
from copy import deepcopy
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

import requests
import stripe
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from pywebpush import WebPushException
from rest_framework.test import APIClient

from .models import (
    Attempt, Lab, Notification, PremiumCheckout, PushDelivery, PushSubscription, Result, User,
)
from .push import NoRedirectSession, enqueue_notification, send_pending


def encoded(value):
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def push_settings():
    key = ec.generate_private_key(ec.SECP256R1())
    return {
        "VAPID_PRIVATE_KEY": encoded(key.private_numbers().private_value.to_bytes(32, "big")),
        "VAPID_PUBLIC_KEY": encoded(key.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)),
        "VAPID_SUBJECT": "mailto:push@example.com",
    }


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class PushTests(TestCase):
    def setUp(self):
        self.settings_override = override_settings(**push_settings())
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.user = User.objects.create_user("push@example.com", "password", name="Owner")
        self.other = User.objects.create_user("other@example.com", "password", name="Other")
        self.client = APIClient(enforce_csrf_checks=True)
        self.client.force_login(self.user)
        self.client.get("/api/csrf/")
        self.token = self.client.cookies["csrftoken"].value
        self.payload = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/browser-token",
            "keys": {"p256dh": push_settings()["VAPID_PUBLIC_KEY"], "auth": encoded(b"x" * 16)},
            "language": "fr",
        }

    def post(self, url, body):
        return self.client.post(url, body, format="json", HTTP_X_CSRFTOKEN=self.token)

    def subscribe(self):
        self.assertEqual(self.post("/api/push/subscriptions/", self.payload).status_code, 201)
        return PushSubscription.objects.get(user=self.user)

    def test_config_disabled_and_keys(self):
        data = self.client.get("/api/push/config/").json()
        self.assertTrue(data["configured"])
        self.assertNotIn("private_key", data)
        with override_settings(VAPID_PRIVATE_KEY=""):
            self.assertEqual(self.client.get("/api/push/config/").json(), {"configured": False, "public_key": ""})
            self.assertEqual(self.post("/api/push/subscriptions/", self.payload).status_code, 503)
            self.assertEqual(self.post("/api/push/test/", {}).status_code, 503)

    def test_auth_csrf_and_ownership(self):
        self.assertEqual(self.client.post("/api/push/subscriptions/", self.payload, format="json").status_code, 403)
        self.subscribe()
        notification = enqueue_notification(self.user, "test", "/progress")
        self.client.force_login(self.other)
        self.assertEqual(self.post("/api/push/subscriptions/", self.payload).status_code, 409)
        self.assertEqual(self.client.get("/api/notifications/").json(), [])
        self.assertEqual(self.post(f"/api/notifications/{notification.pk}/read/", {}).status_code, 404)
        self.assertEqual(self.client.delete(
            "/api/push/subscriptions/", {"endpoint": self.payload["endpoint"]},
            format="json", HTTP_X_CSRFTOKEN=self.token,
        ).status_code, 204)
        self.assertEqual(PushSubscription.objects.count(), 1)
        self.client.logout()
        for url in ("/api/push/config/", "/api/notifications/", "/api/billing/status/"):
            self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.post("/api/push/subscriptions/", self.payload).status_code, 403)
        self.assertEqual(self.post("/api/push/test/", {}).status_code, 403)

    def test_malformed_and_ssrf(self):
        self.assertEqual(self.post("/api/push/subscriptions/", []).status_code, 400)
        for endpoint in [
            "http://fcm.googleapis.com/x", "https://localhost/x", "https://127.0.0.1/x",
            "https://192.168.1.1/x", "https://[::1]/x", "https://169.254.169.254/x",
            "https://fcm.googleapis.com.evil.example/x", "https://fcm.googleapis.com@127.0.0.1/x",
            "https://fcm.googleapis.com:444/x", "https://fcm.googleapis.com/x#fragment",
            "https://fcm.googleapis.com\\@localhost/x", "https://fcm.googleapis.com:bad/x",
            "https://wns.notify.windows.com.evil.example/x",
            "https://evilnotify.windows.com/x", "https://notify.windows.com/x",
            "https://wns.notify.windows.com@127.0.0.1/x",
            "http://wns.notify.windows.com/x", "https://wns.notify.windows.com:444/x",
            "https://wns.notify.windows.com/x#fragment",
            "https://bad_label.notify.windows.com/x",
            None, "x" * 2049,
        ]:
            with self.subTest(endpoint=endpoint):
                self.assertEqual(self.post("/api/push/subscriptions/", {**self.payload, "endpoint": endpoint}).status_code, 400)
        for change in [
            {"language": "de"}, {"keys": []},
            {"keys": {"p256dh": "a" * 101, "auth": "x"}},
            {"keys": {"p256dh": encoded(b"x" * 65), "auth": encoded(b"x" * 16)}},
            {"keys": {**self.payload["keys"], "auth": encoded(b"x" * 17)}},
        ]:
            self.assertEqual(self.post("/api/push/subscriptions/", {**self.payload, **change}).status_code, 400)
        self.assertFalse(PushSubscription.objects.exists())

    def test_edge_windows_push_subscription_update_and_delete(self):
        self.payload["endpoint"] = "https://wn2-test.notify.windows.com/w/?token=test-token"
        subscription = self.subscribe()
        self.assertEqual(subscription.endpoint, self.payload["endpoint"])
        self.payload["language"] = "ar"
        self.assertEqual(self.post("/api/push/subscriptions/", self.payload).status_code, 200)
        subscription.refresh_from_db()
        self.assertEqual(subscription.language, "ar")
        self.assertEqual(self.client.delete(
            "/api/push/subscriptions/", {"endpoint": self.payload["endpoint"]},
            format="json", HTTP_X_CSRFTOKEN=self.token,
        ).status_code, 204)
        self.assertFalse(PushSubscription.objects.exists())

    @patch("academy.push.webpush")
    def test_enqueue_test_and_read_without_network(self, provider):
        self.payload["expirationTime"] = None
        self.subscribe()
        response = self.post("/api/push/test/", {})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["title"], "Notifications CareerVerse")
        self.assertEqual(response.json()["path"], "/notifications")
        provider.assert_not_called()
        self.assertEqual(PushDelivery.objects.count(), 1)
        notification = Notification.objects.get()
        self.assertEqual(self.client.post(f"/api/notifications/{notification.pk}/read/", {}, format="json").status_code, 403)
        self.assertTrue(self.post(f"/api/notifications/{notification.pk}/read/", {}).json()["read"])
        self.assertEqual(send_pending(), 1)
        provider.assert_called_once()
        data = json.loads(provider.call_args.kwargs["data"])
        self.assertEqual(set(data), {"tag", "title", "body", "path"})
        self.assertEqual(data["tag"], f"notification-{notification.pk}")
        self.assertEqual(data["path"], "/notifications")
        self.assertNotIn("score", data)
        self.assertEqual(send_pending(), 0)

    @patch("academy.push.webpush")
    def test_submission_preserves_score_and_enqueues_once(self, provider):
        call_command("seed_demo", stdout=StringIO())
        self.subscribe()
        lab = Lab.objects.get(career__slug="angular", level=1)
        response = self.post(f"/api/labs/{lab.pk}/start/", {})
        attempt = Attempt.objects.get(pk=response.json()["id"])
        answers = {"answers": [
            {"question_id": q["id"], "option_ids": [o["id"] for o in q["options"] if o["correct"]]}
            for q in attempt.snapshot["questions"]
        ]}
        response = self.post(f"/api/attempts/{attempt.pk}/submit/", answers)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Result.objects.get().score, 100)
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(PushDelivery.objects.count(), 1)
        self.assertEqual(self.post(f"/api/attempts/{attempt.pk}/submit/", answers).status_code, 409)
        self.assertEqual(Notification.objects.count(), 1)
        provider.assert_not_called()

    @patch("academy.push.webpush")
    def test_expired_only_and_bounded_retry(self, provider):
        for code in [500, 403, 302, 404, 410]:
            with self.subTest(code=code):
                subscription = PushSubscription.objects.create(user=self.user, **{
                    "endpoint": f"https://fcm.googleapis.com/fcm/send/{code}",
                    **self.payload["keys"], "language": "ar",
                })
                enqueue_notification(self.user, "test", "/progress")
                response = requests.Response()
                response.status_code = code
                provider.side_effect = WebPushException("provider failure", response=response)
                self.assertEqual(send_pending(), 0)
                self.assertEqual(PushSubscription.objects.filter(pk=subscription.pk).exists(), code not in (404, 410))
                if code not in (404, 410):
                    for _ in range(4):
                        PushDelivery.objects.filter(subscription=subscription).update(next_attempt_at=timezone.now())
                        send_pending()
                    delivery = PushDelivery.objects.filter(subscription=subscription).latest("id")
                    self.assertTrue(delivery.failed)
                    self.assertEqual(delivery.attempts, 5)
                PushSubscription.objects.all().delete()

    def test_no_redirect_and_account_cascade(self):
        with patch("requests.Session.request") as send:
            NoRedirectSession().post("https://fcm.googleapis.com/x")
            self.assertFalse(send.call_args.kwargs["allow_redirects"])
        self.subscribe()
        enqueue_notification(self.user, "test", "/progress")
        self.user.delete()
        self.assertFalse(Notification.objects.exists())
        self.assertFalse(PushDelivery.objects.exists())
        self.assertFalse(PushSubscription.objects.exists())

    @patch("requests.Session.request")
    def test_real_encryption_vapid_with_mocked_transport(self, transport):
        self.subscribe()
        enqueue_notification(self.user, "test", "/progress")
        response = requests.Response()
        response.status_code = 201
        transport.return_value = response
        self.assertEqual(send_pending(), 1)
        headers = transport.call_args.kwargs["headers"]
        self.assertIn("vapid", headers["authorization"].lower())
        self.assertEqual(headers["content-encoding"], "aes128gcm")
        self.assertFalse(transport.call_args.kwargs["allow_redirects"])
        self.assertNotIn(b"CareerVerse", transport.call_args.kwargs["data"])

    @patch("academy.push.webpush")
    def test_worker_interruption_exhaustion_and_explicit_disabled_command(self, provider):
        self.subscribe()
        notification = enqueue_notification(self.user, "test", "/progress")
        notification.deliveries.update(attempts=5, next_attempt_at=timezone.now())
        with self.assertLogs("academy.push", level="ERROR"):
            self.assertEqual(send_pending(), 0)
        self.assertTrue(notification.deliveries.get().failed)
        provider.assert_not_called()
        from django.core.management.base import CommandError
        with override_settings(VAPID_PRIVATE_KEY=""), self.assertRaises(CommandError):
            call_command("send_push_notifications", stdout=StringIO())

    def test_latest_fifty_and_locale_per_subscription(self):
        self.subscribe()
        PushSubscription.objects.create(
            user=self.user, endpoint="https://web.push.apple.com/other",
            **self.payload["keys"], language="ar",
        )
        notification = enqueue_notification(self.user, "lab", "/results/1")
        self.assertEqual(notification.title, "اكتمل المختبر")
        self.assertEqual(set(notification.deliveries.values_list("title", flat=True)), {"Lab terminé", "اكتمل المختبر"})
        for _ in range(55):
            Notification.objects.create(user=self.user, title="Title", body="Body", path="/progress")
        self.assertEqual(len(self.client.get("/api/notifications/").json()), 50)

    def test_unread_count_is_complete_private_and_updates_after_changes(self):
        notifications = [
            Notification.objects.create(user=self.user, title="Update", body="Body", path="/careers")
            for _ in range(61)
        ]
        other = User.objects.create_user("other-count@example.test", "password", name="Other")
        Notification.objects.create(user=other, title="Private", body="Body", path="/careers")
        self.assertEqual(self.client.get("/api/notifications/count/").json(), {"unread_count": 61})
        self.assertEqual(len(self.client.get("/api/notifications/").json()), 50)
        self.assertEqual(self.post(f"/api/notifications/{notifications[0].pk}/read/", {}).status_code, 200)
        self.assertEqual(self.client.get("/api/notifications/count/").json(), {"unread_count": 60})
        self.assertEqual(self.post(f"/api/notifications/{notifications[0].pk}/read/", {}).status_code, 200)
        self.assertEqual(self.client.get("/api/notifications/count/").json(), {"unread_count": 60})
        self.client.get("/api/csrf/")
        token = self.client.cookies["csrftoken"].value
        self.assertEqual(self.client.delete("/api/notifications/", {}, format="json",
                                           HTTP_X_CSRFTOKEN=token).status_code, 204)
        self.assertEqual(self.client.get("/api/notifications/count/").json(), {"unread_count": 0})
        self.assertTrue(Notification.objects.filter(user=other).exists())
        self.client.logout()
        self.assertEqual(self.client.get("/api/notifications/count/").status_code, 403)


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    STRIPE_SECRET_KEY="sk_test_mock", STRIPE_WEBHOOK_SECRET="whsec_mock",
    STRIPE_PRICE_ID="price_mock", WEB_APP_ORIGIN="http://127.0.0.1:4200",
)
class BillingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("premium@example.com", "password", name="Owner")
        self.client = APIClient(enforce_csrf_checks=True)
        self.client.force_login(self.user)
        self.client.get("/api/csrf/")
        self.token = self.client.cookies["csrftoken"].value
        self.checkout = PremiumCheckout.objects.create(
            user=self.user, session_id="cs_test_mock", price_id="price_mock", amount=499, currency="eur",
        )
        self.session = {
            "id": self.checkout.session_id, "livemode": False, "mode": "payment",
            "status": "complete", "payment_status": "paid", "amount_total": 499, "currency": "eur",
            "client_reference_id": str(self.user.pk),
            "metadata": {"checkout_id": str(self.checkout.pk), "user_id": str(self.user.pk)},
            "line_items": {"has_more": False, "data": [
                {"quantity": 1, "price": {"id": "price_mock", "livemode": False},
                 "amount_total": 499, "currency": "eur"},
            ]},
        }

    def event(self, session=None, **changes):
        return {"id": "evt_mock", "object": "event", "livemode": False,
                "type": "checkout.session.completed", "data": {"object": session or self.session}, **changes}

    def webhook(self, event, signature=True):
        body = json.dumps(event).encode()
        timestamp = int(time.time())
        signed = hmac.new(b"whsec_mock", str(timestamp).encode() + b"." + body, hashlib.sha256).hexdigest()
        return self.client.post(
            "/api/billing/webhook/", body, content_type="application/json",
            HTTP_STRIPE_SIGNATURE=f"t={timestamp},v1={signed if signature else 'bad'}",
        )

    def test_status_disabled_live_keys_origin_and_csrf(self):
        self.assertEqual(self.client.get("/api/billing/status/").json(),
                         {"configured": True, "premium_until": None, "is_premium": False,
                          "amount": 499, "currency": "eur", "duration_days": 30,
                          "checkout_status": None, "transactions": []})
        self.assertEqual(self.client.post("/api/billing/checkout/", {}, format="json").status_code, 403)
        for changes in [
            {"STRIPE_SECRET_KEY": ""}, {"STRIPE_SECRET_KEY": "sk_live_forbidden"},
            {"STRIPE_WEBHOOK_SECRET": ""}, {"STRIPE_PRICE_ID": ""},
            {"WEB_APP_ORIGIN": "javascript:alert(1)"}, {"WEB_APP_ORIGIN": "https://example.com/evil"},
            {"WEB_APP_ORIGIN": "https://user:secret@example.com"}, {"WEB_APP_ORIGIN": "http://example.com"},
        ]:
            with self.subTest(changes=changes), override_settings(**changes):
                self.assertFalse(self.client.get("/api/billing/status/").json()["configured"])
                self.assertEqual(self.client.post("/api/billing/checkout/", {}, format="json",
                                                 HTTP_X_CSRFTOKEN=self.token).status_code, 503)
                self.assertEqual(self.webhook(self.event()).status_code, 503)

    @patch("academy.billing.stripe.checkout.Session.create")
    @patch("academy.billing.stripe.Price.retrieve")
    def test_checkout_server_price_and_no_redirect_grant(self, price, create):
        price.return_value = {"id": "price_mock", "livemode": False, "active": True,
                              "type": "one_time", "unit_amount": 499, "currency": "eur"}
        create.return_value = {"id": "cs_test_new", "livemode": False, "url": "https://checkout.stripe.com/test"}
        response = self.client.post("/api/billing/checkout/", {"price": "evil", "amount": 1},
                                    format="json", HTTP_X_CSRFTOKEN=self.token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(create.call_args.kwargs["line_items"], [{"price": "price_mock", "quantity": 1}])
        self.assertEqual(PremiumCheckout.objects.get(session_id="cs_test_new").amount, 499)
        self.user.refresh_from_db()
        self.assertIsNone(self.user.premium_until)
        price.return_value["livemode"] = True
        self.assertEqual(self.client.post("/api/billing/checkout/", {}, format="json",
                                         HTTP_X_CSRFTOKEN=self.token).status_code, 503)

    @patch("academy.billing.stripe.checkout.Session.retrieve")
    def test_paid_duplicate_and_extension_once(self, retrieve):
        retrieve.return_value = self.session
        expiry = timezone.now() + timedelta(days=10)
        self.user.premium_until = expiry
        self.user.save()
        self.assertEqual(self.webhook(self.event()).status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.premium_until, expiry + timedelta(days=30))
        self.assertEqual(self.webhook(self.event()).status_code, 200)
        self.assertEqual(self.webhook(self.event(id="evt_other")).status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.premium_until, expiry + timedelta(days=30))
        retrieve.assert_called_once()
        self.checkout.refresh_from_db()
        self.assertIsNotNone(self.checkout.paid_at)

    @patch("academy.billing.stripe.checkout.Session.retrieve")
    def test_expired_extension_from_now(self, retrieve):
        retrieve.return_value = self.session
        self.user.premium_until = timezone.now() - timedelta(days=10)
        self.user.save()
        before = timezone.now()
        self.assertEqual(self.webhook(self.event()).status_code, 200)
        self.user.refresh_from_db()
        self.assertGreaterEqual(self.user.premium_until, before + timedelta(days=30))
        self.assertLessEqual(self.user.premium_until, timezone.now() + timedelta(days=30))

    @patch("academy.billing.stripe.checkout.Session.retrieve")
    def test_two_distinct_payments_add_sixty_days_and_keep_history_boundaries(self, retrieve):
        expiry = timezone.now() + timedelta(days=7)
        self.user.premium_until = expiry
        self.user.save()
        retrieve.return_value = self.session
        self.assertEqual(self.webhook(self.event()).status_code, 200)
        second = PremiumCheckout.objects.create(
            user=self.user, session_id="cs_test_second", price_id="price_mock", amount=499, currency="eur",
        )
        session = {**self.session, "id": second.session_id,
                   "metadata": {"checkout_id": str(second.pk), "user_id": str(self.user.pk)}}
        retrieve.return_value = session
        self.assertEqual(self.webhook(self.event(session, id="evt_second")).status_code, 200)
        self.user.refresh_from_db()
        self.checkout.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(self.user.premium_until, expiry + timedelta(days=60))
        self.assertEqual(self.checkout.premium_until, expiry + timedelta(days=30))
        self.assertEqual(second.premium_until, expiry + timedelta(days=60))
        self.assertEqual(self.webhook(self.event(session, id="evt_second_retry")).status_code, 200)
        history = self.client.get("/api/billing/status/").json()["transactions"]
        self.assertEqual([row["id"] for row in history], [second.pk, self.checkout.pk])
        self.assertEqual(history[0]["premium_until"], second.premium_until.isoformat())
        self.assertEqual(history[1]["premium_until"], self.checkout.premium_until.isoformat())

    @patch("academy.billing.stripe.checkout.Session.retrieve")
    def test_signature_live_unpaid_and_mismatch(self, retrieve):
        retrieve.return_value = self.session
        self.assertEqual(self.webhook(self.event(), signature=False).status_code, 400)
        self.assertEqual(self.webhook(self.event(livemode=True)).status_code, 400)
        self.assertEqual(self.webhook(self.event({**self.session, "livemode": True})).status_code, 400)
        self.assertEqual(self.webhook(self.event({**self.session, "payment_status": "unpaid"})).status_code, 200)
        retrieve.assert_not_called()
        mutations = [
            {"amount_total": 1}, {"currency": "usd"}, {"mode": "subscription"},
            {"status": "open"}, {"client_reference_id": "999"},
            {"metadata": {"checkout_id": str(self.checkout.pk), "user_id": "999"}},
            {"id": "cs_unknown"},
        ]
        for changes in mutations:
            self.assertEqual(self.webhook(self.event({**self.session, **changes})).status_code, 400)
        for mutate in ["price", "quantity", "amount", "live", "extra", "unpaid"]:
            verified = deepcopy(self.session)
            line = verified["line_items"]["data"][0]
            if mutate == "price":
                line["price"]["id"] = "price_other"
            elif mutate == "quantity":
                line["quantity"] = 2
            elif mutate == "amount":
                line["amount_total"] = 1
            elif mutate == "live":
                verified["livemode"] = True
            elif mutate == "extra":
                verified["line_items"]["data"].append(deepcopy(line))
            else:
                verified["payment_status"] = "unpaid"
            retrieve.return_value = verified
            self.assertEqual(self.webhook(self.event()).status_code, 400)
        self.user.refresh_from_db()
        self.assertIsNone(self.user.premium_until)
        self.checkout.refresh_from_db()
        self.assertIsNone(self.checkout.paid_at)

    def test_signed_malformed_payload(self):
        for payload in [[], {}, {"livemode": False, "type": "checkout.session.completed", "data": []}]:
            self.assertEqual(self.webhook(payload).status_code, 400)

    @patch("academy.billing.stripe.checkout.Session.retrieve", side_effect=stripe.APIConnectionError("offline mock"))
    def test_provider_failure_retry_no_grant(self, retrieve):
        self.assertEqual(self.webhook(self.event()).status_code, 503)
        self.user.refresh_from_db()
        self.assertIsNone(self.user.premium_until)

    def test_account_cleanup(self):
        self.user.delete()
        self.assertFalse(PremiumCheckout.objects.exists())

    @patch("academy.billing.stripe.checkout.Session.retrieve")
    def test_return_confirmation_without_webhook_and_duplicate_delivery(self, retrieve):
        retrieve.return_value = self.session
        expiry = timezone.now() + timedelta(days=5)
        self.user.premium_until = expiry
        self.user.save()
        for _ in range(2):
            response = self.client.post("/api/billing/confirm/", {"session_id": self.checkout.session_id},
                                        format="json", HTTP_X_CSRFTOKEN=self.token)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"checkout_status": "paid"})
        retrieve.assert_called_once()
        self.assertEqual(self.webhook(self.event()).status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.premium_until, expiry + timedelta(days=30))
        self.assertEqual(len(self.client.get("/api/billing/status/").json()["transactions"]), 1)

    @patch("academy.billing.stripe.checkout.Session.retrieve")
    def test_confirmation_owner_csrf_and_paid_session_checks(self, retrieve):
        payload = {"session_id": self.checkout.session_id}
        self.assertEqual(self.client.post("/api/billing/confirm/", payload, format="json").status_code, 403)
        other = User.objects.create_user("other-confirm@example.test", "password", name="Other")
        self.client.force_login(other)
        self.client.get("/api/csrf/")
        token = self.client.cookies["csrftoken"].value
        self.assertEqual(self.client.post("/api/billing/confirm/", payload, format="json",
                                         HTTP_X_CSRFTOKEN=token).status_code, 404)
        retrieve.assert_not_called()
        self.client.force_login(self.user)
        self.client.get("/api/csrf/")
        token = self.client.cookies["csrftoken"].value
        for changes, expected in [
            ({"payment_status": "unpaid"}, 200), ({"amount_total": 1}, 400),
            ({"currency": "usd"}, 400), ({"livemode": True}, 400),
            ({"metadata": {}}, 400), ({"client_reference_id": str(other.pk)}, 400),
            ({"status": "open"}, 400),
            ({"line_items": {"has_more": False, "data": []}}, 400),
        ]:
            retrieve.return_value = {**self.session, **changes}
            response = self.client.post("/api/billing/confirm/", payload, format="json", HTTP_X_CSRFTOKEN=token)
            self.assertEqual(response.status_code, expected)
            if changes.get("payment_status") == "unpaid":
                self.assertEqual(response.json(), {"checkout_status": "pending"})
        for invalid in [None, 1, "not-a-session", "cs_" + "x" * 256]:
            self.assertEqual(self.client.post("/api/billing/confirm/", {"session_id": invalid},
                                             format="json", HTTP_X_CSRFTOKEN=token).status_code, 400)
        self.user.refresh_from_db()
        self.assertIsNone(self.user.premium_until)

    @patch("academy.billing.stripe.checkout.Session.retrieve", side_effect=stripe.APIConnectionError("offline mock"))
    def test_confirmation_provider_failure_no_access(self, retrieve):
        self.assertEqual(self.client.post("/api/billing/confirm/", {"session_id": self.checkout.session_id},
                                         format="json", HTTP_X_CSRFTOKEN=self.token).status_code, 503)
        self.checkout.refresh_from_db()
        self.assertIsNone(self.checkout.paid_at)

    @patch("academy.billing.stripe.checkout.Session.create")
    @patch("academy.billing.stripe.Price.retrieve")
    def test_exact_offer_required_and_session_return_id(self, price, create):
        offer = {"id": "price_mock", "livemode": False, "active": True,
                 "type": "one_time", "unit_amount": 499, "currency": "eur"}
        create.return_value = {"id": "cs_test_offer", "livemode": False, "url": "https://checkout.stripe.com/test"}
        for changes in [{"unit_amount": 999}, {"unit_amount": 0}, {"currency": "usd"}, {"type": "recurring"}]:
            price.return_value = {**offer, **changes}
            response = self.client.post("/api/billing/checkout/", {}, format="json", HTTP_X_CSRFTOKEN=self.token)
            self.assertEqual(response.status_code, 503)
        create.assert_not_called()
        self.user.premium_until = timezone.now() + timedelta(days=5)
        self.user.save()
        price.return_value = offer
        response = self.client.post("/api/billing/checkout/", {}, format="json", HTTP_X_CSRFTOKEN=self.token)
        self.assertEqual(response.status_code, 200)
        self.assertIn("session_id={CHECKOUT_SESSION_ID}", create.call_args.kwargs["success_url"])
        self.assertEqual(create.call_args.kwargs["automatic_tax"], {"enabled": False})

    @patch("academy.billing.stripe.checkout.Session.retrieve")
    def test_history_paid_only_owner_only_and_renewal_pending(self, retrieve):
        other = User.objects.create_user("billing-other@example.test", "password", name="Other")
        PremiumCheckout.objects.create(
            user=other, session_id="cs_other", price_id="price_mock",
            amount=499, currency="eur", paid_at=timezone.now(),
        )
        self.user.premium_until = timezone.now() + timedelta(days=10)
        self.user.save()
        pending = self.client.get("/api/billing/status/?session_id=cs_test_mock").json()
        self.assertTrue(pending["is_premium"])
        self.assertEqual(pending["checkout_status"], "pending")
        self.assertEqual(pending["transactions"], [])
        self.assertIsNone(self.client.get("/api/billing/status/?session_id=cs_other").json()["checkout_status"])
        retrieve.return_value = self.session
        self.assertEqual(self.webhook(self.event()).status_code, 200)
        data = self.client.get("/api/billing/status/?session_id=cs_test_mock").json()
        self.assertEqual(data["checkout_status"], "paid")
        self.assertEqual(len(data["transactions"]), 1)
        payment = data["transactions"][0]
        self.assertEqual(payment["amount"], 499)
        self.assertEqual(payment["currency"], "eur")
        self.assertEqual(payment["premium_until"], data["premium_until"])
        self.assertNotIn("session_id", payment)
        self.assertNotIn("event_id", payment)
        self.assertEqual(self.webhook(self.event()).status_code, 200)
        self.assertEqual(len(self.client.get("/api/billing/status/").json()["transactions"]), 1)
        self.client.logout()
        self.assertEqual(self.client.get("/api/billing/status/").status_code, 403)
