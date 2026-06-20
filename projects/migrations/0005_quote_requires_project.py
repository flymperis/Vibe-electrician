from django.db import migrations, models
import django.db.models.deletion


def link_or_remove_orphan_quotes(apps, schema_editor):
    Quote = apps.get_model("projects", "Quote")
    Project = apps.get_model("projects", "Project")

    for quote in Quote.objects.filter(project__isnull=True):
        project = Project.objects.filter(name=quote.title).first()
        if not project:
            project = Project.objects.filter(client_name=quote.client_name).first()
        if project and not Quote.objects.filter(project=project).exclude(pk=quote.pk).exists():
            quote.project_id = project.id
            quote.save(update_fields=["project_id"])
        else:
            quote.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0004_quote_quotelineitem"),
    ]

    operations = [
        migrations.RunPython(link_or_remove_orphan_quotes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="quote",
            name="project",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="quote",
                to="projects.project",
                verbose_name="Έργο",
            ),
        ),
    ]
