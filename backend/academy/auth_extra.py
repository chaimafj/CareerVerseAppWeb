import logging
import secrets
import smtplib
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.csrf import csrf_protect
from google.auth.exceptions import GoogleAuthError, TransportError
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from .models import GoogleIdentity, User
from .push import welcome_once
from .serializers import ProfileSerializer, StrictSerializer
from .views import welcome_language

logger = logging.getLogger(__name__)


class ResetThrottle(SimpleRateThrottle):
    scope = "password_reset"
    rate = "5/hour"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class ConfirmThrottle(ResetThrottle):
    scope = "password_reset_confirm"
    rate = "20/hour"


class GoogleThrottle(ResetThrottle):
    scope = "google_auth"
    rate = "30/hour"


class ResetRequestSerializer(StrictSerializer):
    email = serializers.EmailField(max_length=254)


class ResetConfirmSerializer(StrictSerializer):
    uid = serializers.CharField(max_length=100)
    token = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)


class GoogleSerializer(StrictSerializer):
    credential = serializers.CharField(max_length=10000, trim_whitespace=False)


RESET_MAIL = {
    "en": ("Reset your CareerVerse password", "Use this link to choose a new password. It expires in one hour and can only be used once. If you did not request this, ignore this email."),
    "fr": ("Réinitialiser votre mot de passe CareerVerse", "Utilisez ce lien pour choisir un nouveau mot de passe. Il expire dans une heure et ne peut être utilisé qu'une seule fois. Si vous n'avez pas fait cette demande, ignorez cet e-mail."),
    "ar": ("إعادة تعيين كلمة مرور CareerVerse", "استخدم هذا الرابط لاختيار كلمة مرور جديدة. تنتهي صلاحيته خلال ساعة ويمكن استخدامه مرة واحدة فقط. إذا لم تطلب ذلك، تجاهل هذه الرسالة."),
}


@method_decorator(csrf_protect, name="dispatch")
class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ResetThrottle]

    def post(self, request):
        serializer = ResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        origin = settings.WEB_APP_ORIGIN.rstrip("/")
        try:
            parsed = urlsplit(origin)
        except ValueError:
            logger.error("Password reset WEB_APP_ORIGIN is invalid.")
            return Response({"detail": "Password reset email delivery is not configured."}, status=503)
        valid_origin = (parsed.scheme == "https" or (
            settings.DEBUG and parsed.scheme == "http" and parsed.hostname in ("localhost", "127.0.0.1")
        )) and parsed.hostname and not parsed.username and not parsed.password and parsed.path in ("", "/") and not parsed.query and not parsed.fragment
        if not valid_origin or (settings.EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend" and not settings.EMAIL_HOST):
            logger.error("Password reset email/origin settings are not configured.")
            return Response({"detail": "Password reset email delivery is not configured."}, status=503)
        user = User.objects.filter(email__iexact=serializer.validated_data["email"], is_active=True).first()
        if user and user.has_usable_password():
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            subject, message = RESET_MAIL[welcome_language(request)]
            link = f"{origin}/reset-password/{uid}/{token}"
            try:
                sent = send_mail(subject, f"{message}\n\n{link}", settings.DEFAULT_FROM_EMAIL, [user.email])
            except (smtplib.SMTPException, OSError):
                logger.error("Password reset email delivery failed.")
                return Response({"detail": "Unable to send reset email. Please retry later."}, status=503)
            if sent != 1:
                logger.error("Password reset email backend did not accept the message.")
                return Response({"detail": "Unable to send reset email. Please retry later."}, status=503)
        return Response({"detail": "If an eligible account exists, a reset link has been sent."})


@method_decorator(csrf_protect, name="dispatch")
class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ConfirmThrottle]

    def post(self, request):
        serializer = ResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            uid = urlsafe_base64_decode(data["uid"]).decode()
            if not uid.isdecimal() or len(uid) > 20:
                raise ValueError("Invalid UID.")
        except (ValueError, UnicodeDecodeError, OverflowError):
            return Response({"detail": "This reset link is invalid or expired. Request a new one."}, status=400)
        with transaction.atomic():
            user = User.objects.select_for_update().filter(pk=uid, is_active=True).first()
            if not user or not user.has_usable_password() or not default_token_generator.check_token(user, data["token"]):
                return Response({"detail": "This reset link is invalid or expired. Request a new one."}, status=400)
            try:
                validate_password(data["password"], user)
            except DjangoValidationError as error:
                raise serializers.ValidationError({"password": error.messages}) from error
            user.set_password(data["password"])
            user.save(update_fields=["password"])
        return Response({"detail": "Password reset successfully. Sign in with your new password."})


