from django.db import migrations


def enable_owner_assignable(apps, schema_editor):
    Role = apps.get_model("projects", "Role")
    Role.objects.filter(code="owner").update(is_assignable=True)


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0026_userprofile_must_change_password"),
    ]

    operations = [
        migrations.RunPython(enable_owner_assignable, migrations.RunPython.noop),
    ]
