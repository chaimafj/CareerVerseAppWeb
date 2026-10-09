from django.utils import timezone
from rest_framework.exceptions import PermissionDenied


def premium_active(user):
    return bool(user.is_authenticated and user.premium_until and user.premium_until > timezone.now())


def require_lab_access(user, lab):
    if lab.is_premium and not premium_active(user):
        raise PermissionDenied({
            "detail": "Active Premium access is required for this lab and its course.",
            "code": "premium_required",
        })
