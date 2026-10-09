from django.core.management.base import BaseCommand, CommandError

from academy.push import send_pending


class Command(BaseCommand):
    help = "Send a bounded batch of pending Web Push deliveries; run repeatedly via a scheduler."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        if not 1 <= options["limit"] <= 1000:
            raise CommandError("--limit must be between 1 and 1000.")
        try:
            count = send_pending(options["limit"])
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(f"Sent {count} push notifications.")
