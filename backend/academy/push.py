import base64
import binascii
import json
import logging
import re
from datetime import timedelta
from urllib.parse import urlsplit

import requests
from cryptography.hazmat.primitives.asymmetric import ec
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from pywebpush import WebPushException, webpush
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification, PushDelivery, PushSubscription, User

logger = logging.getLogger(__name__)
PUSH_HOSTS = {"fcm.googleapis.com", "updates.push.services.mozilla.com", "web.push.apple.com"}
MESSAGES = {
    "welcome": {
        "en": ("Welcome to CareerVerse!", "Discover careers, explore courses and try your first lab. Your future starts here!"),
        "fr": ("Bienvenue sur CareerVerse !", "Découvrez les métiers, explorez les cours et essayez votre premier lab. Votre avenir commence ici !"),
        "ar": ("مرحباً بك في CareerVerse!", "اكتشف المهن واستكشف الدورات وجرّب مختبرك الأول. مستقبلك يبدأ هنا!"),
    },
    "lab": {
        "en": ("Lab completed", "Your lab result is ready. Open CareerVerse to view it."),
        "fr": ("Lab terminé", "Votre résultat est prêt. Ouvrez CareerVerse pour le consulter."),
        "ar": ("اكتمل المختبر", "نتيجة المختبر جاهزة. افتح CareerVerse لعرضها."),
    },
    "test": {
        "en": ("CareerVerse notifications", "Web Push is connected to CareerVerse."),
        "fr": ("Notifications CareerVerse", "Web Push est connecté à CareerVerse."),
        "ar": ("إشعارات CareerVerse", "تم ربط إشعارات الويب بـ CareerVerse."),
    },
}


def decode_key(value, size):
    if not isinstance(value, str) or not value or len(value) > 100:
        raise ValueError("Invalid key.")
    if any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for c in value):
        raise ValueError("Invalid base64url key.")
    decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    if len(decoded) != size:
        raise ValueError("Invalid key length.")
    return decoded


def configured():
    try:
        public = decode_key(settings.VAPID_PUBLIC_KEY, 65)
        private = decode_key(settings.VAPID_PRIVATE_KEY, 32)
        key = ec.derive_private_key(int.from_bytes(private, "big"), ec.SECP256R1())
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        if key.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint) != public:
            return False
        subject = urlsplit(settings.VAPID_SUBJECT)
        return bool((subject.scheme == "mailto" and "@" in subject.path)
                    or (subject.scheme == "https" and subject.hostname))
    except (ValueError, binascii.Error):
        return False


def validate_endpoint(value):
    if not isinstance(value, str) or not value or len(value) > 2048:
        raise ValidationError({"endpoint": "Use a valid HTTPS push endpoint."})
    try:
        parsed = urlsplit(value)
        host = parsed.hostname or ""
        supported_host = host in PUSH_HOSTS or bool(
            re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*\.notify\.windows\.com", host)
        )
        valid = (parsed.scheme == "https" and supported_host
                 and parsed.port in (None, 443) and not parsed.username and not parsed.password
                 and not parsed.fragment and parsed.path.startswith("/") and parsed.path != "/"
                 and "\\" not in value and not any(c.isspace() for c in value))
    except ValueError:
        valid = False
    if not valid:
        raise ValidationError({"endpoint": "Only supported public HTTPS push service origins are allowed."})
    return value


def notification_data(notification):
    return {
        "id": notification.pk, "title": notification.title, "body": notification.body,
        "path": notification.path, "read": notification.read,
        "created_at": notification.created_at.isoformat(),
    }


def enqueue_notification(user, kind, path, language=None):
    with transaction.atomic():
        subscriptions = list(PushSubscription.objects.filter(user=user).order_by("-id"))
        language = language or (subscriptions[0].language if subscriptions else "en")
        title, body = MESSAGES[kind][language]
        notification = Notification.objects.create(user=user, title=title, body=body, path=path)
        PushDelivery.objects.bulk_create([
            PushDelivery(
                notification=notification, subscription=subscription,
                title=MESSAGES[kind][subscription.language][0],
                body=MESSAGES[kind][subscription.language][1], next_attempt_at=timezone.now(),
            ) for subscription in subscriptions
        ])
        return notification


def welcome_once(user, language):
    with transaction.atomic():
        claimed = User.objects.filter(pk=user.pk, welcome_notified=False).update(welcome_notified=True)
        if claimed:
            enqueue_notification(user, "welcome", "/careers", language=language)


class PushConfigView(APIView):
    def get(self, request):
        enabled = configured()
        return Response({"configured": enabled, "public_key": settings.VAPID_PUBLIC_KEY if enabled else ""})


