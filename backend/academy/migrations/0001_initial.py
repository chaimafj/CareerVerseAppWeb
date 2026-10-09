import academy.models
import django.core.validators
import django.db.models.deletion
import django.db.models.functions.text
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [("auth", "0012_alter_user_first_name_max_length")]
    operations = [
        migrations.CreateModel(
            name="Career",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(unique=True)),
                ("title", models.CharField(max_length=150)),
                ("summary", models.CharField(max_length=400)),
                ("description", models.TextField()),
                ("category", models.CharField(max_length=100)),
                ("tools", models.JSONField(default=list)),
                ("interests", models.JSONField(default=list)),
                ("salary", models.CharField(max_length=200)),
                ("education", models.CharField(max_length=300)),
                ("outlook", models.CharField(max_length=300)),
            ],
            options={"ordering": ["title"]},
        ),
        migrations.CreateModel(
            name="User",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                ("is_superuser", models.BooleanField(default=False, help_text="Designates that this user has all permissions without explicitly assigning them.", verbose_name="superuser status")),
                ("first_name", models.CharField(blank=True, max_length=150, verbose_name="first name")),
                ("last_name", models.CharField(blank=True, max_length=150, verbose_name="last name")),
                ("is_staff", models.BooleanField(default=False, help_text="Designates whether the user can log into this admin site.", verbose_name="staff status")),
                ("is_active", models.BooleanField(default=True, help_text="Designates whether this user should be treated as active. Unselect this instead of deleting accounts.", verbose_name="active")),
                ("date_joined", models.DateTimeField(default=django.utils.timezone.now, verbose_name="date joined")),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("name", models.CharField(max_length=150)),
                ("interests", models.JSONField(blank=True, default=list)),
                ("university", models.CharField(blank=True, max_length=200)),
                ("specialty", models.CharField(blank=True, max_length=200)),
                ("study_level", models.CharField(blank=True, max_length=100)),
                ("bio", models.TextField(blank=True, max_length=2000)),
                ("groups", models.ManyToManyField(blank=True, help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.", related_name="user_set", related_query_name="user", to="auth.group", verbose_name="groups")),
                ("user_permissions", models.ManyToManyField(blank=True, help_text="Specific permissions for this user.", related_name="user_set", related_query_name="user", to="auth.permission", verbose_name="user permissions")),
            ],
            managers=[("objects", academy.models.UserManager())],
        ),
        migrations.CreateModel(
            name="Lab",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=150)),
                ("level", models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(3)])),
                ("expected_seconds", models.PositiveIntegerField(default=180, validators=[django.core.validators.MinValueValidator(1)])),
                ("career", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="labs", to="academy.career")),
            ],
            options={"ordering": ["career_id", "level", "id"]},
        ),
        migrations.CreateModel(
            name="Course",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=150)),
                ("intro", models.TextField()),
                ("lessons", models.JSONField(default=list, help_text="List of {title, body, example} objects.")),
                ("career", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="courses", to="academy.career")),
                ("lab", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="course", to="academy.lab")),
            ],
            options={"ordering": ["lab__level", "id"]},
        ),
        migrations.CreateModel(
            name="CourseCompletion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("completed_at", models.DateTimeField(auto_now_add=True)),
                ("course", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="completions", to="academy.course")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="course_completions", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="Attempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("schema_version", models.PositiveSmallIntegerField(default=1, editable=False)),
                ("snapshot", models.JSONField(editable=False)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("submitted_at", models.DateTimeField(blank=True, editable=False, null=True)),
                ("lab", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="attempts", to="academy.lab")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attempts", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="Question",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("position", models.PositiveSmallIntegerField()),
                ("prompt", models.TextField()),
                ("multiple", models.BooleanField(default=False)),
                ("explanation", models.TextField()),
                ("skill", models.CharField(max_length=100)),
                ("lab", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="questions", to="academy.lab")),
            ],
            options={"ordering": ["position", "id"]},
        ),
        migrations.CreateModel(
            name="Option",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("position", models.PositiveSmallIntegerField()),
                ("text", models.TextField()),
                ("correct", models.BooleanField(default=False)),
                ("question", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="options", to="academy.question")),
            ],
            options={"ordering": ["position", "id"]},
        ),
        migrations.CreateModel(
            name="Result",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("career_title", models.CharField(max_length=150)),
                ("career_slug", models.SlugField()),
                ("lab_title", models.CharField(max_length=150)),
                ("correct", models.PositiveSmallIntegerField()),
                ("total", models.PositiveSmallIntegerField()),
                ("score", models.FloatField()),
                ("time_score", models.FloatField()),
                ("duration_seconds", models.PositiveIntegerField()),
                ("passed", models.BooleanField()),
                ("skills", models.JSONField()),
                ("feedback", models.JSONField()),
                ("completed_at", models.DateTimeField(auto_now_add=True)),
                ("attempt", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="result", to="academy.attempt")),
            ],
            options={"ordering": ["-completed_at", "-id"]},
        ),
        migrations.AddConstraint(model_name="user", constraint=models.UniqueConstraint(django.db.models.functions.text.Lower("email"), name="unique_email_case_insensitive")),
        migrations.AddConstraint(model_name="lab", constraint=models.UniqueConstraint(fields=("career", "level"), name="one_lab_per_career_level")),
        migrations.AddConstraint(model_name="lab", constraint=models.CheckConstraint(condition=models.Q(expected_seconds__gte=1), name="positive_lab_time")),
        migrations.AddConstraint(model_name="lab", constraint=models.CheckConstraint(condition=models.Q(level__gte=1, level__lte=3), name="valid_lab_level")),
        migrations.AddConstraint(model_name="coursecompletion", constraint=models.UniqueConstraint(fields=("user", "course"), name="unique_course_completion")),
        migrations.AddConstraint(model_name="question", constraint=models.UniqueConstraint(fields=("lab", "position"), name="unique_question_position")),
        migrations.AddConstraint(model_name="option", constraint=models.UniqueConstraint(fields=("question", "position"), name="unique_option_position")),
    ]