class GoogleConfigView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        nonce = secrets.token_urlsafe(32)
        request.session["google_nonce"] = nonce
        request.session["google_nonce_at"] = timezone.now().timestamp()
        return Response({"configured": bool(settings.GOOGLE_CLIENT_ID), "client_id": settings.GOOGLE_CLIENT_ID,
                         "nonce": nonce if settings.GOOGLE_CLIENT_ID else ""}, headers={"Cache-Control": "no-store"})


@method_decorator(csrf_protect, name="dispatch")
class GoogleLoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [GoogleThrottle]

    def post(self, request):
        if not settings.GOOGLE_CLIENT_ID:
            return Response({"detail": "Google sign-in is not configured yet."}, status=503)
        serializer = GoogleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        nonce = request.session.get("google_nonce")
        nonce_at = request.session.get("google_nonce_at", 0)
        if not nonce or timezone.now().timestamp() - nonce_at > 600:
            return Response({"detail": "Google sign-in expired. Reload the page and retry."}, status=400)
        try:
            claims = id_token.verify_oauth2_token(
                serializer.validated_data["credential"], GoogleRequest(), settings.GOOGLE_CLIENT_ID
            )
        except TransportError:
            logger.error("Google token verification service is unreachable.")
            return Response({"detail": "Google verification is unavailable. Please retry."}, status=503)
        except (ValueError, GoogleAuthError):
            return Response({"detail": "Google could not verify your sign-in. Please retry."}, status=400)
        if (claims.get("iss") not in ("accounts.google.com", "https://accounts.google.com")
                or claims.get("aud") != settings.GOOGLE_CLIENT_ID
                or claims.get("email_verified") is not True
                or not isinstance(claims.get("nonce"), str)
                or not claims["nonce"].isascii()
                or not secrets.compare_digest(claims["nonce"], nonce)):
            return Response({"detail": "Google could not verify your sign-in. Please retry."}, status=400)
        email = serializers.EmailField(max_length=254).run_validation(claims.get("email"))
        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject or len(subject) > 255:
            return Response({"detail": "Google could not verify your sign-in. Please retry."}, status=400)
        try:
            with transaction.atomic():
                identity = GoogleIdentity.objects.select_related("user").filter(subject=subject).first()
                if identity:
                    user = identity.user
                    if not user.is_active:
                        return Response({"detail": "This account is inactive."}, status=403)
                else:
                    if User.objects.filter(email__iexact=email).exists():
                        return Response({"detail": "An account already uses this email. Sign in with your password; Google accounts are not linked automatically."}, status=409)
                    name = claims.get("name")
                    user = User.objects.create_user(
                        email=email, name=name.strip()[:150] if isinstance(name, str) and name.strip() else email.split("@")[0]
                    )
                    GoogleIdentity.objects.create(user=user, subject=subject)
                welcome_once(user, welcome_language(request))
        except IntegrityError:
            if GoogleIdentity.objects.filter(subject=subject).exists() or User.objects.filter(email__iexact=email).exists():
                return Response({"detail": "This sign-in conflicts with an existing account. Reload and retry."}, status=409)
            raise
        request.session.pop("google_nonce", None)
        request.session.pop("google_nonce_at", None)
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return Response(ProfileSerializer(user).data)
