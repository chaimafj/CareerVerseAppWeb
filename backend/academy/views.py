from collections import defaultdict
from math import floor

from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError, transaction
from django.db.models import Avg, Max
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_GET
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Attempt, Career, Course, CourseCompletion, Lab, Result, User
from .serializers import (
    CareerSerializer, CourseSerializer, LoginSerializer, ProfileSerializer,
    RegisterSerializer, ResultSerializer, SubmitSerializer,
)
from .services import SNAPSHOT_VERSION, grade, lab_results, public_attempt, snapshot_lab
from .access import premium_active, require_lab_access
from .push import enqueue_notification, welcome_once
from .careernet import CareerNet


def welcome_language(request):
    language = request.headers.get("Accept-Language", "en").split(",")[0].split(";")[0].strip().lower().split("-")[0]
    return language if language in ("en", "fr", "ar") else "en"


def csrf_failure(request, reason=""):
    return JsonResponse({"detail": "CSRF verification failed."}, status=403)


@ensure_csrf_cookie
@require_GET
def csrf(request):
    return JsonResponse({"detail": "CSRF cookie set."})


@method_decorator(csrf_protect, name="dispatch")
class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                user = User.objects.create_user(**serializer.validated_data)
                welcome_once(user, welcome_language(request))
        except IntegrityError:
            if User.objects.filter(email__iexact=serializer.validated_data["email"]).exists():
                raise ValidationError({"email": "An account with this email already exists."})
            raise
        login(request, user)
        return Response(ProfileSerializer(user).data, status=status.HTTP_201_CREATED)


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            email=serializer.validated_data["email"].strip().lower(),
            password=serializer.validated_data["password"],
        )
        if user is None:
            return Response({"detail": "Invalid email or password."}, status=400)
        welcome_once(user, welcome_language(request))
        login(request, user)
        return Response(ProfileSerializer(user).data)


@method_decorator(csrf_protect, name="dispatch")
class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response({"detail": "Logged out."})


class MeView(APIView):
    def get(self, request):
        return Response(ProfileSerializer(request.user).data)

    def patch(self, request):
        serializer = ProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class CareerListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(CareerSerializer(Career.objects.all(), many=True).data)


class CareerDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        career = get_object_or_404(Career, slug=slug)
        completed = set()
        best = {}
        history = lab_results(request.user, attempt__lab__career=career)
        if request.user.is_authenticated:
            completed = set(
                CourseCompletion.objects.filter(user=request.user, course__career=career)
                .values_list("course_id", flat=True)
            )
            best = dict(
                Result.objects.filter(attempt__user=request.user, attempt__lab__career=career)
                .values("attempt__lab_id")
                .annotate(best=Max("score"))
                .values_list("attempt__lab_id", "best")
            )
        data = CareerSerializer(career).data
        from .assessment import career_assessment
        data["assessment"] = career_assessment(request.user, career)
        data["courses"] = [
            {"id": course.id, "title": course.title, "completed": course.id in completed, "lab_id": course.lab_id,
             "is_premium": course.lab.is_premium, "locked": course.lab.is_premium and not premium_active(request.user)}
            for course in career.courses.select_related("lab").all()
        ]
        data["labs"] = [
            {
                "id": lab.id, "title": lab.title, "level": lab.get_level_display(),
                "question_count": lab.questions.count(), "best_score": best.get(lab.id),
                "is_premium": lab.is_premium, "locked": lab.is_premium and not premium_active(request.user),
                "scenario": lab.scenario, "objectives": lab.objectives, "expected_seconds": lab.expected_seconds,
                "completed": bool(history.get(lab.id)), "attempt_count": len(history.get(lab.id, [])),
                "latest_result": history.get(lab.id, [None])[0],
            }
            for lab in career.labs.prefetch_related("questions").all()
        ]
        return Response(data)


class CareerAssessmentView(APIView):
    def get(self, request, slug):
        from .assessment import career_assessment
        career = get_object_or_404(Career, slug=slug)
        return Response(career_assessment(request.user, career))


class CareerAssessmentListView(APIView):
    def get(self, request):
        from .assessment import career_assessment
        return Response([career_assessment(request.user, career) for career in Career.objects.all()])


class CourseView(APIView):
    def get(self, request, pk):
        course = get_object_or_404(Course.objects.select_related("career", "lab"), pk=pk)
        require_lab_access(request.user, course.lab)
        data = CourseSerializer(course).data
        data["completed"] = CourseCompletion.objects.filter(user=request.user, course=course).exists()
        return Response(data)


class CourseListView(APIView):
    def get(self, request):
        completed = set(CourseCompletion.objects.filter(user=request.user).values_list("course_id", flat=True))
        premium = premium_active(request.user)
        return Response([
            {
                "id": course.id, "title": course.title, "career_slug": course.career.slug,
                "career_title": course.career.title, "completed": course.id in completed,
                "is_premium": course.lab.is_premium, "locked": course.lab.is_premium and not premium,
            }
            for course in Course.objects.select_related("career", "lab").all()
        ])


