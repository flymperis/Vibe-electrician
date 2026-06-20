from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0025_restore_auth_role_proxies"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="must_change_password",
            field=models.BooleanField(
                default=False,
                help_text="Ο χρήστης ορίζει δικό του κωδικό μετά την πρώτη σύνδεση.",
                verbose_name="Αλλαγή κωδικού στο επόμενο login",
            ),
        ),
    ]
