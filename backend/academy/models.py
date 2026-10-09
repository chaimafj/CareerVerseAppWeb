from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.functions import Lower


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        user = self.model(email=email.strip().lower(), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields["is_staff"] is not True or extra_fields["is_superuser"] is not True:
            raise ValueError("Superusers must have is_staff=True and is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=150)
    interests = models.JSONField(default=list, blank=True)
    university = models.CharField(max_length=200, blank=True)
    specialty = models.CharField(max_length=200, blank=True)
    study_level = models.CharField(max_length=100, blank=True)
    bio = models.TextField(max_length=2000, blank=True)
    premium_until = models.DateTimeField(null=True, blank=True)
    photo_data = models.BinaryField(null=True, blank=True, editable=False)
    photo_version = models.CharField(max_length=32, blank=True, editable=False)
    welcome_notified = models.BooleanField(default=False, editable=False)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]
    objects = UserManager()

    class Meta:
        constraints = [models.UniqueConstraint(Lower("email"), name="unique_email_case_insensitive")]

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email


class GoogleIdentity(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="google_identity")
    subject = models.CharField(max_length=255, unique=True)


class Career(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=150)
    summary = models.CharField(max_length=400)
    description = models.TextField()
    category = models.CharField(max_length=100)
    tools = models.JSONField(default=list)
    interests = models.JSONField(default=list)
    salary = models.CharField(max_length=200)
    education = models.CharField(max_length=300)
    outlook = models.CharField(max_length=300)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class Lab(models.Model):
    class Level(models.IntegerChoices):
        BEGINNER = 1, "Beginner"
        INTERMEDIATE = 2, "Intermediate"
        ADVANCED = 3, "Advanced"

    career = models.ForeignKey(Career, on_delete=models.CASCADE, related_name="labs")
    title = models.CharField(max_length=150)
    level = models.PositiveSmallIntegerField(
        choices=Level.choices, validators=[MinValueValidator(1), MaxValueValidator(3)]
    )
    expected_seconds = models.PositiveIntegerField(default=180, validators=[MinValueValidator(1)])
    is_premium = models.BooleanField(default=False)
    scenario = models.TextField(blank=True)
    objectives = models.JSONField(default=list, blank=True, help_text="List of non-empty mission objective strings.")

    def clean(self):
        from django.core.exceptions import ValidationError

        if not isinstance(self.objectives, list) or any(
            not isinstance(objective, str) or not objective.strip() for objective in self.objectives
        ):
            raise ValidationError({"objectives": "Use a list of non-empty objective strings."})

    class Meta:
        ordering = ["career_id", "level", "id"]
        constraints = [
            models.UniqueConstraint(fields=["career", "level", "is_premium"], name="one_lab_per_career_level_tier"),
            models.CheckConstraint(condition=models.Q(expected_seconds__gte=1), name="positive_lab_time"),
            models.CheckConstraint(condition=models.Q(level__gte=1, level__lte=3), name="valid_lab_level"),
        ]

    def __str__(self):
        return f"{self.career}: {self.title}"


class Course(models.Model):
    career = models.ForeignKey(Career, on_delete=models.CASCADE, related_name="courses")
    lab = models.OneToOneField(Lab, on_delete=models.CASCADE, related_name="course")
    title = models.CharField(max_length=150)
    intro = models.TextField()
    lessons = models.JSONField(default=list, help_text="List of {title, body, example} objects.")

    class Meta:
        ordering = ["lab__level", "id"]

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.lab_id and self.career_id != self.lab.career_id:
            raise ValidationError({"career": "The course and lab must belong to the same career."})
        if not isinstance(self.lessons, list) or any(
            not isinstance(lesson, dict)
            or set(lesson) != {"title", "body", "example"}
            or any(not isinstance(value, str) for value in lesson.values())
            for lesson in self.lessons
        ):
            raise ValidationError({"lessons": "Use a list of objects with string title, body and example."})

    def __str__(self):
        return self.title


class Question(models.Model):
    lab = models.ForeignKey(Lab, on_delete=models.CASCADE, related_name="questions")
    position = models.PositiveSmallIntegerField()
    prompt = models.TextField()
    multiple = models.BooleanField(default=False)
    explanation = models.TextField()
    skill = models.CharField(max_length=100)
    kind = models.CharField(max_length=16, default="quiz", choices=[
        ("quiz", "Quiz"), ("code", "Code repair"), ("architecture", "Architecture builder"),
        ("evidence", "Evidence analysis"),
    ])
    workspace = models.JSONField(default=dict, blank=True)

    def clean(self):
        from django.core.exceptions import ValidationError

        data = self.workspace
        valid = isinstance(data, dict)
        if valid and self.kind == "quiz":
            valid = not data
        elif valid and self.kind == "code":
            valid = set(data) == {"before", "after"} and all(isinstance(value, str) for value in data.values())
            valid = valid and not self.multiple
        elif valid and self.kind == "architecture":
            valid = (
                set(data) == {"nodes", "gap"} and isinstance(data["nodes"], list)
                and 2 <= len(data["nodes"]) <= 5
                and all(isinstance(node, str) for node in data["nodes"])
                and type(data["gap"]) is int and 0 <= data["gap"] < len(data["nodes"])
                and data["nodes"][data["gap"]] == "" and not self.multiple
            )
        elif valid and self.kind == "evidence":
            valid = set(data) == {"context"} and isinstance(data["context"], str)
        else:
            valid = False
        if not valid:
            raise ValidationError({"workspace": "Invalid workspace for this task type."})

    class Meta:
        ordering = ["position", "id"]
        constraints = [models.UniqueConstraint(fields=["lab", "position"], name="unique_question_position")]

    def __str__(self):
        return self.prompt[:100]


class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    position = models.PositiveSmallIntegerField()
    text = models.TextField()
    correct = models.BooleanField(default=False)

    class Meta:
        ordering = ["position", "id"]
        constraints = [
            models.UniqueConstraint(fields=["question", "position"], name="unique_option_position")
        ]

    def __str__(self):
        return self.text[:100]


class CourseCompletion(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="course_completions")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="completions")
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "course"], name="unique_course_completion")
        ]

    def __str__(self):
        return f"{self.user}: {self.course}"


class Attempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="attempts")
    lab = models.ForeignKey(Lab, on_delete=models.SET_NULL, null=True, related_name="attempts")
    schema_version = models.PositiveSmallIntegerField(default=1, editable=False)
    snapshot = models.JSONField(editable=False)
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True, editable=False)

    def __str__(self):
        return f"Attempt {self.pk}: {self.user}"


class Result(models.Model):
    attempt = models.OneToOneField(Attempt, on_delete=models.CASCADE, related_name="result")
    career_title = models.CharField(max_length=150)
    career_slug = models.SlugField()
    lab_title = models.CharField(max_length=150)
    correct = models.PositiveSmallIntegerField()
    total = models.PositiveSmallIntegerField()
    score = models.FloatField()
    time_score = models.FloatField()
    duration_seconds = models.PositiveIntegerField()
    passed = models.BooleanField()
    skills = models.JSONField()
    feedback = models.JSONField()
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-completed_at", "-id"]

    def __str__(self):
        return f"{self.career_title}: {self.score}"


class ChatExchange(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chat_exchanges")
    message = models.CharField(max_length=2000)
    reply = models.TextField()
    actions = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]


class PremiumCheckout(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="premium_checkouts")
    session_id = models.CharField(max_length=255, unique=True, null=True)
    price_id = models.CharField(max_length=255)
    amount = models.PositiveIntegerField()
    currency = models.CharField(max_length=3)
    paid_at = models.DateTimeField(null=True)
    event_id = models.CharField(max_length=255, unique=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class PushSubscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="push_subscriptions")
    endpoint = models.URLField(max_length=2048, unique=True)
    p256dh = models.CharField(max_length=100)
    auth = models.CharField(max_length=32)
    language = models.CharField(max_length=2, choices=[("en", "English"), ("fr", "French"), ("ar", "Arabic")])
    created_at = models.DateTimeField(auto_now_add=True)


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=200)
    body = models.CharField(max_length=500)
    path = models.CharField(max_length=300)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class PushDelivery(models.Model):
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name="deliveries")
    subscription = models.ForeignKey(PushSubscription, on_delete=models.CASCADE, related_name="deliveries")
    title = models.CharField(max_length=200)
    body = models.CharField(max_length=500)
    attempts = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField()
    sent_at = models.DateTimeField(null=True)
    failed = models.BooleanField(default=False)
    last_error = models.CharField(max_length=300, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["notification", "subscription"], name="unique_push_delivery")
        ]