class LabListView(APIView):
    def get(self, request):
        history = lab_results(request.user)
        premium = premium_active(request.user)
        return Response([
            {
                "id": lab.id, "title": lab.title, "career_slug": lab.career.slug,
                "career_title": lab.career.title, "level": lab.get_level_display(),
                "scenario": lab.scenario, "question_count": lab.questions.count(),
                "expected_seconds": lab.expected_seconds, "is_premium": lab.is_premium,
                "locked": lab.is_premium and not premium, "completed": bool(history.get(lab.id)),
                "attempt_count": len(history.get(lab.id, [])), "latest_result": history.get(lab.id, [None])[0],
            }
            for lab in Lab.objects.select_related("career").prefetch_related("questions").all()
        ])


class CompleteCourseView(APIView):
    def post(self, request, pk):
        course = get_object_or_404(Course, pk=pk)
        require_lab_access(request.user, course.lab)
        CourseCompletion.objects.get_or_create(user=request.user, course=course)
        return Response({"id": course.id, "completed": True})


class StartLabView(APIView):
    def post(self, request, pk):
        lab = get_object_or_404(Lab.objects.select_related("career"), pk=pk)
        require_lab_access(request.user, lab)
        snapshot = snapshot_lab(lab)
        attempt = Attempt.objects.create(
            user=request.user, lab=lab, snapshot=snapshot, schema_version=SNAPSHOT_VERSION
        )
        return Response(public_attempt(attempt), status=201)


class LabDetailView(APIView):
    def get(self, request, pk):
        lab = get_object_or_404(Lab.objects.select_related("career"), pk=pk)
        history = lab_results(request.user, attempt__lab=lab).get(lab.id, [])
        return Response({
            "id": lab.id, "title": lab.title, "career_title": lab.career.title,
            "career_slug": lab.career.slug, "level": lab.get_level_display(),
            "is_premium": lab.is_premium, "locked": lab.is_premium and not premium_active(request.user),
            "scenario": lab.scenario, "objectives": lab.objectives,
            "expected_seconds": lab.expected_seconds, "question_count": lab.questions.count(),
            "completed": bool(history), "attempt_count": len(history),
            "latest_result": history[0] if history else None, "results": history,
        })


class SubmitAttemptView(APIView):
    def post(self, request, pk):
        with transaction.atomic():
            attempt = get_object_or_404(
                Attempt.objects.select_for_update().filter(user=request.user), pk=pk
            )
            if attempt.submitted_at:
                return Response({"detail": "This attempt has already been submitted."}, status=409)
            if attempt.schema_version != SNAPSHOT_VERSION:
                return Response({"detail": "Unsupported attempt snapshot version."}, status=409)
            serializer = SubmitSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            submitted_at = timezone.now()
            elapsed = max(0, int((submitted_at - attempt.started_at).total_seconds()))
            graded = grade(attempt.snapshot, serializer.validated_data["answers"], elapsed)
            # Conditional claim also guards replay where row locks are unavailable.
            claimed = Attempt.objects.filter(pk=pk, submitted_at__isnull=True).update(
                submitted_at=submitted_at
            )
            if not claimed:
                return Response({"detail": "This attempt has already been submitted."}, status=409)
            result = Result.objects.create(attempt=attempt, **graded)
            enqueue_notification(request.user, "lab", f"/results/{result.pk}")
        return Response(ResultSerializer(result).data, status=201)


class ResultView(APIView):
    def get(self, request, pk):
        result = get_object_or_404(Result.objects.select_related("attempt").filter(attempt__user=request.user), pk=pk)
        return Response(ResultSerializer(result).data)


class ProgressView(APIView):
    def get(self, request):
        results = Result.objects.filter(attempt__user=request.user)
        return Response({
            "completed_labs": results.filter(attempt__lab__isnull=False)
            .values("attempt__lab_id").distinct().count(),
            "total_labs": Lab.objects.count(),
            "average_score": round(results.aggregate(value=Avg("score"))["value"] or 0, 2),
            "completed_courses": CourseCompletion.objects.filter(user=request.user).count(),
            "results": [
                {
                    "id": result.id, "career_title": result.career_title,
                    "lab_title": result.lab_title, "score": result.score,
                    "completed_at": result.completed_at.isoformat(),
                }
                for result in results
            ],
        })


class RecommendationsView(APIView):
    def get(self, request):
        best = defaultdict(dict)
        for result in Result.objects.filter(attempt__user=request.user).select_related("attempt"):
            slug = result.career_slug
            lab_id = result.attempt.snapshot["lab_id"]
            best[slug][lab_id] = max(best[slug].get(lab_id, 0), result.score)

        user_interests = request.user.interests or []
        model = CareerNet()
        recommendations = []
        for career in Career.objects.all():
            career_interests = career.interests or []
            shared = sorted({value.strip().lower() for value in user_interests if isinstance(value, str)} &
                            {value.strip().lower() for value in career_interests if isinstance(value, str)})
            interest_score = model.score(user_interests, career_interests)
            scores = list(best[career.slug].values())
            performance = round(sum(scores) / len(scores), 2) if scores else 0
            match_score = (
                0.75 * performance + 0.25 * interest_score
                if scores else 0.6 * interest_score
            )
            recommendations.append({
                "career_slug": career.slug, "career_title": career.title,
                "score": floor(match_score + 0.5),
                "tested": bool(scores), "performance": performance, "shared_interests": shared,
            })
        recommendations.sort(key=lambda item: (-item["score"], item["career_slug"]))
        return Response(recommendations)
