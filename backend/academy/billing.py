import logging
from datetime import timedelta
from urllib.parse import urlsplit

import stripe
from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PremiumCheckout, User
from .access import premium_active

logger = logging.getLogger(__name__)
PREMIUM_AMOUNT = 499
PREMIUM_CURRENCY = "eur"
PREMIUM_DAYS = 30


def web_origin():
    value = settings.WEB_APP_ORIGIN
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return None
    if (parsed.scheme not in ("http", "https") or not parsed.hostname
            or parsed.username or parsed.password or parsed.path not in ("", "/")
            or parsed.query or parsed.fragment or "\\" in value
            or any(char.isspace() for char in value)
            or (parsed.scheme == "http" and parsed.hostname not in ("localhost", "127.0.0.1"))
            or (port is not None and not 1 <= port <= 65535)):
        return None
    return value.rstrip("/")


def configured():
    return bool(settings.STRIPE_SECRET_KEY.startswith("sk_test_")
                and settings.STRIPE_WEBHOOK_SECRET.startswith("whsec_")
                and settings.STRIPE_PRICE_ID.startswith("price_") and web_origin())


class BillingStatusView(APIView):
    def get(self, request):
        expiry = request.user.premium_until
        session_id = request.query_params.get("session_id")
        checkout = PremiumCheckout.objects.filter(user=request.user, session_id=session_id).first() if session_id else None
        return Response({
            "configured": configured(),
            "premium_until": expiry.isoformat() if expiry else None,
            "is_premium": premium_active(request.user),
            "amount": PREMIUM_AMOUNT, "currency": PREMIUM_CURRENCY, "duration_days": PREMIUM_DAYS,
            "checkout_status": ("paid" if checkout.paid_at else "pending") if checkout else None,
            "transactions": [
                {
                    "id": purchase.pk, "amount": purchase.amount, "currency": purchase.currency,
                    "created_at": purchase.created_at.isoformat(), "paid_at": purchase.paid_at.isoformat(),
                    "premium_until": purchase.premium_until.isoformat() if purchase.premium_until else None,
                }
                for purchase in PremiumCheckout.objects.filter(user=request.user, paid_at__isnull=False).order_by("-paid_at", "-pk")
            ],
        })


class CheckoutView(APIView):
    def post(self, request):
        if not configured():
            return Response({"detail": "Stripe test billing is not configured."}, status=503)
        try:
            price = stripe.Price.retrieve(settings.STRIPE_PRICE_ID, api_key=settings.STRIPE_SECRET_KEY)
            if (price.get("livemode") is not False or price.get("active") is not True
                    or price.get("type") != "one_time"
                    or type(price.get("unit_amount")) is not int or price["unit_amount"] != PREMIUM_AMOUNT
                    or price.get("currency") != PREMIUM_CURRENCY
                    or price.get("id") != settings.STRIPE_PRICE_ID):
                return Response({"detail": "Configure an active one-time Stripe test price of EUR 4.99."}, status=503)
            checkout = PremiumCheckout.objects.create(
                user=request.user, price_id=price["id"],
                amount=price["unit_amount"], currency=price["currency"],
            )
            origin = web_origin()
            session = stripe.checkout.Session.create(
                api_key=settings.STRIPE_SECRET_KEY, mode="payment",
                line_items=[{"price": checkout.price_id, "quantity": 1}],
                client_reference_id=str(request.user.pk),
                metadata={"checkout_id": str(checkout.pk), "user_id": str(request.user.pk)},
                success_url=f"{origin}/premium?checkout=success&session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{origin}/premium?checkout=cancelled",
                allow_promotion_codes=False,
                automatic_tax={"enabled": False},
                idempotency_key=f"premium-checkout-{checkout.pk}",
            )
            if session.get("livemode") is not False or not session.get("url"):
                logger.error("Stripe returned an invalid test checkout for checkout %s", checkout.pk)
                return Response({"detail": "Stripe test checkout unavailable."}, status=502)
            checkout.session_id = session["id"]
            checkout.save(update_fields=["session_id"])
            return Response({"url": session["url"]})
        except stripe.StripeError:
            logger.exception("Stripe test checkout provider failure")
            return Response({"detail": "Stripe test checkout unavailable."}, status=502)


def session_matches(session, checkout):
    lines = session.get("line_items", {})
    metadata = session.get("metadata", {})
    if not isinstance(lines, dict) or not isinstance(metadata, dict):
        return False
    items = lines.get("data", [])
    if (not isinstance(items, list) or len(items) != 1 or not isinstance(items[0], dict)
            or not isinstance(items[0].get("price"), dict)):
        return False
    return (
        session.get("id") == checkout.session_id
        and session.get("livemode") is False
        and session.get("mode") == "payment"
        and session.get("status") == "complete"
        and session.get("payment_status") == "paid"
        and type(session.get("amount_total")) is int
        and session.get("amount_total") == checkout.amount
        and session.get("currency") == checkout.currency
        and session.get("client_reference_id") == str(checkout.user_id)
        and metadata.get("checkout_id") == str(checkout.pk)
        and metadata.get("user_id") == str(checkout.user_id)
        and not lines.get("has_more")
        and items[0].get("quantity") == 1
        and items[0].get("price", {}).get("id") == checkout.price_id
        and items[0].get("price", {}).get("livemode") is False
        and items[0].get("amount_total") == checkout.amount
        and items[0].get("currency") == checkout.currency
    )


