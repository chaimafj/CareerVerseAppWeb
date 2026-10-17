from django.core.management.base import BaseCommand
from django.db import transaction

from academy.demo_data import CAREERS, MISSIONS
from academy.models import Career, Course, Lab, Option, Question


class Command(BaseCommand):
    help = "Upsert three demo careers, nine courses/labs and 27 questions. Does not create users."
    careers = CAREERS
    missions = MISSIONS

    @transaction.atomic
    def handle(self, *args, **options):
        for data in self.careers:
            fields = {key: value for key, value in data.items() if key not in ("slug", "levels")}
            career, _ = Career.objects.update_or_create(slug=data["slug"], defaults=fields)
            for level, (title, questions) in enumerate(data["levels"], start=1):
                lab, _ = Lab.objects.update_or_create(
                    career=career, level=level, is_premium=False,
                    defaults={
                        "title": title, "expected_seconds": 180 + (level - 1) * 60,
                        "scenario": self.missions[career.slug][level - 1],
                        "objectives": [f"Practice {skill} in the mission"
                                       for skill in dict.fromkeys(question[3] for question in questions)],
                    },
                )
                lessons = []
                for position, (prompt, texts, correct, skill, explanation, example) in enumerate(questions, start=1):
                    question, _ = Question.objects.update_or_create(
                        lab=lab, position=position,
                        defaults={
                            "prompt": prompt, "multiple": len(correct) > 1,
                            "skill": skill, "explanation": explanation,
                            "kind": "quiz", "workspace": {},
                        },
                    )
                    for option_position, text in enumerate(texts, start=1):
                        Option.objects.update_or_create(
                            question=question, position=option_position,
                            defaults={"text": text, "correct": option_position - 1 in correct},
                        )
                    question.options.filter(position__gt=len(texts)).delete()
                    lessons.append({"title": skill.title(), "body": explanation, "example": example})
                lab.questions.filter(position__gt=len(questions)).delete()
                Course.objects.update_or_create(
                    lab=lab,
                    defaults={
                        "career": career, "title": f"{career.title}: {title}",
                        "intro": f"Level {level}: learn {title.lower()} before practicing in the linked lab.",
                        "lessons": lessons,
                    },
                )
        lab_count = sum(len(data["levels"]) for data in self.careers)
        question_count = sum(len(questions) for data in self.careers for _, questions in data["levels"])
        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(self.careers)} careers, {lab_count} courses/labs and {question_count} questions; no users created."
        ))
