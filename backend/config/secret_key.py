import os
import secrets
import uuid
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured


def resolve_secret_key(base_dir, *, debug, environment_key):
    if environment_key:
        return environment_key
    if not debug:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY is required outside development.")

    secret_path = Path(base_dir) / ".dev-secret-key"
    if not secret_path.exists():
        candidate = secret_path.with_name(f".dev-secret-key.{uuid.uuid4().hex}")
        try:
            descriptor = os.open(candidate, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(secrets.token_urlsafe(64))
            try:
                # Publish a complete file without overwriting another process's key.
                os.link(candidate, secret_path)
            except FileExistsError:
                pass
        finally:
            candidate.unlink(missing_ok=True)
    key = secret_path.read_text(encoding="utf-8").strip()
    if len(key) < 50:
        raise ImproperlyConfigured(
            "The local .dev-secret-key is invalid. Set DJANGO_SECRET_KEY or remove "
            "the invalid development key file (this signs out existing sessions)."
        )
    return key
