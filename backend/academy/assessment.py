from decimal import Decimal, ROUND_HALF_UP

from .models import Course, CourseCompletion, Lab, Result


def career_assessment(user, career):
    labs = list(Lab.objects.filter(career=career, is_premium=False).order_by("level", "id"))
    best = {}
    if user.is_authenticated:
        results = Result.objects.filter(attempt__user=user, attempt__lab__in=labs).select_related("attempt")
        for result in results.order_by("-score", "-completed_at", "-id"):
            best.setdefault(result.attempt.lab_id, result)
    complete = bool(labs) and len(best) == len(labs)
    mean = sum((Decimal(str(result.score)) for result in best.values()), Decimal(0)) / len(labs) if complete else None
    final_score = mean.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if mean is not None else None
    needs_improvement = final_score is not None and final_score < Decimal("60")
    completed_courses = set(
        CourseCompletion.objects.filter(user=user, course__career=career).values_list("course_id", flat=True)
    ) if user.is_authenticated else set()
    courses = {course.lab_id: course for course in Course.objects.filter(lab__in=labs)}
    path = []
    if needs_improvement:
        for lab in sorted(labs, key=lambda lab: (best[lab.id].score, lab.level, lab.id)):
            result = best[lab.id]
            weak_skills = [skill for skill, score in result.skills.items() if score < 60]
            if result.score < 60 or weak_skills:
                course = courses.get(lab.id)
                path.append({
                    "lab_id": lab.id, "lab_title": lab.title, "best_score": result.score,
                    "result_id": result.id, "weak_skills": weak_skills,
                    "course_id": course.id if course else None,
                    "course_title": course.title if course else None,
                    "course_completed": bool(course and course.id in completed_courses),
                })
    return {
        "career_slug": career.slug, "career_title": career.title,
        "completed_labs": len(best), "required_labs": len(labs), "complete": complete,
        "final_score": float(final_score) if final_score is not None else None,
        "needs_improvement": needs_improvement, "learning_path": path,
    }
