from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from portal.seed import build_demo


class Command(BaseCommand):
    help = "Create demo university, units, students and staff. DEMO ONLY: shared throwaway password."

    def add_arguments(self, parser):
        parser.add_argument("--password", default="demo12345")
        parser.add_argument("--force", action="store_true", help="Allow when DEBUG is off.")

    def handle(self, *args, **opts):
        if not settings.DEBUG and not opts["force"]:
            raise CommandError("Refusing to create demo accounts with DEBUG off. Use --force if you really mean it.")
        build_demo(opts["password"])
        self.stdout.write(self.style.SUCCESS("Demo data ready. Password for every demo account: " + opts["password"]))
        for line in ("student: brian / amina / peter", "lecturer: lec1 / lec2", "hod: hod1", "staff: staff1"):
            self.stdout.write("  " + line)
