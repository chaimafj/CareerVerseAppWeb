from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Attempt, Course, CourseCompletion, Lab, User
from .services import public_attempt


def correct_answers(snapshot):
    answers = []
    for question in snapshot["questions"]:
        expected = [option for option in question["options"] if option["correct"]]
        if question.get("kind") == "code":
            answers.append({"question_id": question["id"], "option_ids": [], "code_text": expected[0]["text"]})
        else:
            answers.append({"question_id": question["id"], "option_ids": [option["id"] for option in expected]})
    return answers


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class PremiumLabTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=StringIO())
        call_command("seed_premium", stdout=StringIO())
        cls.user = User.objects.create_user("lab-access@example.test", "Test-only-932!", name="Student")

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.lab = Lab.objects.filter(is_premium=True, career__slug="angular").get()
        self.course = Course.objects.get(lab=self.lab)

    def activate(self, expiry=None):
        self.user.premium_until = expiry or timezone.now() + timedelta(days=30)
        self.user.save()

    def test_seed_idempotent_free_content_and_history_preserved(self):
        free = Lab.objects.filter(is_premium=False).first()
        attempt = Attempt.objects.create(user=self.user, lab=free, snapshot={"historical": True})
        ids = list(Lab.objects.order_by("id").values_list("id", flat=True))
        call_command("seed_demo", stdout=StringIO())
        call_command("seed_premium", stdout=StringIO())
        self.assertEqual(list(Lab.objects.order_by("id").values_list("id", flat=True)), ids)
        self.assertEqual(Lab.objects.filter(is_premium=False).count(), 9)
        self.assertEqual(Lab.objects.filter(is_premium=True).count(), 3)
        self.assertEqual(self.lab.questions.count(), 5)
        attempt.refresh_from_db()
        self.assertEqual(attempt.snapshot, {"historical": True})

    def test_lock_enforced_on_direct_api_and_expiry(self):
        for expiry in [None, timezone.now() - timedelta(seconds=1)]:
            self.user.premium_until = expiry
            self.user.save()
            self.assertEqual(self.client.post(f"/api/labs/{self.lab.id}/start/").status_code, 403)
            self.assertEqual(self.client.get(f"/api/courses/{self.course.id}/").status_code, 403)
            self.assertEqual(self.client.post(f"/api/courses/{self.course.id}/complete/").status_code, 403)
        self.assertFalse(Attempt.objects.exists())
        self.assertFalse(CourseCompletion.objects.exists())
        free = Lab.objects.filter(is_premium=False).first()
        self.assertEqual(self.client.post(f"/api/labs/{free.id}/start/").status_code, 201)

    def test_preview_has_no_answers_and_reports_locked_state(self):
        preview = self.client.get(f"/api/labs/{self.lab.id}/").json()
        self.assertTrue(preview["locked"])
        self.assertEqual(preview["question_count"], 5)
        self.assertNotIn("questions", preview)
        detail = self.client.get("/api/careers/angular/").json()
        self.assertTrue(next(lab for lab in detail["labs"] if lab["id"] == self.lab.id)["locked"])
        self.assertTrue(next(c for c in detail["courses"] if c["id"] == self.course.id)["locked"])
        self.activate()
        self.assertFalse(self.client.get(f"/api/labs/{self.lab.id}/").json()["locked"])

    def test_separate_catalogs_preserve_premium_lock_without_leaking_content(self):
        for path, item_id in [("/api/courses/", self.course.id), ("/api/labs/", self.lab.id)]:
            items = self.client.get(path).json()
            self.assertEqual(len(items), 12)
            item = next(item for item in items if item["id"] == item_id)
            self.assertTrue(item["locked"])
            self.assertNotIn("lessons", item)
            self.assertNotIn("questions", item)
        self.activate()
        for path, item_id in [("/api/courses/", self.course.id), ("/api/labs/", self.lab.id)]:
            item = next(item for item in self.client.get(path).json() if item["id"] == item_id)
            self.assertFalse(item["locked"])

    def test_anonymous_cannot_access_premium_content(self):
        self.client.force_authenticate(user=None)
        for path in [f"/api/labs/{self.lab.id}/", f"/api/courses/{self.course.id}/"]:
            self.assertEqual(self.client.get(path).status_code, 403)
        self.assertEqual(self.client.post(f"/api/labs/{self.lab.id}/start/").status_code, 403)
        self.assertFalse(Attempt.objects.exists())

    def test_all_premium_packs_are_valid_and_fully_gradable(self):
        self.activate()
        for lab in Lab.objects.filter(is_premium=True):
            response = self.client.post(f"/api/labs/{lab.id}/start/")
            self.assertEqual(response.status_code, 201)
            attempt = Attempt.objects.get(pk=response.json()["id"])
            answers = correct_answers(attempt.snapshot)
            result = self.client.post(f"/api/attempts/{attempt.id}/submit/", {"answers": answers}, format="json")
            self.assertEqual(result.status_code, 201)
            self.assertEqual(result.json()["score"], 100)
            self.assertEqual(result.json()["total"], 5)

    def test_legacy_snapshot_does_not_require_mission_fields(self):
        free = Lab.objects.filter(is_premium=False).first()
        response = self.client.post(f"/api/labs/{free.id}/start/")
        attempt = Attempt.objects.get(pk=response.json()["id"])
        for field in ["scenario", "objectives", "is_premium"]:
            attempt.snapshot.pop(field)
        legacy = public_attempt(attempt)
        self.assertEqual(legacy["objectives"], [])
        self.assertEqual(legacy["scenario"], "")
        self.assertFalse(legacy["is_premium"])

    def test_premium_attempt_snapshot_feedback_and_grandfathered_submission(self):
        self.activate()
        self.assertEqual(self.client.get(f"/api/courses/{self.course.id}/").status_code, 200)
        self.assertEqual(self.client.post(f"/api/courses/{self.course.id}/complete/").status_code, 200)
        response = self.client.post(f"/api/labs/{self.lab.id}/start/")
        self.assertEqual(response.status_code, 201)
        public = response.json()
        self.assertEqual(public["scenario"], self.lab.scenario)
        self.assertTrue(public["is_premium"])
        for question in public["questions"]:
            for option in question["options"]:
                self.assertNotIn("correct", option)
        attempt = Attempt.objects.get(pk=public["id"])
        self.lab.scenario = "Edited mission"
        self.lab.save()
        self.activate(timezone.now() - timedelta(seconds=1))
        answers = correct_answers(attempt.snapshot)
        result = self.client.post(f"/api/attempts/{attempt.id}/submit/", {"answers": answers}, format="json")
        self.assertEqual(result.status_code, 201)
        self.assertEqual(result.json()["score"], 100)
        self.assertEqual(len(result.json()["feedback"]), 5)
        self.assertTrue(all(f["explanation"] for f in result.json()["feedback"]))
        self.assertTrue(all(f["selected_options"] == f["correct_options"] for f in result.json()["feedback"]))
        attempt.refresh_from_db()
        self.assertNotEqual(attempt.snapshot["scenario"], "Edited mission")
        self.assertEqual(self.client.get(f"/api/results/{result.json()['id']}/").status_code, 200)
        self.assertEqual(self.client.post(f"/api/labs/{self.lab.id}/start/").status_code, 403)
