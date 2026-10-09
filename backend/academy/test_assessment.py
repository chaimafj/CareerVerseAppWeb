from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import Attempt, CourseCompletion, Lab, Result, User
from .services import grade, snapshot_lab


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class CareerAssessmentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=StringIO())
        call_command("seed_premium", stdout=StringIO())
        cls.user = User.objects.create_user("assessment@example.test", "Test-only-932!", name="Student")
        cls.other = User.objects.create_user("other-assessment@example.test", "Test-only-932!", name="Other")

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.labs = list(Lab.objects.filter(career__slug="angular", is_premium=False).order_by("level"))

    def record(self, lab, score, user=None):
        snapshot = snapshot_lab(lab)
        attempt = Attempt.objects.create(user=user or self.user, lab=lab, snapshot=snapshot)
        answers = [
            {"question_id": q["id"], "option_ids": [],
             **({"code_text": ""} if q.get("kind") == "code" else {})}
            for q in snapshot["questions"]
        ]
        graded = grade(snapshot, answers, 10)
        graded["score"] = score
        graded["passed"] = score >= 70
        return Result.objects.create(attempt=attempt, **graded)

    def assessment(self):
        response = self.client.get("/api/careers/angular/assessment/")
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_incomplete_no_final_score_and_premium_does_not_count(self):
        self.record(self.labs[0], 50)
        self.record(self.labs[1], 40)
        self.record(self.labs[2], 100, self.other)
        self.record(Lab.objects.get(career__slug="angular", is_premium=True), 100)
        data = self.assessment()
        self.assertFalse(data["complete"])
        self.assertEqual(data["completed_labs"], 2)
        self.assertEqual(data["required_labs"], 3)
        self.assertIsNone(data["final_score"])
        self.assertEqual(data["learning_path"], [])
        self.assertFalse(data["needs_improvement"])

    def test_low_score_targets_courses_ordered_weakest_first(self):
        records = [self.record(lab, score) for lab, score in zip(self.labs, [50, 20, 40])]
        CourseCompletion.objects.create(user=self.user, course=self.labs[1].course)
        data = self.assessment()
        self.assertTrue(data["complete"])
        self.assertEqual(data["final_score"], 36.67)
        self.assertTrue(data["needs_improvement"])
        self.assertEqual([step["lab_id"] for step in data["learning_path"]], [self.labs[1].id, self.labs[2].id, self.labs[0].id])
        self.assertTrue(data["learning_path"][0]["course_completed"])
        self.assertTrue(all(step["weak_skills"] for step in data["learning_path"]))
        self.assertEqual(data["learning_path"][0]["result_id"], records[1].id)
        self.assertTrue(all(not Lab.objects.get(pk=step["lab_id"]).is_premium for step in data["learning_path"]))
        self.assertEqual(self.client.get("/api/careers/angular/").json()["assessment"], data)
        self.assertIn(data, self.client.get("/api/career-assessments/").json())

    def test_threshold_exact_60_and_rounding(self):
        for lab in self.labs:
            self.record(lab, 59.99)
        self.assertTrue(self.assessment()["needs_improvement"])
        self.assertEqual(self.assessment()["final_score"], 59.99)
        for lab in self.labs:
            self.record(lab, 60)
        self.assertFalse(self.assessment()["needs_improvement"])
        self.assertEqual(self.assessment()["final_score"], 60)
        self.assertEqual(self.assessment()["learning_path"], [])

    def test_best_scores_survive_worse_retake_and_update_on_improvement(self):
        for lab in self.labs:
            self.record(lab, 50)
        self.record(self.labs[0], 20)
        self.assertEqual(self.assessment()["final_score"], 50)
        self.record(self.labs[0], 100)
        self.assertEqual(self.assessment()["final_score"], 66.67)
        self.assertFalse(self.assessment()["needs_improvement"])

    def test_display_rounding_and_empty_career(self):
        from .models import Career

        for lab, score in zip(self.labs, [59.99, 60, 60]):
            self.record(lab, score)
        self.assertEqual(self.assessment()["final_score"], 60)
        self.assertFalse(self.assessment()["needs_improvement"])
        Career.objects.create(slug="empty", title="Empty")
        empty = self.client.get("/api/careers/empty/assessment/").json()
        self.assertFalse(empty["complete"])
        self.assertIsNone(empty["final_score"])

    def test_private_and_anonymous_access(self):
        for lab in self.labs:
            self.record(lab, 50)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.assessment()["completed_labs"], 0)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/careers/angular/assessment/").status_code, 403)
        self.assertEqual(self.client.get("/api/career-assessments/").status_code, 403)
        self.assertIsNone(self.client.get("/api/careers/angular/").json()["assessment"]["final_score"])
