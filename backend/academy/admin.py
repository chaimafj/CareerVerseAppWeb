from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Attempt, Career, Course, CourseCompletion, Lab, Option, Question, Result, User


@admin.register(User)
class StudentAdmin(UserAdmin):
    ordering = ["email"]
    list_display = ["email", "name", "is_staff", "is_active"]
    search_fields = ["email", "name"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("name", "interests", "university", "specialty", "study_level", "bio")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "name", "password1", "password2")}),)


class LabInline(admin.TabularInline):
    model = Lab
    extra = 0
    show_change_link = True


class CourseInline(admin.StackedInline):
    model = Course
    extra = 0
    show_change_link = True


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 0
    show_change_link = True


class OptionInline(admin.TabularInline):
    model = Option
    extra = 2


@admin.register(Career)
class CareerAdmin(admin.ModelAdmin):
    list_display = ["title", "slug", "category"]
    search_fields = ["title", "description"]
    prepopulated_fields = {"slug": ("title",)}
    inlines = [LabInline, CourseInline]


@admin.register(Lab)
class LabAdmin(admin.ModelAdmin):
    list_display = ["title", "career", "level", "is_premium", "expected_seconds"]
    list_filter = ["career", "level", "is_premium"]
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ["prompt", "lab", "position", "kind", "multiple", "skill"]
    list_filter = ["lab__career", "kind", "multiple"]
    search_fields = ["prompt", "skill"]
    inlines = [OptionInline]


@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    list_display = ["text", "question", "correct"]
    list_filter = ["correct"]
    search_fields = ["text", "question__prompt"]


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ["title", "career", "lab"]
    list_filter = ["career"]


@admin.register(CourseCompletion)
class CompletionAdmin(admin.ModelAdmin):
    list_display = ["user", "course", "completed_at"]
    readonly_fields = ["completed_at"]
    list_filter = ["course__career"]
    autocomplete_fields = ["user"]


class HistoricalAdmin(admin.ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Attempt)
class AttemptAdmin(HistoricalAdmin):
    list_display = ["id", "user", "lab", "schema_version", "started_at", "submitted_at"]
    list_filter = ["schema_version", "lab__career"]
    search_fields = ["user__email"]


@admin.register(Result)
class ResultAdmin(HistoricalAdmin):
    list_display = ["id", "career_title", "lab_title", "score", "passed", "completed_at"]
    list_filter = ["career_slug", "passed"]
    search_fields = ["attempt__user__email", "lab_title"]
