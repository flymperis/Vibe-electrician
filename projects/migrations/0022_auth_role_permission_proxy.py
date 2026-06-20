from django.db import migrations, models


def seed_role_permissions(apps, schema_editor):
    RolePermission = apps.get_model("projects", "RolePermission")
    defaults = {
        "admin": {
            "access_django_admin": True,
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
        "owner": {
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
        "worker": {
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
    }
    for role, permissions in defaults.items():
        for permission, allowed in permissions.items():
            RolePermission.objects.update_or_create(
                role=role,
                permission=permission,
                defaults={"allowed": allowed},
            )


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0021_rolepermission_auth_app"),
    ]

    operations = [
        migrations.CreateModel(
            name="RolePermission",
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
                    "role",
                    models.CharField(
                        choices=[
                            ("admin", "Admin"),
                            ("owner", "Owner"),
                            ("worker", "Worker"),
                        ],
                        max_length=20,
                        verbose_name="Ρόλος",
                    ),
                ),
                (
                    "permission",
                    models.CharField(max_length=50, verbose_name="Δικαίωμα"),
                ),
                (
                    "allowed",
                    models.BooleanField(default=False, verbose_name="Επιτρέπεται"),
                ),
            ],
            options={
                "verbose_name": "Δικαίωμα ρόλου",
                "verbose_name_plural": "Ρόλοι",
                "ordering": ["role", "permission"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("role", "permission"),
                        name="unique_role_permission",
                    )
                ],
            },
        ),
        migrations.RunPython(seed_role_permissions, migrations.RunPython.noop),
        migrations.CreateModel(
            name="AuthRolePermission",
            fields=[],
            options={
                "verbose_name": "Ρόλοι",
                "verbose_name_plural": "Ρόλοι",
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("projects.rolepermission",),
        ),
    ]
