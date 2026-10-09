import re
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from google.auth.exceptions import TransportError
from rest_framework.test import APIClient

from .models import GoogleIdentity, Notification, User


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    WEB_APP_ORIGIN="http://127.0.0.1:4200",
    DEBUG=True,
    GOOGLE_CLIENT_ID="qa-client.apps.googleusercontent.com",
)
class ExtraAuthTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient(enforce_csrf_checks=True)
        self.user = User.objects.create_user("reset@example.test", "Original-test-932!", name="Student")

    def post(self, path, body, language="fr"):
        self.client.get("/api/csrf/")
        return self.client.post(path, body, format="json",
                                HTTP_X_CSRFTOKEN=self.client.cookies["csrftoken"].value,
                                HTTP_ACCEPT_LANGUAGE=language)

    def request_reset(self, email=None):
        return self.post("/api/auth/password-reset/", {"email": email or self.user.email})

    def reset_data(self):
        self.assertEqual(self.request_reset().status_code, 200)
        link = re.search(r"/reset-password/([^/]+)/(\S+)", mail.outbox[-1].body)
        return {"uid": link[1], "token": link[2], "password": "Changed-passphrase-932!"}

    def test_reset_email_generic_response_single_use_password_and_session_invalidation(self):
        self.client.force_login(self.user)
        data = self.reset_data()
        self.assertIn("une heure", mail.outbox[-1].body)
        self.assertEqual(mail.outbox[-1].to, [self.user.email])
        response = self.post("/api/auth/password-reset/confirm/", data)
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(data["password"]))
        self.assertEqual(self.client.get("/api/me/").status_code, 403)
        self.assertEqual(self.post("/api/auth/password-reset/confirm/", data).status_code, 400)

    def test_unknown_inactive_and_google_only_have_identical_response_and_no_email(self):
        expected = self.request_reset().json()
        count = len(mail.outbox)
        for email, active, usable in [("absent@example.test", True, True), ("inactive@example.test", False, True), ("google@example.test", True, False)]:
            if email != "absent@example.test":
                User.objects.create_user(email, "Original-test-932!" if usable else None, name="QA", is_active=active)
            response = self.request_reset(email)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), expected)
        self.assertEqual(len(mail.outbox), count)

    def test_reset_rejects_invalid_expired_weak_and_unexpected_fields(self):
        data = self.reset_data()
        for overrides in [{"uid": "%%%bad"}, {"token": "bad"}, {"password": "123"}, {"is_staff": True}]:
            self.assertEqual(self.post("/api/auth/password-reset/confirm/", {**data, **overrides}).status_code, 400)
        with patch.object(default_token_generator, "_now", return_value=default_token_generator._now() + timedelta(hours=2)):
            self.assertEqual(self.post("/api/auth/password-reset/confirm/", data).status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Original-test-932!"))

    def test_reset_csrf_throttle_and_delivery_failure(self):
        self.assertEqual(self.client.post("/api/auth/password-reset/", {"email": self.user.email}, format="json").status_code, 403)
        with patch("academy.auth_extra.send_mail", side_effect=OSError("offline")):
            self.assertEqual(self.request_reset().status_code, 503)
        for _ in range(4):
            self.assertEqual(self.request_reset("absent@example.test").status_code, 200)
        self.assertEqual(self.request_reset().status_code, 429)

    def google_claims(self, **overrides):
        config = self.client.get("/api/auth/google/config/").json()
        return {**{"sub": "qa-google-subject", "email": "google-new@example.test", "email_verified": True,
                   "aud": "qa-client.apps.googleusercontent.com", "iss": "https://accounts.google.com",
                   "nonce": config["nonce"], "name": "Google Student"}, **overrides}

    def google_post(self, claims):
        with patch("academy.auth_extra.id_token.verify_oauth2_token", return_value=claims) as verify:
            response = self.post("/api/auth/google/", {"credential": "signed-test-token"})
            verify.assert_called_once()
            self.assertEqual(verify.call_args.args[2], "qa-client.apps.googleusercontent.com")
            return response

    def test_google_verified_registration_repeat_login_and_welcome_once(self):
        claims = self.google_claims()
        response = self.google_post(claims)
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(email=claims["email"])
        self.assertFalse(user.has_usable_password())
        self.assertFalse(user.is_staff)
        self.assertEqual(self.client.get("/api/me/").json()["id"], user.pk)
        self.assertEqual(Notification.objects.filter(user=user).count(), 1)
        self.assertEqual(GoogleIdentity.objects.get(user=user).subject, claims["sub"])
        self.assertEqual(self.google_post(self.google_claims()).status_code, 200)
        self.assertEqual(GoogleIdentity.objects.count(), 1)
        self.assertEqual(Notification.objects.filter(user=user).count(), 1)

    def test_google_rejects_bad_claims_nonce_replay_existing_email_and_inactive_user(self):
        for overrides in [{"email_verified": False}, {"nonce": "wrong"}, {"aud": "wrong"}, {"iss": "evil"}, {"sub": ""}]:
            with self.subTest(overrides=overrides):
                self.assertEqual(self.google_post(self.google_claims(**overrides)).status_code, 400)
        self.assertEqual(self.google_post(self.google_claims(email=self.user.email)).status_code, 409)
        self.assertFalse(GoogleIdentity.objects.exists())
        claims = self.google_claims()
        self.assertEqual(self.google_post(claims).status_code, 200)
        # The consumed nonce rejects replay before any provider call.
        self.assertEqual(self.post("/api/auth/google/", {"credential": "signed-test-token"}).status_code, 400)
        user = User.objects.get(email=claims["email"])
        user.is_active = False
        user.save(update_fields=["is_active"])
        self.assertEqual(self.google_post(self.google_claims()).status_code, 403)

    def test_google_provider_failure_configuration_and_csrf(self):
        self.google_claims()
        for error, code in [(ValueError("bad signature"), 400), (TransportError("offline"), 503)]:
            with patch("academy.auth_extra.id_token.verify_oauth2_token", side_effect=error):
                self.assertEqual(self.post("/api/auth/google/", {"credential": "test"}).status_code, code)
        self.assertEqual(self.client.post("/api/auth/google/", {"credential": "test"}, format="json").status_code, 403)
        with override_settings(GOOGLE_CLIENT_ID=""):
            self.assertFalse(self.client.get("/api/auth/google/config/").json()["configured"])
            self.assertEqual(self.post("/api/auth/google/", {"credential": "test"}).status_code, 503)

    def test_confirm_requires_csrf_and_google_nonce_expires(self):
        data = self.reset_data()
        self.assertEqual(self.client.post("/api/auth/password-reset/confirm/", data, format="json").status_code, 403)
        self.google_claims()
        session = self.client.session
        session["google_nonce_at"] = (timezone.now() - timedelta(minutes=11)).timestamp()
        session.save()
        with patch("academy.auth_extra.id_token.verify_oauth2_token") as verify:
            self.assertEqual(self.post("/api/auth/google/", {"credential": "test"}).status_code, 400)
            verify.assert_not_called()

    def test_email_origin_and_missing_smtp_configuration_fail_explicitly(self):
        for origin in ["http://[bad", "https://example.test/untrusted/path", "http://example.test"]:
            with override_settings(WEB_APP_ORIGIN=origin):
                self.assertEqual(self.request_reset().status_code, 503)
        with override_settings(EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend", EMAIL_HOST=""):
            self.assertEqual(self.request_reset().status_code, 503)
