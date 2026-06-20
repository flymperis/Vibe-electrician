from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from projects.models import Role, UserProfile
from projects.permissions import ROLE_ADMIN
from projects.role_permissions import ensure_system_roles


class Command(BaseCommand):
    help = "Ensure system roles exist and every user has a UserProfile with a role."

    def handle(self, *args, **options):
        ensure_system_roles()
        User = get_user_model()
        created = 0
        fixed = 0

        for user in User.objects.all().order_by("id"):
            if user.is_superuser:
                role = Role.by_code(ROLE_ADMIN)
            elif user.is_staff:
                role = Role.by_code(UserProfile.CODE_OWNER)
            else:
                role = Role.by_code(UserProfile.CODE_WORKER)

            profile = UserProfile.objects.filter(user=user).first()
            if profile is None:
                UserProfile.objects.create(user=user, role=role)
                created += 1
                self.stdout.write(f"Created profile: {user.username} -> {role.code}")
            elif profile.role_id is None:
                profile.role = role
                profile.save(update_fields=["role"])
                fixed += 1
                self.stdout.write(f"Fixed profile: {user.username} -> {role.code}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. profiles created={created}, fixed={fixed}, roles={Role.objects.count()}"
            )
        )
