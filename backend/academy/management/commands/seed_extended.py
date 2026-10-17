from academy.extended_data import CAREERS, MISSIONS
from academy.management.commands.seed_demo import Command as SeedCommand


class Command(SeedCommand):
    help = "Upsert six additional careers, 18 free courses/labs and 54 questions without resetting the original catalogue."
    careers = CAREERS
    missions = MISSIONS
