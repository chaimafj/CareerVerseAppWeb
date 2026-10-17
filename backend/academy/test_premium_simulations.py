from copy import deepcopy
from datetime import timedelta
from io import StringIO

from django.core.exceptions import ValidationError as ModelValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from .models import Attempt, Course, Lab, Option, Question, User
from .services import grade, public_attempt, snapshot_lab
from .test_premium_labs import correct_answers


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class PremiumSimulationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=StringIO())
        call_command("seed_extended", stdout=StringIO())
        call_command("seed_premium", stdout=StringIO())
        cls.user = User.objects.create_user(
            "simulator@example.test", "Test-only-932!", name="Learner",
            premium_until=timezone.now() + timedelta(days=1),
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_nine_paths_have_five_varied_tasks_and_preparation_lessons(self):
        self.assertEqual(Lab.objects.filter(is_premium=True).count(), 9)
        self.assertEqual(Lab.objects.filter(is_premium=False).count(), 27)
        self.assertEqual(Course.objects.count(), 36)
        self.assertEqual(Question.objects.count(), 126)
        for lab in Lab.objects.filter(is_premium=True).select_related("course"):
            with self.subTest(career=lab.career.slug):
                lab.full_clean()
                lab.course.full_clean()
                tasks = list(lab.questions.all())
                self.assertEqual(len(tasks), 5)
                self.assertEqual(len(lab.course.lessons), 5)
                course_response = self.client.get(f"/api/courses/{lab.course.id}/")
                self.assertEqual(course_response.status_code, 200)
                self.assertEqual(len(course_response.json()["lessons"]), 5)
                self.assertEqual(
                    self.client.post(f"/api/courses/{lab.course.id}/complete/").status_code, 200,
                )
                self.assertNotIn("quiz", [task.kind for task in tasks])
                self.assertGreaterEqual(len({task.kind for task in tasks}), 2)
                self.assertIn("sequence", [task.kind for task in tasks])
                for task in tasks:
                    task.full_clean()
                response = self.client.post(f"/api/labs/{lab.id}/start/")
                self.assertEqual(response.status_code, 201)
                public = response.json()
                self.assertTrue(all("order" not in task["workspace"] for task in public["questions"]))
                self.assertTrue(all("correct" not in option for task in public["questions"] for option in task["options"]))
                attempt = Attempt.objects.get(pk=public["id"])
                response = self.client.post(
                    f"/api/attempts/{attempt.id}/submit/",
                    {"answers": correct_answers(attempt.snapshot)}, format="json",
                )
                self.assertEqual(response.status_code, 201)
                self.assertEqual(response.json()["correct"], 5)
                self.assertEqual(response.json()["score"], 100)
                for feedback in response.json()["feedback"]:
                    self.assertEqual(feedback["selected_options"], feedback["correct_options"])

    def test_workflow_order_not_set_membership_determines_correctness(self):
        lab = Lab.objects.get(career__slug="devops", is_premium=True)
        snapshot = snapshot_lab(lab)
        answers = correct_answers(snapshot)
        self.assertEqual(grade(snapshot, answers, 10)["score"], 100)
        answers[0]["option_ids"].reverse()
        wrong = grade(snapshot, answers, 10)
        self.assertEqual(wrong["correct"], 4)
        self.assertEqual(wrong["score"], 84)
        self.assertEqual(wrong["feedback"][0]["selected_options"],
                         list(reversed(wrong["feedback"][0]["correct_options"])))
        answers[0]["option_ids"].pop()
        self.assertEqual(grade(snapshot, answers, 10)["correct"], 4)
        answers[0]["option_ids"] = []
        self.assertEqual(grade(snapshot, answers, 10)["correct"], 4)

    def test_workflow_invalid_options_duplicates_and_code_payload_rejected(self):
        lab = Lab.objects.get(career__slug="devops", is_premium=True)
        response = self.client.post(f"/api/labs/{lab.id}/start/")
        attempt = Attempt.objects.get(pk=response.json()["id"])
        original = correct_answers(attempt.snapshot)
        foreign = attempt.snapshot["questions"][2]["options"][0]["id"]
        for option_ids in [[foreign], [original[0]["option_ids"][0]] * 2]:
            answers = deepcopy(original)
            answers[0]["option_ids"] = option_ids
            response = self.client.post(f"/api/attempts/{attempt.id}/submit/", {"answers": answers}, format="json")
            self.assertEqual(response.status_code, 400)
        answers = deepcopy(original)
        answers[0]["code_text"] = "not valid for workflow"
        with self.assertRaises(ValidationError):
            grade(attempt.snapshot, answers, 10)
        attempt.refresh_from_db()
        self.assertIsNone(attempt.submitted_at)

    def test_invalid_workflow_configuration_rejected_without_new_attempt(self):
        task = Question.objects.filter(kind="sequence").first()
        original = deepcopy(task.workspace)
        for order in [[0, 0, 1, 2], [0, 1], [0, 1, 2, True], [0, 1, 2, 9]]:
            task.workspace = {**original, "order": order}
            with self.assertRaises(ModelValidationError):
                task.clean()
        task.workspace = original
        task.save()
        task.options.last().delete()
        response = self.client.post(f"/api/labs/{task.lab_id}/start/")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Attempt.objects.count(), 0)

    def test_all_premium_courses_and_simulations_enforce_expiry(self):
        self.user.premium_until = timezone.now() - timedelta(seconds=1)
        self.user.save()
        for lab in Lab.objects.filter(is_premium=True).select_related("course"):
            self.assertEqual(self.client.post(f"/api/labs/{lab.id}/start/").status_code, 403)
            self.assertEqual(self.client.get(f"/api/courses/{lab.course.id}/").status_code, 403)
            self.assertEqual(self.client.post(f"/api/courses/{lab.course.id}/complete/").status_code, 403)
        self.assertEqual(Attempt.objects.count(), 0)

    def test_reseed_retains_ids_snapshots_and_expired_attempt_submission(self):
        lab = Lab.objects.get(career__slug="devops", is_premium=True)
        attempt = Attempt.objects.create(user=self.user, lab=lab, snapshot=snapshot_lab(lab))
        snapshot = deepcopy(attempt.snapshot)
        public = public_attempt(attempt)
        ids = {model: set(model.objects.values_list("id", flat=True)) for model in (Lab, Course, Question, Option)}
        call_command("seed_premium", stdout=StringIO())
        for model, values in ids.items():
            self.assertEqual(set(model.objects.values_list("id", flat=True)), values)
        attempt.refresh_from_db()
        self.assertEqual(attempt.snapshot, snapshot)
        self.assertEqual(public_attempt(attempt), public)
        self.user.premium_until = timezone.now() - timedelta(seconds=1)
        self.user.save()
        response = self.client.post(f"/api/attempts/{attempt.id}/submit/",
                                    {"answers": correct_answers(snapshot)}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["score"], 100)
