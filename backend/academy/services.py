from collections import defaultdict
from django.core.exceptions import ValidationError as ModelValidationError

from rest_framework.exceptions import ValidationError
from .models import Result

SNAPSHOT_VERSION = 1


def lab_results(user, **filters):
    if not user.is_authenticated:
        return {}
    grouped = defaultdict(list)
    results = Result.objects.filter(attempt__user=user, **filters).select_related("attempt").order_by("-completed_at", "-id")
    for result in results:
        grouped[result.attempt.lab_id].append({
            "id": result.id, "score": result.score, "passed": result.passed,
            "correct": result.correct, "total": result.total,
            "completed_at": result.completed_at.isoformat(),
        })
    return grouped


def snapshot_lab(lab):
    questions = []
    for question in lab.questions.prefetch_related("options").all():
        try:
            question.clean()
        except ModelValidationError as error:
            raise ValidationError({"detail": "This lab has invalid workshop configuration."}) from error
        options = [
            {"id": option.id, "text": option.text, "correct": option.correct}
            for option in question.options.all()
        ]
        correct_count = sum(option["correct"] for option in options)
        if len(options) < 2 or correct_count < 1 or (
            not question.multiple and correct_count != 1
        ):
            raise ValidationError({"detail": "This lab has invalid answer configuration."})
        questions.append({
            "id": question.id,
            "prompt": question.prompt,
            "multiple": question.multiple,
            "skill": question.skill,
            "explanation": question.explanation,
            "options": options,
            "kind": question.kind,
            "workspace": question.workspace,
        })
    if not questions:
        raise ValidationError({"detail": "This lab has no questions."})
    return {
        "lab_id": lab.id,
        "lab_title": lab.title,
        "career_title": lab.career.title,
        "career_slug": lab.career.slug,
        "expected_seconds": lab.expected_seconds,
        "scenario": lab.scenario,
        "objectives": lab.objectives,
        "is_premium": lab.is_premium,
        "questions": questions,
    }


def public_attempt(attempt):
    snapshot = attempt.snapshot
    return {
        "id": attempt.id,
        "lab_title": snapshot["lab_title"],
        "career_title": snapshot["career_title"],
        "questions": [
            {
                "id": question["id"],
                "prompt": question["prompt"],
                "multiple": question["multiple"],
                "kind": question.get("kind", "quiz"),
                "workspace": question.get("workspace", {}),
                "options": [
                    {"id": option["id"], "text": option["text"]}
                    for option in question["options"] if question.get("kind", "quiz") != "code"
                ],
            }
            for question in snapshot["questions"]
        ],
        "expected_seconds": snapshot["expected_seconds"],
        "scenario": snapshot.get("scenario", ""),
        "objectives": snapshot.get("objectives", []),
        "is_premium": snapshot.get("is_premium", False),
    }


def grade(snapshot, answers, duration_seconds):
    by_question = {}
    code_answers = {}
    for answer in answers:
        question_id = answer["question_id"]
        if question_id in by_question:
            raise ValidationError({"answers": "Duplicate question_id."})
        option_ids = answer["option_ids"]
        if len(option_ids) != len(set(option_ids)):
            raise ValidationError({"answers": "Duplicate option_ids."})
        by_question[question_id] = set(option_ids)
        if "code_text" in answer:
            code_answers[question_id] = answer["code_text"]
    questions = snapshot["questions"]
    if set(by_question) != {question["id"] for question in questions}:
        raise ValidationError({"answers": "Provide exactly one answer for every question in this attempt."})
    correct = 0
    feedback = []
    skill_totals = defaultdict(lambda: [0, 0])
    for question in questions:
        selected = by_question[question["id"]]
        allowed = {option["id"] for option in question["options"]}
        if not selected.issubset(allowed):
            raise ValidationError({"answers": "An option does not belong to its question."})
        if not question["multiple"] and len(selected) > 1:
            raise ValidationError({"answers": "Single-choice questions accept at most one option."})
        expected = {option["id"] for option in question["options"] if option["correct"]}
        if question.get("kind", "quiz") == "code":
            if selected or question["id"] not in code_answers:
                raise ValidationError({"answers": "Code tasks require code_text and empty option_ids."})
            typed = code_answers[question["id"]]
            is_correct = typed.strip() in {
                option["text"].strip() for option in question["options"] if option["correct"]
            }
            selected_texts = [typed]
        else:
            if question["id"] in code_answers:
                raise ValidationError({"answers": "code_text is only valid for code tasks."})
            is_correct = selected == expected
            selected_texts = [option["text"] for option in question["options"] if option["id"] in selected]
        correct += int(is_correct)
        skill_totals[question["skill"]][0] += int(is_correct)
        skill_totals[question["skill"]][1] += 1
        feedback.append({
            "prompt": question["prompt"],
            "correct": is_correct,
            "explanation": question["explanation"],
            "selected_options": selected_texts,
            "correct_options": [option["text"] for option in question["options"] if option["id"] in expected],
            "kind": question.get("kind", "quiz"),
            "workspace": question.get("workspace", {}),
        })
    expected_seconds = max(1, snapshot["expected_seconds"])
    time_score = round(100 * max(0, min(1, 2 - duration_seconds / expected_seconds)), 2)
    score = round(80 * correct / len(questions) + 0.2 * time_score, 2)
    return {
        "career_title": snapshot["career_title"],
        "career_slug": snapshot["career_slug"],
        "lab_title": snapshot["lab_title"],
        "correct": correct,
        "total": len(questions),
        "score": score,
        "time_score": time_score,
        "duration_seconds": duration_seconds,
        "passed": score >= 70,
        "skills": {skill: round(100 * hits / total, 2) for skill, (hits, total) in skill_totals.items()},
        "feedback": feedback,
    }
