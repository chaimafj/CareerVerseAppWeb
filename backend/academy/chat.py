import re
import unicodedata

from .models import Career, ChatExchange, CourseCompletion, Result
from .access import premium_active


def normalized(text):
    return "".join(
        char for char in unicodedata.normalize("NFKD", text.lower())
        if not unicodedata.combining(char)
    )


def career_reply(user, message):
    """Use only published catalogue data and this student's saved progress."""
    words = set(re.findall(r"\w+", normalized(message)))
    careers = list(Career.objects.prefetch_related("courses__lab").all())
    matched = [
        career for career in careers
        if words & set(re.findall(r"\w+", normalized(
            f"{career.slug} {career.title} {' '.join(career.tools)}"
        ))) - {"developer", "engineer", "analyst"}
    ]
    if not matched and words & {"tools", "outils", "salary", "salaire", "course", "cours", "next", "suite"}:
        previous = ChatExchange.objects.filter(user=user).first()
        if previous:
            paths = {action["path"] for action in previous.actions}
            matched = [career for career in careers if f"/careers/{career.slug}" in paths]
    actions = []
    if not careers:
        return {
            "reply": "The career catalogue is empty. Please try again after an administrator adds content.",
            "actions": [],
        }
    if words & {"score", "scores", "result", "results", "resultat", "resultats", "progres", "progress"}:
        results = Result.objects.filter(attempt__user=user)
        latest = results.first()
        if latest:
            reply = (
                f"Your latest lab, {latest.lab_title}, scored {latest.score:g}/100 "
                f"({latest.correct}/{latest.total} correct answers). "
                "The score combines 80% answer accuracy and 20% server-measured timing. "
                f"The pass threshold is 70/100. You have submitted {results.count()} attempts."
            )
            actions.append({"label": "View latest result", "path": f"/results/{latest.id}"})
        else:
            reply = "You have no completed labs yet. Read a course, then try its scenario quiz to discover your strengths."
            actions.append({"label": "Explore careers", "path": "/careers"})
    elif matched:
        descriptions = []
        completed = set(CourseCompletion.objects.filter(user=user).values_list("course_id", flat=True))
        for career in matched[:3]:
            descriptions.append(
                f"{career.title}\n{career.summary}\n"
                f"Tools: {', '.join(career.tools)}.\nEducation: {career.education}\n"
                f"Salary: {career.salary}\nOutlook: {career.outlook}"
            )
            actions.append({"label": career.title, "path": f"/careers/{career.slug}"})
            course = next((c for c in career.courses.all()
                           if c.id not in completed and (not c.lab.is_premium or premium_active(user))), None)
            if course:
                actions.append({"label": f"Study: {course.title}", "path": f"/courses/{course.id}"})
        reply = "\n\n".join(descriptions)
        reply += "\n\nTry the suggested course, then its lab. These are educational scenarios, not executable work environments."
    elif words & {
        "recommend", "recommendation", "recommendations", "recommande",
        "orientation", "career", "careers", "metier", "metiers", "interests", "interets",
        "choose", "choisir", "match", "matches",
    }:
        interests = {normalized(value.strip()) for value in user.interests}
        related = [
            career.title for career in careers
            if interests & {normalized(value.strip()) for value in career.interests}
        ]
        reply = (
            f"Your interests overlap with: {', '.join(related)}. "
            if related else
            "Add interests to your profile and try labs from different careers. "
        )
        reply += (
            "Your matches page combines 75% lab performance and 25% interest fit for tested careers; "
            "untested careers use 60% interest fit. These are exploration suggestions, not a definitive assessment of your vocation."
        )
        actions = [
            {"label": "View my matches", "path": "/recommendations"},
            {"label": "Update my interests", "path": "/profile"},
        ]
    elif words & {"hello", "hi", "bonjour", "salut", "help", "aide"}:
        reply = (
            "Hello! I can explain careers in the catalogue, suggest a next course, "
            "and explain your saved results. Ask about Angular, Cloud or Cybersecurity, "
            "or ask: 'What do my scores mean?'"
        )
    else:
        reply = (
            "I could not match your question to the available career guidance topics. "
            "I am a local rule-based assistant, not a generative AI. "
            f"Ask about {', '.join(c.title for c in careers)}, your interests, or your results."
        )
        actions = [{"label": "Explore the catalogue", "path": "/careers"}]
    return {"reply": reply, "actions": actions}
