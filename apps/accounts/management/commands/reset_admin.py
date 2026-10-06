from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Reset ADMIN user password"

    def handle(self, *args, **options):
        User = get_user_model()

        try:
            user = User.objects.get(username="ADMIN")
            user.set_password("ADMIN+123")
            user.is_active = True
            user.save()

            self.stdout.write(
                self.style.SUCCESS("ADMIN password reset successfully")
            )

        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR("ADMIN user does not exist")
            )