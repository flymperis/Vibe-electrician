from django.contrib.auth import get_user_model
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Role, RolePermission, UserProfile
from .permissions import ROLE_ADMIN, clear_permission_cache
from .role_permissions import ALL_PERMISSION_CODES, ensure_role_permissions

User = get_user_model()


@receiver(post_save, sender=RolePermission)
@receiver(post_delete, sender=RolePermission)
def role_permission_changed(sender, **kwargs):
    clear_permission_cache()


@receiver(post_save, sender=Role)
def role_created(sender, instance, created, **kwargs):
    if created:
        ensure_role_permissions(instance)
    clear_permission_cache()


@receiver(post_save, sender=User)
def ensure_user_profile(sender, instance, created, **kwargs):
    from .role_permissions import ensure_system_roles

    ensure_system_roles()

    if instance.is_superuser:
        role = Role.by_code(ROLE_ADMIN)
    elif instance.is_staff:
        role = Role.by_code(UserProfile.CODE_OWNER)
    else:
        role = Role.by_code(UserProfile.CODE_WORKER)

    profile, profile_created = UserProfile.objects.get_or_create(
        user=instance,
        defaults={"role": role},
    )
    if not profile_created:
        if profile.role_id is None:
            profile.role = role
            profile.save(update_fields=["role"])
        return
    if not instance.is_superuser:
        profile.must_change_password = True
        profile.save(update_fields=["must_change_password"])
    _sync_staff_flags(instance, profile.role.code)


def _sync_staff_flags(user, role_code: str) -> None:
    is_admin = role_code == ROLE_ADMIN
    updates = {}
    if user.is_staff != is_admin:
        updates["is_staff"] = is_admin
    if updates:
        User.objects.filter(pk=user.pk).update(**updates)
