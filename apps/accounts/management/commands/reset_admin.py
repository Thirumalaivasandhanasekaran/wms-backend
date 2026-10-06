from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Create or reset ADMIN user"

    def handle(self, *args, **options):
        User = get_user_model()

        user, created = User.objects.get_or_create(
            username="ADMIN",
            defaults={
                "is_active": True,
                "is_staff": True,
                "is_superuser": True,
            },
        )

        user.set_password("ADMIN+123")
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.save()

        if created:
            self.stdout.write(
                self.style.SUCCESS("ADMIN user created and password set successfully")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("ADMIN user already existed; password reset successfully")
            )