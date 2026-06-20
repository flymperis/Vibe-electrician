from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0024_user_preferences"),
    ]

    operations = [
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
