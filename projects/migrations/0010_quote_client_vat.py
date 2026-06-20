from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0009_date_defaults"),
    ]

    operations = [
        migrations.AddField(
            model_name="quote",
            name="client_vat",
            field=models.CharField(blank=True, max_length=20, verbose_name="ΑΦΜ"),
        ),
    ]
