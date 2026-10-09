import base64

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Generate a VAPID key pair. Keep the private key in your local environment, never source control."

    def handle(self, *args, **options):
        key = ec.generate_private_key(ec.SECP256R1())
        public = key.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
        private = key.private_numbers().private_value.to_bytes(32, "big")
        for name, value in [("VAPID_PUBLIC_KEY", public), ("VAPID_PRIVATE_KEY", private)]:
            encoded = base64.urlsafe_b64encode(value).decode().rstrip("=")
            self.stdout.write(f'{name}={encoded}')
