import subprocess
import sys
import uuid
from pathlib import Path

from django.conf import settings
from django.contrib.sessions.backends.db import SessionStore
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings

from .secret_key import resolve_secret_key


class SecretKeyTests(TestCase):
    def setUp(self):
        self.directory = Path(settings.BASE_DIR) / f".test-secret-{uuid.uuid4().hex}"
        self.directory.mkdir()
        self.addCleanup(self.remove_directory)

    def remove_directory(self):
        for path in self.directory.iterdir():
            path.unlink()
        self.directory.rmdir()

    def resolve(self, *, debug=True, environment_key=None):
        return resolve_secret_key(self.directory, debug=debug, environment_key=environment_key)

    def test_new_process_reads_same_development_key(self):
        key = self.resolve()
        self.assertGreaterEqual(len(key), 50)
        script = (
            "import sys; from config.secret_key import resolve_secret_key; "
            "assert resolve_secret_key(sys.argv[1], debug=True, environment_key=None) == sys.argv[2]"
        )
        subprocess.run(
            [sys.executable, "-c", script, str(self.directory), key],
            cwd=settings.BASE_DIR, check=True, capture_output=True, text=True,
        )
        self.assertEqual([path.name for path in self.directory.iterdir()], [".dev-secret-key"])

    def test_database_session_decodes_after_key_reload(self):
        with override_settings(SECRET_KEY=self.resolve()):
            session = SessionStore()
            session["_auth_user_id"] = "123"
            session.save()
            session_key = session.session_key
        with override_settings(SECRET_KEY=self.resolve()):
            reloaded = SessionStore(session_key=session_key)
            self.assertEqual(reloaded["_auth_user_id"], "123")

    def test_production_requires_environment_even_with_local_file(self):
        for create_file in [False, True]:
            if create_file:
                self.resolve()
            with self.assertRaisesMessage(ImproperlyConfigured, "required outside development"):
                self.resolve(debug=False)
            with self.assertRaises(ImproperlyConfigured):
                self.resolve(debug=False, environment_key="")
        self.assertEqual(self.resolve(debug=False, environment_key="explicit-environment-key"), "explicit-environment-key")

    def test_environment_key_precedence_without_local_file_access(self):
        self.assertEqual(self.resolve(environment_key="environment-key"), "environment-key")
        self.assertFalse((self.directory / ".dev-secret-key").exists())
        (self.directory / ".dev-secret-key").write_text("invalid", encoding="utf-8")
        self.assertEqual(self.resolve(environment_key="environment-key"), "environment-key")

    def test_invalid_file_does_not_silently_rotate(self):
        path = self.directory / ".dev-secret-key"
        path.write_text("invalid", encoding="utf-8")
        with self.assertRaisesMessage(ImproperlyConfigured, "local .dev-secret-key is invalid"):
            self.resolve()
        self.assertEqual(path.read_text(encoding="utf-8"), "invalid")