def grant_checkout(checkout, event_id=None):
    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=checkout.user_id)
        now = timezone.now()
        premium_until = max(now, user.premium_until or now) + timedelta(days=PREMIUM_DAYS)
        if not PremiumCheckout.objects.filter(pk=checkout.pk, paid_at__isnull=True).update(
            paid_at=now, event_id=event_id, premium_until=premium_until
        ):
            return
        user.premium_until = premium_until
        user.save(update_fields=["premium_until"])


class ConfirmCheckoutView(APIView):
    def post(self, request):
        session_id = request.data.get("session_id")
        if not isinstance(session_id, str) or not session_id.startswith("cs_") or len(session_id) > 255:
            return Response({"detail": "Invalid checkout session."}, status=400)
        checkout = PremiumCheckout.objects.filter(user=request.user, session_id=session_id).first()
        if not checkout:
            return Response({"detail": "Unknown checkout."}, status=404)
        if checkout.paid_at:
            return Response({"checkout_status": "paid"})
        if not configured():
            return Response({"detail": "Stripe test billing is not configured."}, status=503)
        try:
            verified = stripe.checkout.Session.retrieve(
                checkout.session_id, api_key=settings.STRIPE_SECRET_KEY, expand=["line_items.data.price"]
            )
        except stripe.StripeError:
            logger.exception("Stripe return confirmation provider failure")
            return Response({"detail": "Stripe verification unavailable; retry."}, status=503)
        if verified.get("livemode") is not False:
            return Response({"detail": "Live payments are forbidden."}, status=400)
        if verified.get("payment_status") != "paid":
            return Response({"checkout_status": "pending"})
        if not session_matches(verified, checkout):
            return Response({"detail": "Checkout does not match the persisted test purchase."}, status=400)
        grant_checkout(checkout)
        return Response({"checkout_status": "paid"})


@csrf_exempt
@require_POST
def webhook(request):
    if not configured():
        return JsonResponse({"detail": "Stripe test billing is not configured."}, status=503)
    try:
        event = stripe.Webhook.construct_event(
            request.body, request.headers.get("Stripe-Signature", ""), settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, TypeError, AttributeError, stripe.SignatureVerificationError):
        return JsonResponse({"detail": "Invalid Stripe signature or payload."}, status=400)
    if not isinstance(event, dict):
        return JsonResponse({"detail": "Invalid Stripe event."}, status=400)
    if event.get("livemode") is not False:
        return JsonResponse({"detail": "Live payments are forbidden."}, status=400)
    if event.get("type") not in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
        return JsonResponse({"received": True})
    data = event.get("data")
    session = data.get("object") if isinstance(data, dict) else None
    if not isinstance(session, dict):
        return JsonResponse({"detail": "Invalid checkout event."}, status=400)
    if session.get("livemode") is not False:
        return JsonResponse({"detail": "Live payments are forbidden."}, status=400)
    if session.get("payment_status") != "paid":
        return JsonResponse({"received": True})
    if (not isinstance(session.get("id"), str) or not session["id"].startswith("cs_")
            or len(session["id"]) > 255):
        return JsonResponse({"detail": "Invalid checkout session."}, status=400)
    checkout = PremiumCheckout.objects.filter(session_id=session.get("id")).first()
    if (not checkout or not isinstance(event.get("id"), str) or not event["id"]
            or len(event["id"]) > 255):
        return JsonResponse({"detail": "Unknown checkout."}, status=400)
    if checkout.paid_at:
        return JsonResponse({"received": True})
    try:
        verified = stripe.checkout.Session.retrieve(
            checkout.session_id, api_key=settings.STRIPE_SECRET_KEY, expand=["line_items.data.price"]
        )
    except stripe.StripeError:
        logger.exception("Stripe webhook verification provider failure")
        return JsonResponse({"detail": "Stripe verification unavailable; retry."}, status=503)
    # Both signed event and server-retrieved session must identify the paid purchase.
    signed = dict(session)
    signed["line_items"] = verified.get("line_items", {})
    if not session_matches(signed, checkout) or not session_matches(verified, checkout):
        return JsonResponse({"detail": "Checkout does not match the persisted test purchase."}, status=400)
    grant_checkout(checkout, event["id"])
    return JsonResponse({"received": True})
