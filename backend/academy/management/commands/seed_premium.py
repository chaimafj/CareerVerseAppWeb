from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from academy.models import Career, Course, Lab, Option, Question
from academy.premium_workshops import PREMIUM_LABS
from academy.extended_premium import PREMIUM_LABS as EXTENDED_PREMIUM_LABS


class Command(BaseCommand):
    help = "Upsert Premium simulations for seeded careers without changing free labs or historical attempts."

    @transaction.atomic
    def handle(self, *args, **options):
        seeded = 0
        skipped = []
        for data in [*PREMIUM_LABS, *EXTENDED_PREMIUM_LABS]:
            try:
                career = Career.objects.get(slug=data["career"])
            except Career.DoesNotExist as exc:
                if data in EXTENDED_PREMIUM_LABS:
                    skipped.append(data["career"])
                    continue
                raise CommandError("Run seed_demo before seed_premium.") from exc
            lab, _ = Lab.objects.update_or_create(
                career=career, level=3, is_premium=True,
                defaults={"title": data["title"], "scenario": data["scenario"],
                          "objectives": data["objectives"], "expected_seconds": 600},
            )
            lessons = []
            for position, task in enumerate(data["questions"], 1):
                texts, correct = task["options"], task["correct"]
                skill, explanation, example = task["skill"], task["explanation"], task["example"]
                question, _ = Question.objects.update_or_create(
                    lab=lab, position=position,
                    defaults={"prompt": task["prompt"], "multiple": len(correct) > 1,
                              "skill": skill, "explanation": explanation,
                              "kind": task["kind"], "workspace": task["workspace"]},
                )
                for option_position, text in enumerate(texts, 1):
                    Option.objects.update_or_create(
                        question=question, position=option_position,
                        defaults={"text": text, "correct": option_position - 1 in correct},
                    )
                question.options.filter(position__gt=len(texts)).delete()
                lessons.append({"title": skill.title(), "body": explanation, "example": example})
            lab.questions.filter(position__gt=len(data["questions"])).delete()
            Course.objects.update_or_create(
                lab=lab, defaults={"career": career, "title": data["title"],
                                  "intro": data["scenario"], "lessons": lessons},
            )
            seeded += 1
        self.stdout.write(self.style.SUCCESS(
            f"Seeded {seeded} Premium simulations, {seeded} courses and {seeded * 5} interactive tasks."
        ))
        if skipped:
            self.stdout.write(self.style.WARNING(
                "Extended careers not installed: " + ", ".join(skipped)
                + ". Run seed_extended then seed_premium for all nine simulations."
            ))
