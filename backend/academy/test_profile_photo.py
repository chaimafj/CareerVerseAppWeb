from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from .models import User


def photo(format="PNG", size=(1000, 600)):
    output = BytesIO()
    Image.new("RGB", size, "blue").save(output, format=format)
    return SimpleUploadedFile("photo.png", output.getvalue(), content_type="image/png")


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ProfilePhotoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("photo@example.test", "Test-only-932!", name="Student")
        self.other = User.objects.create_user("other-photo@example.test", "Test-only-932!", name="Other")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_upload_reencode_private_read_replace_remove(self):
        response = self.client.post("/api/me/photo/", {"photo": photo()}, format="multipart")
        self.assertEqual(response.status_code, 200)
        url = response.json()["photo_url"]
        self.assertTrue(url.startswith("/api/me/photo/?v="))
        image_response = self.client.get(url)
        self.assertEqual(image_response.status_code, 200)
        self.assertEqual(image_response["Cache-Control"], "private, no-store")
        with Image.open(BytesIO(image_response.content)) as image:
            self.assertEqual(image.format, "JPEG")
            self.assertLessEqual(max(image.size), 512)
            self.assertFalse(image.getexif())
        self.assertNotEqual(self.client.post("/api/me/photo/", {"photo": photo()}, format="multipart").json()["photo_url"], url)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_authenticate(self.user)
        self.assertIsNone(self.client.delete("/api/me/photo/").json()["photo_url"])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_invalid_files_size_and_fields_preserve_existing_photo(self):
        self.client.post("/api/me/photo/", {"photo": photo()}, format="multipart")
        self.user.refresh_from_db()
        version = self.user.photo_version
        invalid = [
            SimpleUploadedFile("fake.png", b"<svg>not an image</svg>", content_type="image/png"),
            SimpleUploadedFile("large.jpg", b"x" * (5 * 1024 * 1024 + 1), content_type="image/jpeg"),
            photo("GIF"),
        ]
        for file in invalid:
            self.assertEqual(self.client.post("/api/me/photo/", {"photo": file}, format="multipart").status_code, 400)
        self.assertEqual(self.client.post("/api/me/photo/", {"photo": photo(), "user_id": self.other.id}, format="multipart").status_code, 400)
        self.user.refresh_from_db()
        self.assertEqual(self.user.photo_version, version)
        self.assertEqual(self.client.patch("/api/me/", {"photo_url": "https://example.test"}, format="json").status_code, 400)

    def test_supported_formats_and_pixel_limit(self):
        for format in ["JPEG", "PNG", "WEBP"]:
            self.assertEqual(self.client.post("/api/me/photo/", {"photo": photo(format)}, format="multipart").status_code, 200)
        self.assertEqual(self.client.post("/api/me/photo/", {"photo": photo(size=(4100, 4000))}, format="multipart").status_code, 400)

    def test_anonymous_and_csrf_protection(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/me/photo/").status_code, 403)
        self.assertEqual(self.client.post("/api/me/photo/", {"photo": photo()}, format="multipart").status_code, 403)
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post("/api/me/photo/", {"photo": photo()}, format="multipart").status_code, 403)
