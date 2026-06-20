import django.db.models.deletion
from django.db import migrations, models


ALL_PERMISSION_CODES = (
    "access_django_admin",
    "view_dashboard",
    "manage_projects",
    "manage_customers",
    "manage_quotes",
    "manage_project_finances",
    "manage_operational",
    "view_calendar",
    "manage_schedules",
    "view_reports",
    "export_reports",
)

SYSTEM_ROLES = {
    "admin": {
        "name": "Διαχειριστής",
        "description": "Πλήρης πρόσβαση στο σύστημα και Django admin.",
        "is_system": True,
        "is_assignable": False,
        "sort_order": 1,
        "permissions": {code: True for code in ALL_PERMISSION_CODES},
    },
    "owner": {
        "name": "Ιδιοκτήτης",
        "description": "Διαχείριση έργων, οικονομικών, προσφορών και αναφορών.",
        "is_system": True,
        "is_assignable": False,
        "sort_order": 2,
        "permissions": {
            "access_django_admin": False,
            "view_dashboard": True,
            "manage_projects": True,
            "manage_customers": True,
            "manage_quotes": True,
            "manage_project_finances": True,
            "manage_operational": True,
            "view_calendar": True,
            "manage_schedules": True,
            "view_reports": True,
            "export_reports": True,
        },
    },
    "worker": {
        "name": "Εργαζόμενος",
        "description": "Πρόσβαση μόνο στο ημερολόγιο εργασιών.",
        "is_system": True,
        "is_assignable": True,
        "sort_order": 3,
        "permissions": {
            "access_django_admin": False,
            "view_dashboard": False,
            "manage_projects": False,
            "manage_customers": False,
            "manage_quotes": False,
            "manage_project_finances": False,
            "manage_operational": False,
            "view_calendar": True,
            "manage_schedules": False,
            "view_reports": False,
            "export_reports": False,
        },
    },
}


def seed_roles(apps, schema_editor):
    Role = apps.get_model("projects", "Role")

    for code, spec in SYSTEM_ROLES.items():
        Role.objects.update_or_create(
            code=code,
            defaults={
                "name": spec["name"],
                "description": spec["description"],
                "is_system": spec["is_system"],
                "is_assignable": spec["is_assignable"],
                "sort_order": spec["sort_order"],
            },
        )


def migrate_userprofile_roles(apps, schema_editor):
    Role = apps.get_model("projects", "Role")
    UserProfile = apps.get_model("projects", "UserProfile")
    role_map = {role.code: role.pk for role in Role.objects.all()}
    default_pk = role_map.get("worker")
    for profile in UserProfile.objects.all():
        profile.role_id = role_map.get(profile.role_legacy, default_pk)
        profile.save(update_fields=["role_id"])


def migrate_rolepermission_roles(apps, schema_editor):
    Role = apps.get_model("projects", "Role")
    RolePermission = apps.get_model("projects", "RolePermission")
    role_map = {role.code: role.pk for role in Role.objects.all()}
    seen = set()
    for row in RolePermission.objects.all().order_by("id"):
        key = (row.role_legacy, row.permission)
        role_id = role_map.get(row.role_legacy)
        if role_id is None:
            row.delete()
            continue
        if key in seen:
            row.delete()
            continue
        seen.add(key)
        row.role_id = role_id
        row.save(update_fields=["role_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0022_auth_role_permission_proxy"),
    ]

    operations = [
        migrations.DeleteModel(
            name="AuthRolePermission",
        ),
        migrations.CreateModel(
            name="Role",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "code",
                    models.SlugField(
                        help_text="Μοναδικό αναγνωριστικό, π.χ. owner, worker",
                        max_length=30,
                        unique=True,
                        verbose_name="Κωδικός",
                    ),
                ),
                ("name", models.CharField(max_length=100, verbose_name="Όνομα")),
                ("description", models.TextField(blank=True, verbose_name="Περιγραφή")),
                (
                    "is_system",
                    models.BooleanField(
                        default=False,
                        help_text="Οι συστημικοί ρόλοι δεν διαγράφονται.",
                        verbose_name="Συστημικός",
                    ),
                ),
                (
                    "is_assignable",
                    models.BooleanField(
                        default=False,
                        help_text="Εμφανίζεται στις επιλογές εργαζομένων (ώρες, ημερολόγιο).",
                        verbose_name="Εμφάνιση ως εργαζόμενος",
                    ),
                ),
                (
                    "sort_order",
                    models.PositiveSmallIntegerField(default=0, verbose_name="Σειρά"),
                ),
            ],
            options={
                "verbose_name": "Ρόλος",
                "verbose_name_plural": "Ρόλοι",
                "ordering": ["sort_order", "name"],
            },
        ),
        migrations.RenameField(
            model_name="rolepermission",
            old_name="role",
            new_name="role_legacy",
        ),
        migrations.RenameField(
            model_name="userprofile",
            old_name="role",
            new_name="role_legacy",
        ),
        migrations.AddField(
            model_name="rolepermission",
            name="role",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="permissions",
                to="projects.role",
                verbose_name="Ρόλος",
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="role",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="user_profiles",
                to="projects.role",
                verbose_name="Ρόλος",
            ),
        ),
        migrations.RunPython(seed_roles, migrations.RunPython.noop),
        migrations.RunPython(migrate_rolepermission_roles, migrations.RunPython.noop),
        migrations.RunPython(migrate_userprofile_roles, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name="rolepermission",
            name="unique_role_permission",
        ),
        migrations.RemoveField(
            model_name="rolepermission",
            name="role_legacy",
        ),
        migrations.RemoveField(
            model_name="userprofile",
            name="role_legacy",
        ),
        migrations.AlterField(
            model_name="rolepermission",
            name="role",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="permissions",
                to="projects.role",
                verbose_name="Ρόλος",
            ),
        ),
        migrations.AlterField(
            model_name="userprofile",
            name="role",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="user_profiles",
                to="projects.role",
                verbose_name="Ρόλος",
            ),
        ),
        migrations.AddConstraint(
            model_name="rolepermission",
            constraint=models.UniqueConstraint(
                fields=("role", "permission"),
                name="unique_role_permission",
            ),
        ),
        migrations.AlterModelOptions(
            name="rolepermission",
            options={
                "ordering": ["role", "permission"],
                "verbose_name": "Δικαίωμα ρόλου",
                "verbose_name_plural": "Δικαιώματα ρόλων",
            },
        ),
        migrations.CreateModel(
            name="AuthRole",
            fields=[],
            options={
                "verbose_name": "Ρόλος",
                "verbose_name_plural": "Ρόλοι",
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("projects.role",),
        ),
        migrations.CreateModel(
            name="AuthRolePermission",
            fields=[],
            options={
                "verbose_name": "Δικαιώματα ρόλων",
                "verbose_name_plural": "Δικαιώματα ρόλων",
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("projects.rolepermission",),
        ),
    ]
