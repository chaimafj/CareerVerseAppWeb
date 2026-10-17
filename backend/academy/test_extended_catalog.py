from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .extended_data import CAREERS
from .models import Attempt, Career, Course, CourseCompletion, Lab, Option, Question, Result, User


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ExtendedCatalogTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=StringIO())
        call_command("seed_premium", stdout=StringIO())
        cls.original_ids = {
            model: set(model.objects.values_list("id", flat=True))
            for model in (Career, Course, Lab, Question, Option)
        }
        call_command("seed_extended", stdout=StringIO())
        cls.user = User.objects.create_user(
            "extended@example.test", "Test-only-932!", name="Learner",
            interests=["machine learning", "automation", "statistics"],
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def start_and_submit(self, lab):
        response = self.client.post(f"/api/labs/{lab.id}/start/", {}, format="json")
        self.assertEqual(response.status_code, 201)
        public = response.json()
        self.assertEqual(len(public["questions"]), 3)
        for question in public["questions"]:
            self.assertNotIn("explanation", question)
            self.assertTrue(all(set(option) == {"id", "text"} for option in question["options"]))
        attempt = Attempt.objects.get(pk=public["id"])
        answers = [
            {"question_id": question["id"], "option_ids": [
                option["id"] for option in question["options"] if option["correct"]
            ]}
            for question in attempt.snapshot["questions"]
        ]
        response = self.client.post(
            f"/api/attempts/{attempt.id}/submit/", {"answers": answers}, format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["score"], 100)
        return attempt, response.json()

    def test_seed_structure_validation_and_idempotence(self):
        self.assertEqual(Career.objects.count(), 9)
        self.assertEqual(Lab.objects.count(), 30)
        self.assertEqual(Course.objects.count(), 30)
        slugs = [career["slug"] for career in CAREERS]
        self.assertEqual(Question.objects.filter(lab__career__slug__in=slugs).count(), 54)
        ids = {model: set(model.objects.values_list("id", flat=True)) for model in self.original_ids}
        call_command("seed_extended", stdout=StringIO())
        for model, values in ids.items():
            self.assertEqual(set(model.objects.values_list("id", flat=True)), values)
            self.assertTrue(self.original_ids[model] <= values)
        self.assertEqual(User.objects.count(), 1)
        for slug in slugs:
            career = Career.objects.get(slug=slug)
            career.full_clean()
            self.assertEqual(list(career.labs.values_list("level", flat=True)), [1, 2, 3])
            for lab in career.labs.all():
                lab.full_clean()
                self.assertFalse(lab.is_premium)
                self.assertTrue(lab.scenario and lab.objectives)
                lab.course.full_clean()
                self.assertEqual(len(lab.course.lessons), 3)
                for question in lab.questions.all():
                    question.full_clean()
                    self.assertEqual(question.options.count(), 4)
                    self.assertEqual(question.multiple, question.options.filter(correct=True).count() > 1)
                    self.assertTrue(question.options.filter(correct=True).exists())

    def test_every_new_path_is_readable_completable_and_assessed(self):
        for career in CAREERS:
            slug = career["slug"]
            with self.subTest(slug=slug):
                response = self.client.get(f"/api/careers/{slug}/")
                self.assertEqual(response.status_code, 200)
                detail = response.json()
                self.assertEqual(len(detail["courses"]), 3)
                self.assertEqual(len(detail["labs"]), 3)
                for lab in Lab.objects.filter(career__slug=slug):
                    course_response = self.client.get(f"/api/courses/{lab.course.id}/")
                    self.assertEqual(course_response.status_code, 200)
                    self.assertEqual(len(course_response.json()["lessons"]), 3)
                    completed = self.client.post(f"/api/courses/{lab.course.id}/complete/", {}, format="json")
                    self.assertEqual(completed.status_code, 200)
                    self.start_and_submit(lab)
                assessment = self.client.get(f"/api/careers/{slug}/assessment/").json()
                self.assertTrue(assessment["complete"])
                self.assertEqual(assessment["final_score"], 100)
        progress = self.client.get("/api/progress/").json()
        self.assertEqual(progress["completed_labs"], 18)
        self.assertEqual(progress["completed_courses"], 18)
        self.assertEqual(progress["total_labs"], 30)
        self.assertEqual(Result.objects.count(), 18)

    def test_seed_preserves_original_and_new_history(self):
        old_lab = Lab.objects.get(career__slug="angular", level=1, is_premium=False)
        new_lab = Lab.objects.get(career__slug="devops", level=1)
        old_attempt, old_result = self.start_and_submit(old_lab)
        new_attempt, new_result = self.start_and_submit(new_lab)
        old_snapshot = old_attempt.snapshot
        new_snapshot = new_attempt.snapshot
        CourseCompletion.objects.create(user=self.user, course=new_lab.course)
        call_command("seed_extended", stdout=StringIO())
        old_attempt.refresh_from_db()
        new_attempt.refresh_from_db()
        self.assertEqual(old_attempt.snapshot, old_snapshot)
        self.assertEqual(new_attempt.snapshot, new_snapshot)
        self.assertEqual(self.client.get(f"/api/results/{old_result['id']}/").json(), old_result)
        self.assertEqual(self.client.get(f"/api/results/{new_result['id']}/").json(), new_result)
        self.assertEqual(CourseCompletion.objects.filter(user=self.user).count(), 1)
        self.assertEqual(Result.objects.count(), 2)

    def test_catalog_recommendations_interests_and_chat_include_new_careers(self):
        slugs = {career["slug"] for career in CAREERS}
        self.assertTrue(slugs <= {career["slug"] for career in self.client.get("/api/careers/").json()})
        matches = self.client.get("/api/recommendations/")
        self.assertEqual(matches.status_code, 200)
        self.assertTrue(slugs <= {item["career_slug"] for item in matches.json()})
        for path in ("/api/labs/", "/api/courses/"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(slugs <= {item["career_slug"] for item in response.json()})
        response = self.client.post("/api/chat/", {"message": "DevOps"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertIn("/careers/devops", [action["path"] for action in response.json()["actions"]])
