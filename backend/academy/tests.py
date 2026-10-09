from copy import deepcopy
from datetime import timedelta
from io import StringIO

from django.contrib import admin
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Attempt, Career, Course, CourseCompletion, Lab, Option, Question, Result, User

PASSWORD = "Unusual-passphrase-932!"
FAST_PASSWORDS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
PROFILE_FIELDS = {"id", "email", "name", "interests", "university", "specialty", "study_level", "bio", "photo_url"}
RESULT_FIELDS = {
    "id", "career_title", "career_slug", "lab_title", "correct", "total", "score",
    "time_score", "duration_seconds", "passed", "skills", "feedback", "lab_id",
}


@override_settings(PASSWORD_HASHERS=FAST_PASSWORDS)
class AuthTests(TestCase):
    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)
        self.user = User.objects.create_user("student@example.com", PASSWORD, name="Student")

    def token(self):
        response = self.client.get("/api/csrf/")
        self.assertEqual(response.status_code, 200)
        return self.client.cookies["csrftoken"].value

    def login(self):
        response = self.client.post(
            "/api/auth/login/", {"email": self.user.email, "password": PASSWORD},
            format="json", HTTP_X_CSRFTOKEN=self.token(),
        )
        self.assertEqual(response.status_code, 200)
        return self.client.cookies["csrftoken"].value

    def test_register_creates_session_and_hashed_password(self):
        response = self.client.post(
            "/api/auth/register/",
            {"name": "New Student", "email": "NEW@EXAMPLE.COM", "password": PASSWORD},
            format="json", HTTP_X_CSRFTOKEN=self.token(),
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(set(response.json()), PROFILE_FIELDS)
        user = User.objects.get(email="new@example.com")
        self.assertTrue(user.check_password(PASSWORD))
        self.assertFalse(user.is_staff)
        self.assertEqual(self.client.get("/api/me/").json()["id"], user.id)

    def test_register_rejects_duplicate_weak_and_privileged_fields(self):
        payloads = [
            {"name": "Duplicate", "email": "STUDENT@EXAMPLE.COM", "password": PASSWORD},
            {"name": "Weak", "email": "weak@example.com", "password": "123"},
            {"name": "Admin", "email": "admin@example.com", "password": PASSWORD, "is_staff": True},
        ]
        for payload in payloads:
            with self.subTest(payload=payload["email"]):
                response = self.client.post(
                    "/api/auth/register/", payload, format="json", HTTP_X_CSRFTOKEN=self.token()
                )
                self.assertEqual(response.status_code, 400)
        self.assertEqual(User.objects.count(), 1)

    def test_login_case_insensitive_wrong_password_and_inactive_user(self):
        token = self.token()
        for password in ["wrong", PASSWORD]:
            response = self.client.post(
                "/api/auth/login/", {"email": "STUDENT@EXAMPLE.COM", "password": password},
                format="json", HTTP_X_CSRFTOKEN=token,
            )
            self.assertEqual(response.status_code, 400 if password == "wrong" else 200)
        self.user.is_active = False
        self.user.save()
        response = self.client.post(
            "/api/auth/login/", {"email": self.user.email, "password": PASSWORD},
            format="json", HTTP_X_CSRFTOKEN=self.token(),
        )
        self.assertEqual(response.status_code, 400)

    def test_anonymous_auth_posts_require_csrf(self):
        self.token()
        for url, body in [
            ("/api/auth/login/", {"email": self.user.email, "password": PASSWORD}),
            ("/api/auth/register/", {"email": "new@example.com", "name": "New", "password": PASSWORD}),
        ]:
            for token in [None, "x" * 32]:
                headers = {"HTTP_X_CSRFTOKEN": token} if token else {}
                response = self.client.post(url, body, format="json", **headers)
                self.assertEqual(response.status_code, 403)
                self.assertIn("CSRF", response.json()["detail"])
        self.assertEqual(User.objects.count(), 1)

    def test_authenticated_patch_and_logout_require_csrf_and_rotate_token(self):
        old = self.token()
        current = self.login()
        self.assertNotEqual(old, current)
        for token in [None, old]:
            headers = {"HTTP_X_CSRFTOKEN": token} if token else {}
            self.assertEqual(
                self.client.patch("/api/me/", {"bio": "Forged"}, format="json", **headers).status_code, 403
            )
            self.assertEqual(self.client.post("/api/auth/logout/", {}, format="json", **headers).status_code, 403)
        response = self.client.patch(
            "/api/me/",
            {"name": "Updated", "interests": [" Security ", "security"], "bio": "Hello",
             "university": "University", "specialty": "Computing", "study_level": "Bachelor"},
            format="json", HTTP_X_CSRFTOKEN=current,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["interests"], ["security"])
        self.assertEqual(set(response.json()), PROFILE_FIELDS)
        self.assertEqual(
            self.client.post("/api/auth/logout/", {}, format="json", HTTP_X_CSRFTOKEN=current).status_code, 200
        )
        self.assertEqual(self.client.get("/api/me/").status_code, 403)

    def test_profile_rejects_non_string_interests_and_readonly_fields(self):
        token = self.login()
        for body in [{"interests": [5]}, {"interests": "security"}, {"interests": [" "]},
                     {"name": ""}, {"email": "other@example.com"}, {"is_superuser": True}]:
            response = self.client.patch("/api/me/", body, format="json", HTTP_X_CSRFTOKEN=token)
            self.assertEqual(response.status_code, 400)

    def test_anonymous_private_endpoints_denied(self):
        for url in ["/api/me/", "/api/progress/", "/api/recommendations/", "/api/results/1/", "/api/courses/1/"]:
            self.assertEqual(self.client.get(url).status_code, 403)

    def test_email_uniqueness_and_superuser_manager(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user("STUDENT@EXAMPLE.COM", PASSWORD, name="Duplicate")
        superuser = User.objects.create_superuser("admin@example.com", PASSWORD, name="Admin")
        self.assertTrue(superuser.is_superuser and superuser.is_staff)
        with self.assertRaises(ValueError):
            User.objects.create_superuser("invalid@example.com", PASSWORD, is_staff=False)


@override_settings(PASSWORD_HASHERS=FAST_PASSWORDS)
class AcademyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=StringIO())
        cls.user = User.objects.create_user("owner@example.com", PASSWORD, name="Owner")
        cls.other = User.objects.create_user("other@example.com", PASSWORD, name="Other")

    def setUp(self):
        self.client = APIClient()
        self.client.force_login(self.user)
        self.lab = Lab.objects.get(career__slug="angular", level=1)

    def start(self, lab=None):
        response = self.client.post(f"/api/labs/{(lab or self.lab).id}/start/", {}, format="json")
        self.assertEqual(response.status_code, 201)
        return Attempt.objects.get(pk=response.json()["id"]), response.json()

    def answers(self, attempt):
        return {"answers": [
            {"question_id": question["id"], "option_ids": [
                option["id"] for option in question["options"] if option["correct"]
            ]}
            for question in attempt.snapshot["questions"]
        ]}

    def submit(self, attempt, payload=None):
        return self.client.post(
            f"/api/attempts/{attempt.id}/submit/", payload if payload is not None else self.answers(attempt),
            format="json",
        )

    def test_seed_idempotent_consistent_and_no_users_created(self):
        ids = list(Option.objects.values_list("id", flat=True))
        call_command("seed_demo", stdout=StringIO())
        self.assertEqual(list(Option.objects.values_list("id", flat=True)), ids)
        self.assertEqual(Career.objects.count(), 3)
        self.assertEqual(Lab.objects.count(), 9)
        self.assertEqual(Course.objects.count(), 9)
        self.assertEqual(Question.objects.count(), 27)
        self.assertEqual(Option.objects.count(), 108)
        self.assertEqual(User.objects.count(), 2)
        for career in Career.objects.all():
            self.assertEqual(list(career.labs.values_list("level", flat=True)), [1, 2, 3])
        for course in Course.objects.select_related("lab"):
            course.full_clean()
            self.assertEqual(course.career_id, course.lab.career_id)
            self.assertEqual(len(course.lessons), 3)
        for lab in Lab.objects.all():
            attempt, _ = self.start(lab)
            self.assertEqual(self.submit(attempt).json()["score"], 100)

    def test_catalog_and_course_exact_shapes_without_answer_keys(self):
        response = self.client.get("/api/careers/")
        self.assertIsInstance(response.json(), list)
        career_fields = {
            "slug", "title", "summary", "description", "category", "tools",
            "interests", "salary", "education", "outlook",
        }
        self.assertEqual(set(response.json()[0]), career_fields)
        detail = self.client.get("/api/careers/angular/").json()
        self.assertEqual(set(detail), career_fields | {"courses", "labs", "assessment"})
        self.assertEqual(set(detail["courses"][0]), {"id", "title", "completed", "lab_id", "is_premium", "locked"})
        self.assertEqual(set(detail["labs"][0]), {
            "id", "title", "level", "question_count", "best_score", "is_premium",
            "locked", "scenario", "objectives", "expected_seconds",
            "completed", "attempt_count", "latest_result",
        })
        self.assertEqual(
            [lab["level"] for lab in detail["labs"]],
            ["Beginner", "Intermediate", "Advanced"],
        )
        self.assertIsNone(detail["labs"][0]["best_score"])
        course = self.client.get(f"/api/courses/{self.lab.course.id}/").json()
        self.assertEqual(set(course), {"id", "title", "intro", "lessons", "career_slug", "lab_id", "completed"})
        self.assertEqual(set(course["lessons"][0]), {"title", "body", "example"})
        _, public = self.start()
        self.assertEqual(set(public), {
            "id", "lab_title", "career_title", "questions", "expected_seconds",
            "scenario", "objectives", "is_premium",
        })
        for question in public["questions"]:
            self.assertEqual(set(question), {"id", "prompt", "options", "multiple", "kind", "workspace"})
            for option in question["options"]:
                self.assertEqual(set(option), {"id", "text"})

    def test_catalog_public_and_student_cannot_write_catalog(self):
        for url in ["/api/careers/", "/api/careers/angular/", f"/api/courses/{self.lab.course.id}/"]:
            self.assertEqual(self.client.post(url, {}, format="json").status_code, 405)
            self.assertEqual(self.client.patch(url, {}, format="json").status_code, 405)
            self.assertEqual(self.client.delete(url).status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.get("/api/careers/").status_code, 200)
        self.assertEqual(self.client.get("/api/careers/angular/").status_code, 200)
        self.assertEqual(self.client.post(f"/api/labs/{self.lab.id}/start/", {}, format="json").status_code, 403)

    def test_full_score_result_shape_and_replay_protection(self):
        attempt, _ = self.start()
        response = self.submit(attempt)
        self.assertEqual(response.status_code, 201)
        result = response.json()
        self.assertEqual(set(result), RESULT_FIELDS)
        self.assertEqual(result["correct"], 3)
        self.assertEqual(result["total"], 3)
        self.assertEqual(result["score"], 100)
        self.assertEqual(result["time_score"], 100)
        self.assertTrue(result["passed"])
        self.assertEqual(set(result["skills"].values()), {100})
        self.assertEqual(set(result["feedback"][0]), {
            "prompt", "correct", "explanation", "selected_options", "correct_options",
            "kind", "workspace",
        })
        self.assertEqual(self.client.get(f"/api/results/{result['id']}/").json(), result)
        self.assertEqual(self.submit(attempt).status_code, 409)
        self.assertEqual(Result.objects.count(), 1)

    def test_time_formula_uses_server_elapsed_not_client_value(self):
        for elapsed, time_score, score in [(0, 100, 100), (180, 100, 100), (270, 50, 90), (360, 0, 80), (100000, 0, 80), (-60, 100, 100)]:
            with self.subTest(elapsed=elapsed):
                attempt, _ = self.start()
                Attempt.objects.filter(pk=attempt.id).update(started_at=timezone.now() - timedelta(seconds=elapsed))
                response = self.submit(attempt)
                self.assertEqual(response.status_code, 201)
                self.assertEqual(response.json()["time_score"], time_score)
                self.assertEqual(response.json()["score"], score)
                self.assertEqual(response.json()["duration_seconds"], max(0, elapsed))
        attempt, _ = self.start()
        payload = self.answers(attempt)
        payload["duration_seconds"] = 0
        self.assertEqual(self.submit(attempt, payload).status_code, 400)

    def test_wrong_empty_and_partial_multiple_answers(self):
        attempt, _ = self.start()
        payload = self.answers(attempt)
        payload["answers"][0]["option_ids"] = []
        payload["answers"][2]["option_ids"] = payload["answers"][2]["option_ids"][:1]
        result = self.submit(attempt, payload).json()
        self.assertEqual(result["correct"], 1)
        self.assertEqual(result["score"], 46.67)
        self.assertFalse(result["passed"])
        self.assertEqual(result["skills"]["accessibility"], 0)
        attempt, _ = self.start()
        payload = self.answers(attempt)
        for answer in payload["answers"]:
            answer["option_ids"] = []
        result = self.submit(attempt, payload).json()
        self.assertEqual(result["correct"], 0)
        self.assertEqual(result["score"], 20)

    def test_malformed_answers_are_rejected_without_consuming_attempt(self):
        attempt, _ = self.start()
        good = self.answers(attempt)
        bad = [[], "bad", {}, {"answers": []}, {"answers": None}, {"answers": "bad"},
               {"answers": [{}]}, {"answers": [None]}, {"answers": [[]]}]
        duplicate = deepcopy(good)
        duplicate["answers"].append(deepcopy(duplicate["answers"][0]))
        bad.append(duplicate)
        missing = deepcopy(good)
        missing["answers"].pop()
        bad.append(missing)
        for field, value in [
            ("question_id", 999999), ("question_id", True), ("question_id", 1.5),
            ("option_ids", [999999]), ("option_ids", [True]), ("option_ids", "bad"),
            ("option_ids", [good["answers"][0]["option_ids"][0]] * 2),
            ("option_ids", good["answers"][2]["option_ids"]),
            ("option_ids", [item["id"] for item in attempt.snapshot["questions"][0]["options"][:2]]),
            ("correct", True),
        ]:
            payload = deepcopy(good)
            payload["answers"][0][field] = value
            bad.append(payload)
        for payload in bad:
            with self.subTest(payload=payload):
                self.assertEqual(self.submit(attempt, payload).status_code, 400)
                attempt.refresh_from_db()
                self.assertIsNone(attempt.submitted_at)
                self.assertEqual(Result.objects.count(), 0)
        self.assertEqual(self.submit(attempt).status_code, 201)

    def test_owner_only_attempt_result_and_progress(self):
        attempt, _ = self.start()
        self.client.force_login(self.other)
        self.assertEqual(self.submit(attempt).status_code, 404)
        self.client.force_login(self.user)
        result = self.submit(attempt).json()
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(f"/api/results/{result['id']}/").status_code, 404)
        self.assertEqual(self.client.get("/api/progress/").json()["results"], [])
        self.assertTrue(all(not item["tested"] for item in self.client.get("/api/recommendations/").json()))

    def test_snapshot_preserves_corrections_after_catalog_edits_and_deletion(self):
        attempt, _ = self.start()
        payload = self.answers(attempt)
        original = deepcopy(attempt.snapshot)
        Question.objects.filter(lab=self.lab).update(prompt="Changed", explanation="Changed")
        Option.objects.filter(question__lab=self.lab).update(correct=False)
        self.lab.delete()
        response = self.submit(attempt, payload)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["correct"], 3)
        self.assertEqual(response.json()["lab_title"], original["lab_title"])
        self.assertEqual(response.json()["feedback"][0]["explanation"], original["questions"][0]["explanation"])
        self.assertEqual(self.client.get(f"/api/results/{response.json()['id']}/").status_code, 200)

    def test_unknown_snapshot_version_rejected(self):
        attempt, _ = self.start()
        Attempt.objects.filter(pk=attempt.pk).update(schema_version=99)
        self.assertEqual(self.submit(attempt).status_code, 409)
        self.assertFalse(Result.objects.exists())

    def test_invalid_lab_configuration_returns_explicit_error(self):
        Option.objects.filter(question__lab=self.lab).update(correct=False)
        self.assertEqual(self.client.post(f"/api/labs/{self.lab.id}/start/", {}, format="json").status_code, 400)
        self.assertEqual(Attempt.objects.count(), 0)
        self.lab.questions.all().delete()
        self.assertEqual(self.client.post(f"/api/labs/{self.lab.id}/start/", {}, format="json").status_code, 400)

    def test_course_completion_idempotent_and_progress_best_score(self):
        course = self.lab.course
        for _ in range(2):
            self.assertEqual(
                self.client.post(f"/api/courses/{course.id}/complete/", {}, format="json").json(),
                {"id": course.id, "completed": True},
            )
        self.assertEqual(CourseCompletion.objects.count(), 1)
        attempt, _ = self.start()
        self.submit(attempt)
        attempt, _ = self.start()
        payload = self.answers(attempt)
        for answer in payload["answers"]:
            answer["option_ids"] = []
        self.submit(attempt, payload)
        progress = self.client.get("/api/progress/").json()
        self.assertEqual(set(progress), {"completed_labs", "total_labs", "average_score", "completed_courses", "results"})
        self.assertEqual(progress["completed_labs"], 1)
        self.assertEqual(progress["total_labs"], 9)
        self.assertEqual(progress["completed_courses"], 1)
        self.assertEqual(progress["average_score"], 60)
        self.assertEqual(set(progress["results"][0]), {"id", "career_title", "lab_title", "score", "completed_at"})
        career = self.client.get("/api/careers/angular/").json()
        self.assertEqual(career["labs"][0]["best_score"], 100)
        self.assertTrue(career["courses"][0]["completed"])
        self.client.force_login(self.other)
        self.assertFalse(self.client.get("/api/careers/angular/").json()["courses"][0]["completed"])

    def test_recommendations_weight_interests_and_best_lab_results(self):
        self.user.interests = ["programming", "design", "web development"]
        self.user.save()
        untested = self.client.get("/api/recommendations/").json()
        self.assertEqual(untested[0]["career_slug"], "angular")
        self.assertEqual(untested[0]["score"], 60)
        self.assertEqual(untested[0]["performance"], 0)
        self.assertFalse(untested[0]["tested"])
        attempt, _ = self.start()
        self.submit(attempt)
        attempt, _ = self.start()
        self.submit(attempt)
        recommendations = self.client.get("/api/recommendations/").json()
        self.assertEqual(set(recommendations[0]), {"career_slug", "career_title", "score", "tested", "performance", "shared_interests"})
        self.assertEqual(recommendations[0]["score"], 100)
        self.assertEqual(recommendations[0]["performance"], 100)
        self.assertTrue(recommendations[0]["tested"])
        self.assertEqual(recommendations[0]["shared_interests"], ["design", "programming", "web development"])

    def test_recommendations_use_career_denominator_and_flutter_rounding(self):
        self.user.interests = ["Programming", "Web"]
        self.user.save()
        angular = next(
            item for item in self.client.get("/api/recommendations/").json()
            if item["career_slug"] == "angular"
        )
        self.assertEqual(angular["shared_interests"], ["programming"])
        self.assertEqual(angular["score"], 20)
        attempt, _ = self.start()
        self.submit(attempt)
        for interests in [
            ["Programming", "Web"],
            ["Programming", "Web", "unrelated", "another unrelated interest"],
        ]:
            self.user.interests = interests
            self.user.save()
            angular = next(
                item for item in self.client.get("/api/recommendations/").json()
                if item["career_slug"] == "angular"
            )
            self.assertEqual(angular["performance"], 100)
            self.assertEqual(angular["score"], 83)
            self.assertEqual(angular["shared_interests"], ["programming"])
        self.user.interests = ["Programming", "Design"]
        self.user.save()
        angular = next(
            item for item in self.client.get("/api/recommendations/").json()
            if item["career_slug"] == "angular"
        )
        self.assertEqual(angular["score"], 92)
        Career.objects.filter(slug="angular").update(interests=[])
        angular = next(
            item for item in self.client.get("/api/recommendations/").json()
            if item["career_slug"] == "angular"
        )
        self.assertEqual(angular["score"], 75)
        self.assertEqual(angular["shared_interests"], [])

    def test_quiz_and_completion_posts_require_csrf(self):
        secure = APIClient(enforce_csrf_checks=True)
        secure.force_login(self.user)
        secure.get("/api/csrf/")
        token = secure.cookies["csrftoken"].value
        for url in [f"/api/labs/{self.lab.id}/start/", f"/api/courses/{self.lab.course.id}/complete/"]:
            self.assertEqual(secure.post(url, {}, format="json").status_code, 403)
            self.assertIn(secure.post(url, {}, format="json", HTTP_X_CSRFTOKEN=token).status_code, [200, 201])
        attempt = Attempt.objects.get()
        url = f"/api/attempts/{attempt.id}/submit/"
        self.assertEqual(secure.post(url, self.answers(attempt), format="json").status_code, 403)
        self.assertEqual(secure.post(url, self.answers(attempt), format="json", HTTP_X_CSRFTOKEN=token).status_code, 201)

    def test_not_found_errors(self):
        for url in ["/api/careers/missing/", "/api/courses/9999/", "/api/results/9999/"]:
            self.assertEqual(self.client.get(url).status_code, 404)
        for url in ["/api/labs/9999/start/", "/api/courses/9999/complete/", "/api/attempts/9999/submit/"]:
            self.assertEqual(self.client.post(url, {}, format="json").status_code, 404)

    def test_admin_all_models_registered_and_student_denied(self):
        for model in [User, Career, Lab, Course, Question, Option, CourseCompletion, Attempt, Result]:
            self.assertTrue(admin.site.is_registered(model))
        self.assertEqual(self.client.get("/admin/academy/career/").status_code, 302)
        user = User.objects.create_superuser("admin@example.com", PASSWORD, name="Admin")
        self.client.force_login(user)
        for url in ["/admin/academy/user/add/", f"/admin/academy/question/{Question.objects.first().id}/change/"]:
            self.assertEqual(self.client.get(url).status_code, 200)
