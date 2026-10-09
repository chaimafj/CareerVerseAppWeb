from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import Attempt, Lab, Result, User


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class LabHistoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=StringIO())
        cls.user = User.objects.create_user("history@example.test", "Test-only-932!", name="Student")
        cls.other = User.objects.create_user("other-history@example.test", "Test-only-932!", name="Other")
        cls.lab = Lab.objects.filter(career__slug="angular", level=1).get()

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def submit(self, wrong=False):
        response = self.client.post(f"/api/labs/{self.lab.id}/start/")
        self.assertEqual(response.status_code, 201)
        attempt = Attempt.objects.get(pk=response.json()["id"])
        answers = [
            {"question_id": question["id"],
             "option_ids": [option["id"] for option in question["options"] if option["correct"] != wrong]}
            for question in attempt.snapshot["questions"]
        ]
        # Single-choice questions must retain exactly one choice even when wrong.
        if wrong:
            for answer, question in zip(answers, attempt.snapshot["questions"]):
                if not question["multiple"]:
                    answer["option_ids"] = answer["option_ids"][:1]
        result = self.client.post(f"/api/attempts/{attempt.id}/submit/", {"answers": answers}, format="json")
        self.assertEqual(result.status_code, 201)
        return result.json()

    def test_completion_latest_vs_best_and_retake_history(self):
        preview = self.client.get(f"/api/labs/{self.lab.id}/").json()
        self.assertFalse(preview["completed"])
        self.assertEqual(preview["results"], [])
        first = self.submit()
        second = self.submit(wrong=True)
        preview = self.client.get(f"/api/labs/{self.lab.id}/").json()
        self.assertTrue(preview["completed"])
        self.assertEqual(preview["attempt_count"], 2)
        self.assertEqual([r["id"] for r in preview["results"]], [second["id"], first["id"]])
        self.assertFalse(preview["latest_result"]["passed"])
        lab = next(lab for lab in self.client.get("/api/careers/angular/").json()["labs"] if lab["id"] == self.lab.id)
        self.assertEqual(lab["best_score"], 100)
        self.assertEqual(lab["latest_result"]["score"], second["score"])
        self.assertTrue(lab["completed"])  # Completed does not mean passed.
        self.assertEqual(second["lab_id"], self.lab.id)
        self.assertTrue(all(not feedback["correct"] for feedback in second["feedback"]))
        self.assertTrue(all(feedback["correct_options"] for feedback in second["feedback"]))
        self.assertEqual(self.client.get(f"/api/results/{first['id']}/").json(), first)
        self.assertEqual(Result.objects.count(), 2)

    def test_separate_catalogs_and_course_completion_does_not_start_lab(self):
        courses = self.client.get("/api/courses/").json()
        self.assertEqual(len(courses), 9)
        self.assertTrue(all("lessons" not in course for course in courses))
        course_id = self.lab.course.id
        self.assertFalse(self.client.get(f"/api/courses/{course_id}/").json()["completed"])
        self.assertEqual(self.client.post(f"/api/courses/{course_id}/complete/").status_code, 200)
        self.assertTrue(self.client.get(f"/api/courses/{course_id}/").json()["completed"])
        course = next(c for c in self.client.get("/api/courses/").json() if c["id"] == course_id)
        self.assertTrue(course["completed"])
        self.assertFalse(Attempt.objects.exists())
        labs = self.client.get("/api/labs/").json()
        self.assertEqual(len(labs), 9)
        self.assertTrue(all(not lab["completed"] for lab in labs))
        self.assertTrue(all("questions" not in lab for lab in labs))
        self.client.force_authenticate(self.other)
        self.assertFalse(self.client.get(f"/api/courses/{course_id}/").json()["completed"])
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/courses/").status_code, 403)
        self.assertEqual(self.client.get("/api/labs/").status_code, 403)

    def test_history_is_owner_private_and_unsubmitted_attempt_is_not_completed(self):
        result = self.submit()
        self.client.force_authenticate(self.other)
        self.client.post(f"/api/labs/{self.lab.id}/start/")
        preview = self.client.get(f"/api/labs/{self.lab.id}/").json()
        self.assertFalse(preview["completed"])
        self.assertIsNone(preview["latest_result"])
        self.assertEqual(preview["results"], [])
        self.assertEqual(self.client.get(f"/api/results/{result['id']}/").status_code, 404)
        self.client.force_authenticate(None)
        lab = next(lab for lab in self.client.get("/api/careers/angular/").json()["labs"] if lab["id"] == self.lab.id)
        self.assertFalse(lab["completed"])
        self.assertIsNone(lab["latest_result"])

    def test_legacy_corrections_come_from_snapshot_without_modifying_saved_result(self):
        response = self.submit(wrong=True)
        result = Result.objects.get(pk=response["id"])
        for item in result.feedback:
            item.pop("selected_options")
            item.pop("correct_options")
        result.save()
        self.lab.questions.first().options.update(text="Changed catalog text")
        historical = self.client.get(f"/api/results/{result.id}/").json()
        self.assertTrue(all(item["correct_options"] for item in historical["feedback"]))
        self.assertNotIn("Changed catalog text", str(historical["feedback"]))
        self.assertTrue(all("selected_options" not in item for item in historical["feedback"]))
        result.refresh_from_db()
        self.assertTrue(all("correct_options" not in item for item in result.feedback))
