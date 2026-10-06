import os

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.constants import ACTIONS, DEFAULT_ROLES, MODULES
from apps.accounts.models import Permission, Role, User
from apps.settings_app.models import BusinessSettings, HardwareSettings, InvoiceSettings, PaymentSettings


class Command(BaseCommand):
    help = "Create permissions, default roles, settings rows and (optionally) the first Admin user. Safe to run repeatedly."

    def add_arguments(self, parser):
        parser.add_argument("--username", default=os.environ.get("ADMIN_USERNAME"))
        parser.add_argument("--password", default=os.environ.get("ADMIN_PASSWORD"))
        parser.add_argument("--email", default=os.environ.get("ADMIN_EMAIL", ""))
        parser.add_argument("--demo", action="store_true", help="Also load a small set of demo master data")

    @transaction.atomic
    def handle(self, *args, **opts):
        for module, _ in MODULES:
            for action in ACTIONS:
                Permission.objects.get_or_create(module=module, action=action)
        perms = {str(p): p for p in Permission.objects.all()}

        for name, cfg in DEFAULT_ROLES.items():
            role, created = Role.objects.get_or_create(name=name, defaults={"description": cfg["description"]})
            if role.full_access != cfg["full_access"]:
                Role.objects.filter(pk=role.pk).update(full_access=cfg["full_access"])
            if created:  # never overwrite permissions an admin has customised
                role.permissions.set([perms[f"{m}:{a}"] for m, actions in cfg["perms"].items() for a in actions])
        for model in (BusinessSettings, InvoiceSettings, PaymentSettings, HardwareSettings):
            model.load()
        self.stdout.write(self.style.SUCCESS("Permissions, roles and settings are ready."))

        if opts["username"] and opts["password"]:
            admin_role = Role.objects.get(name="Admin / Owner")
            user, created = User.objects.get_or_create(
                username=opts["username"], defaults={"email": opts["email"], "full_name": "Administrator", "is_staff": True, "is_superuser": True, "role": admin_role},
            )
            if created:
                user.set_password(opts["password"])
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Admin user '{user.username}' created."))
            else:
                self.stdout.write(f"User '{user.username}' already exists - left unchanged.")
        else:
            self.stdout.write("No ADMIN_USERNAME / ADMIN_PASSWORD provided: skipped admin user creation.")

        if opts["demo"]:
            from apps.accounts.demo import load_demo

            load_demo()
            self.stdout.write(self.style.SUCCESS("Demo master data loaded."))
