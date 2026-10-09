from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import Attempt, ChatExchange, Course, CourseCompletion, Result, User


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ChatTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)
        cls.user = User.objects.create_user("chat@example.test", "Test-only-932!", name="Chat")
        cls.other = User.objects.create_user("other@example.test", "Test-only-932!", name="Other")

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def send(self, message):
        return self.client.post("/api/chat/", {"message": message}, format="json")

    def test_anonymous_cannot_read_send_or_delete(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/chat/").status_code, 403)
        self.assertEqual(self.send("hello").status_code, 403)
        self.assertEqual(self.client.delete("/api/chat/").status_code, 403)

    def test_validation_does_not_save_invalid_messages(self):
        for message in ["", "   ", "x" * 2001, ["hello"], None]:
            with self.subTest(message=type(message)):
                self.assertEqual(self.send(message).status_code, 400)
        self.assertEqual(ChatExchange.objects.count(), 0)

    def test_career_reply_and_followup_use_catalogue(self):
        response = self.send("Tell me about Angular")
        self.assertEqual(response.status_code, 201)
        self.assertIn("Angular Developer", response.json()["reply"])
        self.assertIn("/careers/angular", [a["path"] for a in response.json()["actions"]])
        self.assertTrue(any(a["path"].startswith("/courses/") for a in response.json()["actions"]))
        self.assertIn("Angular Developer", self.send("What tools should I learn?").json()["reply"])

    def test_personal_interests_and_empty_results(self):
        self.user.interests = ["Programming"]
        self.user.save()
        self.assertIn("Angular Developer", self.send("Help me choose a career").json()["reply"])
        self.assertIn("no completed labs", self.send("What do my scores mean?").json()["reply"])

    def test_saved_result_is_personal_and_course_suggestion_skips_completed(self):
        course = Course.objects.filter(career__slug="angular").first()
        CourseCompletion.objects.create(user=self.user, course=course)
        response = self.send("Angular").json()
        self.assertNotIn(f"/courses/{course.id}", [a["path"] for a in response["actions"]])
        for user, title in [(self.user, "My lab"), (self.other, "Private other lab")]:
            attempt = Attempt.objects.create(user=user, lab=course.lab, snapshot={})
            Result.objects.create(
                attempt=attempt, career_title="Angular Developer", career_slug="angular",
                lab_title=title, correct=2, total=3, score=73.33, time_score=100,
                duration_seconds=10, passed=True, skills={}, feedback=[],
            )
        response = self.send("Explain my results").json()
        self.assertIn("My lab", response["reply"])
        self.assertIn("73.33/100", response["reply"])
        self.assertNotIn("Private other lab", response["reply"])
        result = Result.objects.get(attempt__user=self.user)
        self.assertEqual(response["actions"][0]["path"], f"/results/{result.pk}")

    def test_history_is_ordered_private_and_clear_is_scoped(self):
        other = ChatExchange.objects.create(user=self.other, message="private", reply="private")
        first = self.send("hello").json()
        second = self.send("cloud").json()
        history = self.client.get("/api/chat/").json()
        self.assertEqual([item["id"] for item in history], [first["id"], second["id"]])
        self.assertEqual(self.client.delete("/api/chat/").status_code, 204)
        self.assertEqual(self.client.get("/api/chat/").json(), [])
        self.assertTrue(ChatExchange.objects.filter(pk=other.pk).exists())

    def test_retention_limit_and_unknown_topic(self):
        ChatExchange.objects.bulk_create([
            ChatExchange(user=self.user, message="hello", reply="hello") for _ in range(50)
        ])
        reply = self.send("a completely unrelated question").json()
        self.assertIn("could not match", reply["reply"])
        self.assertEqual(ChatExchange.objects.filter(user=self.user).count(), 50)
        self.assertEqual(len(self.client.get("/api/chat/").json()), 50)

    def test_session_requests_require_csrf_for_send_and_clear(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post("/api/chat/", {"message": "hello"}, format="json").status_code, 403)
        self.assertEqual(client.delete("/api/chat/").status_code, 403)
        client.get("/api/csrf/")
        token = client.cookies["csrftoken"].value
        self.assertEqual(client.post(
            "/api/chat/", {"message": "hello"}, format="json", HTTP_X_CSRFTOKEN=token
        ).status_code, 201)
        self.assertEqual(client.delete("/api/chat/", HTTP_X_CSRFTOKEN=token).status_code, 204)
