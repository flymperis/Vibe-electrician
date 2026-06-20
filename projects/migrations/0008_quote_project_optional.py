from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0007_expense_project_label"),
    ]

    operations = [
        migrations.AlterField(
            model_name="quote",
            name="project",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="quote",
                to="projects.project",
                verbose_name="Έργο",
            ),
        ),
    ]
