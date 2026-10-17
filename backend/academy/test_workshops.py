from io import StringIO
from datetime import timedelta

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Attempt, Lab, User
from .services import grade, public_attempt
from .test_premium_labs import correct_answers


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class WorkshopTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=StringIO())
        call_command("seed_premium", stdout=StringIO())
        cls.user = User.objects.create_user("workshop@example.test", "Test-only-932!", name="Student",
                                           premium_until=timezone.now() + timedelta(days=1))

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def start(self, career):
        lab = Lab.objects.get(is_premium=True, career__slug=career)
        response = self.client.post(f"/api/labs/{lab.id}/start/")
        self.assertEqual(response.status_code, 201)
        return Attempt.objects.get(pk=response.json()["id"]), response.json()

    def test_code_answer_keys_hidden_and_typed_answers_graded_on_server(self):
        attempt, public = self.start("angular")
        self.assertTrue(all(task["kind"] == "code" and task["options"] == [] for task in public["questions"][:4]))
        self.assertEqual(public["questions"][4]["kind"], "sequence")
        self.assertNotIn("order", public["questions"][4]["workspace"])
        self.assertEqual(set(public["questions"][0]["workspace"]), {"before", "after"})
        answers = correct_answers(attempt.snapshot)
        answers[0]["code_text"] = "window.location.search"
        answers[1]["code_text"] = "  switchMap\n"
        result = self.client.post(f"/api/attempts/{attempt.id}/submit/", {"answers": answers}, format="json")
        self.assertEqual(result.status_code, 201)
        self.assertEqual(result.json()["correct"], 4)
        self.assertEqual(result.json()["score"], 84)
        feedback = result.json()["feedback"][0]
        self.assertEqual(feedback["selected_options"], ["window.location.search"])
        self.assertEqual(feedback["correct_options"], ["status.is_premium"])
        self.assertEqual(feedback["workspace"], public["questions"][0]["workspace"])

    def test_invalid_payload_types_and_option_bypass_rejected_without_claiming_attempt(self):
        attempt, _ = self.start("angular")
        answers = correct_answers(attempt.snapshot)
        answers[0]["option_ids"] = [attempt.snapshot["questions"][0]["options"][0]["id"]]
        self.assertEqual(self.client.post(f"/api/attempts/{attempt.id}/submit/", {"answers": answers}, format="json").status_code, 400)
        answers = correct_answers(attempt.snapshot)
        answers[0].pop("code_text")
        self.assertEqual(self.client.post(f"/api/attempts/{attempt.id}/submit/", {"answers": answers}, format="json").status_code, 400)
        answers = correct_answers(attempt.snapshot)
        answers[0]["code_text"] = "x" * 501
        self.assertEqual(self.client.post(f"/api/attempts/{attempt.id}/submit/", {"answers": answers}, format="json").status_code, 400)
        attempt.refresh_from_db()
        self.assertIsNone(attempt.submitted_at)

    def test_architecture_mapping_wrong_node_and_foreign_options(self):
        attempt, public = self.start("cloud")
        self.assertTrue(all(task["kind"] == "architecture" for task in public["questions"][:4]))
        self.assertEqual(public["questions"][4]["kind"], "sequence")
        self.assertEqual(public["questions"][0]["workspace"]["nodes"][1], "")
        answers = correct_answers(attempt.snapshot)
        answers[0]["option_ids"] = [attempt.snapshot["questions"][0]["options"][0]["id"]]
        self.assertEqual(grade(attempt.snapshot, answers, 10)["correct"], 4)
        answers[0]["option_ids"] = [attempt.snapshot["questions"][1]["options"][0]["id"]]
        response = self.client.post(f"/api/attempts/{attempt.id}/submit/", {"answers": answers}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_evidence_exact_selection_and_code_in_mixed_workshop(self):
        attempt, public = self.start("cybersecurity")
        self.assertEqual([task["kind"] for task in public["questions"]],
                         ["evidence", "evidence", "code", "architecture", "sequence"])
        answers = correct_answers(attempt.snapshot)
        answers[0]["option_ids"].pop()
        self.assertEqual(grade(attempt.snapshot, answers, 10)["correct"], 4)

    def test_invalid_workspace_rejected_and_existing_snapshot_frozen(self):
        attempt, public = self.start("cloud")
        question = attempt.lab.questions.first()
        question.workspace["gap"] = 99
        question.save()
        response = self.client.post(f"/api/labs/{attempt.lab_id}/start/")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Attempt.objects.count(), 1)
        self.assertEqual(public_attempt(attempt), public)
        self.assertEqual(grade(attempt.snapshot, correct_answers(attempt.snapshot), 10)["score"], 100)

    def test_free_and_legacy_quizzes_still_use_original_answer_contract(self):
        self.assertTrue(all(q.kind == "quiz" and q.workspace == {} for lab in Lab.objects.filter(is_premium=False) for q in lab.questions.all()))
        free = Lab.objects.filter(is_premium=False).first()
        response = self.client.post(f"/api/labs/{free.id}/start/")
        attempt = Attempt.objects.get(pk=response.json()["id"])
        for task in attempt.snapshot["questions"]:
            task.pop("kind")
            task.pop("workspace")
        self.assertTrue(all(task["kind"] == "quiz" for task in public_attempt(attempt)["questions"]))
        self.assertEqual(grade(attempt.snapshot, correct_answers(attempt.snapshot), 10)["score"], 100)