class SubscriptionView(APIView):
    def post(self, request):
        if not configured():
            return Response({"detail": "Web Push is not configured."}, status=503)
        if not isinstance(request.data, dict):
            raise ValidationError({"detail": "Use a subscription JSON object."})
        endpoint = validate_endpoint(request.data.get("endpoint"))
        keys = request.data.get("keys")
        language = request.data.get("language")
        if not isinstance(keys, dict) or set(keys) != {"p256dh", "auth"} or language not in ("en", "fr", "ar"):
            raise ValidationError({"detail": "Provide p256dh/auth keys and an en, fr or ar language."})
        try:
            point = decode_key(keys["p256dh"], 65)
            ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), point)
            decode_key(keys["auth"], 16)
        except (ValueError, binascii.Error):
            raise ValidationError({"keys": "Invalid Web Push subscription keys."})
        with transaction.atomic():
            subscription, created = PushSubscription.objects.get_or_create(
                endpoint=endpoint, defaults={"user": request.user, **keys, "language": language}
            )
            if subscription.user_id != request.user.pk:
                # Do not transfer endpoints between users or disclose the owner's identity.
                return Response({"detail": "Endpoint unavailable. Unsubscribe and create a new subscription."}, status=409)
            subscription.p256dh, subscription.auth = keys["p256dh"], keys["auth"]
            subscription.language = language
            subscription.save(update_fields=["p256dh", "auth", "language"])
        return Response({"endpoint": endpoint, "keys": keys, "language": language}, status=201 if created else 200)

    def delete(self, request):
        if not isinstance(request.data, dict):
            raise ValidationError({"detail": "Use an endpoint JSON object."})
        endpoint = validate_endpoint(request.data.get("endpoint"))
        PushSubscription.objects.filter(user=request.user, endpoint=endpoint).delete()
        return Response(status=204)


class NotificationListView(APIView):
    def get(self, request):
        return Response([notification_data(n) for n in Notification.objects.filter(user=request.user)[:50]])

    def delete(self, request):
        Notification.objects.filter(user=request.user).delete()
        return Response(status=204)


class NotificationReadView(APIView):
    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        notification.read = True
        notification.save(update_fields=["read"])
        return Response(notification_data(notification))


class PushTestView(APIView):
    def post(self, request):
        if not configured():
            return Response({"detail": "Web Push is not configured."}, status=503)
        if not PushSubscription.objects.filter(user=request.user).exists():
            return Response({"detail": "Subscribe this browser before testing Web Push."}, status=400)
        return Response(notification_data(enqueue_notification(request.user, "test", "/notifications")), status=201)


class NoRedirectSession(requests.Session):
    def request(self, method, url, **kwargs):
        kwargs["allow_redirects"] = False
        return super().request(method, url, **kwargs)


def send_pending(limit=100):
    if not configured():
        raise ValueError("Web Push is not configured; set matching VAPID keys and VAPID_SUBJECT.")
    now = timezone.now()
    exhausted = PushDelivery.objects.filter(
        sent_at__isnull=True, failed=False, attempts__gte=5, next_attempt_at__lte=now,
    ).update(failed=True, last_error="Retry budget exhausted after worker interruption")
    if exhausted:
        logger.error("%s push deliveries exhausted their retry budget", exhausted)
    ids = list(PushDelivery.objects.filter(
        sent_at__isnull=True, failed=False, attempts__lt=5, next_attempt_at__lte=now
    ).order_by("id").values_list("id", flat=True)[:limit])
    sent = 0
    for pk in ids:
        with transaction.atomic():
            delivery = PushDelivery.objects.select_related("subscription", "notification").filter(pk=pk).first()
            if delivery is None:
                continue
            claimed = PushDelivery.objects.filter(
                pk=pk, sent_at__isnull=True, failed=False, next_attempt_at__lte=now,
                attempts=delivery.attempts,
            ).update(attempts=delivery.attempts + 1, next_attempt_at=now + timedelta(minutes=5))
            if not claimed:
                continue
        subscription = delivery.subscription
        try:
            validate_endpoint(subscription.endpoint)
            with NoRedirectSession() as session:
                webpush(
                    subscription_info={"endpoint": subscription.endpoint,
                                       "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth}},
                    data=json.dumps({"tag": f"notification-{delivery.notification_id}", "title": delivery.title,
                                     "body": delivery.body, "path": delivery.notification.path}),
                    vapid_private_key=settings.VAPID_PRIVATE_KEY,
                    vapid_claims={"sub": settings.VAPID_SUBJECT},
                    requests_session=session, timeout=20, ttl=3600,
                )
        except (WebPushException, requests.RequestException, ValueError, ValidationError) as exc:
            response = getattr(exc, "response", None)
            code = response.status_code if response is not None else None
            # Never log endpoint tokens, encryption keys, or provider response bodies.
            error = f"{type(exc).__name__}; HTTP {code}" if code else type(exc).__name__
            logger.error("Push delivery %s failed: %s", pk, error)
            if code in (404, 410):
                PushSubscription.objects.filter(pk=subscription.pk).delete()
                continue
            attempts = delivery.attempts + 1
            PushDelivery.objects.filter(pk=pk).update(
                failed=attempts >= 5, last_error=error,
                next_attempt_at=timezone.now() + timedelta(seconds=min(3600, 60 * 2 ** attempts)),
            )
        else:
            PushDelivery.objects.filter(pk=pk).update(sent_at=timezone.now(), last_error="")
            sent += 1
    return sent
