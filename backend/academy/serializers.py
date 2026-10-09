from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Career, Course, Result, User


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError({"non_field_errors": ["Expected a JSON object."]})
        unknown = set(data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError({key: "Unknown field." for key in sorted(unknown)})
        return super().to_internal_value(data)


class InterestsField(serializers.ListField):
    child = serializers.CharField(max_length=100, allow_blank=False)

    def __init__(self, **kwargs):
        super().__init__(max_length=30, **kwargs)

    def to_internal_value(self, data):
        if not isinstance(data, list) or any(not isinstance(item, str) for item in data):
            raise serializers.ValidationError("Expected a list of strings.")
        values = super().to_internal_value(data)
        return list(dict.fromkeys(value.strip().lower() for value in values))


class ProfileSerializer(serializers.ModelSerializer):
    interests = InterestsField(required=False)
    photo_url = serializers.SerializerMethodField()

    def get_photo_url(self, user):
        return f"/api/me/photo/?v={user.photo_version}" if user.photo_version else None

    class Meta:
        model = User
        fields = ["id", "email", "name", "interests", "university", "specialty", "study_level", "bio", "photo_url"]
        read_only_fields = ["id", "email", "photo_url"]
        extra_kwargs = {"name": {"allow_blank": False}}

    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError({"non_field_errors": ["Expected a JSON object."]})
        forbidden = set(data) - {"name", "interests", "university", "specialty", "study_level", "bio"}
        if forbidden:
            raise serializers.ValidationError({key: "Field is not writable." for key in sorted(forbidden)})
        return super().to_internal_value(data)


class RegisterSerializer(StrictSerializer):
    name = serializers.CharField(max_length=150)
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate(self, attrs):
        user = User(email=attrs["email"], name=attrs["name"])
        try:
            validate_password(attrs["password"], user)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password": error.messages}) from error
        return attrs


class LoginSerializer(StrictSerializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(trim_whitespace=False, max_length=128)


class ExactIntegerField(serializers.IntegerField):
    def to_internal_value(self, data):
        if type(data) is not int:
            raise serializers.ValidationError("Expected an integer.")
        return super().to_internal_value(data)


class AnswerSerializer(StrictSerializer):
    question_id = ExactIntegerField(min_value=1)
    option_ids = serializers.ListField(child=ExactIntegerField(min_value=1), max_length=100)
    code_text = serializers.CharField(required=False, allow_blank=True, max_length=500, trim_whitespace=False)


class SubmitSerializer(StrictSerializer):
    answers = AnswerSerializer(many=True, allow_empty=False)


class CareerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Career
        fields = [
            "slug", "title", "summary", "description", "category", "tools",
            "interests", "salary", "education", "outlook",
        ]


class CourseSerializer(serializers.ModelSerializer):
    career_slug = serializers.CharField(source="career.slug")

    class Meta:
        model = Course
        fields = ["id", "title", "intro", "lessons", "career_slug", "lab_id"]


class ResultSerializer(serializers.ModelSerializer):
    lab_id = serializers.IntegerField(source="attempt.lab_id", read_only=True, allow_null=True)
    feedback = serializers.SerializerMethodField()

    def get_feedback(self, result):
        questions = result.attempt.snapshot.get("questions", [])
        feedback = []
        for index, item in enumerate(result.feedback):
            entry = dict(item)
            if "correct_options" not in entry and index < len(questions):
                entry["correct_options"] = [
                    option["text"] for option in questions[index]["options"] if option["correct"]
                ]
            feedback.append(entry)
        return feedback

    class Meta:
        model = Result
        fields = [
            "id", "career_title", "career_slug", "lab_title", "correct", "total",
            "score", "time_score", "duration_seconds", "passed", "skills", "feedback", "lab_id",
        ]
