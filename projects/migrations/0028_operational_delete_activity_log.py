from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0027_owner_assignable_workers"),
    ]

    operations = [
        migrations.AlterField(
            model_name="activitylog",
            name="action",
            field=models.CharField(
                choices=[
                    ("quote_created", "Δημιουργία προσφοράς"),
                    ("quote_updated", "Επεξεργασία προσφοράς"),
                    ("quote_deleted", "Διαγραφή προσφοράς"),
                    ("project_created", "Δημιουργία έργου"),
                    ("project_updated", "Επεξεργασία έργου"),
                    ("project_deleted", "Διαγραφή έργου"),
                    ("income_created", "Καταχώρηση εσόδου"),
                    ("income_updated", "Επεξεργασία εσόδου"),
                    ("income_deleted", "Διαγραφή εσόδου"),
                    ("expense_created", "Καταχώρηση εξόδου έργου"),
                    ("expense_updated", "Επεξεργασία εξόδου έργου"),
                    ("expense_deleted", "Διαγραφή εξόδου έργου"),
                    ("work_hours_created", "Καταχώρηση εργατοωρών"),
                    ("work_schedule_created", "Προγραμματισμός εργασίας"),
                    ("work_schedule_updated", "Επεξεργασία προγραμματισμένης εργασίας"),
                    ("work_schedule_deleted", "Διαγραφή προγραμματισμένης εργασίας"),
                    ("operational_expense_created", "Καταχώρηση λειτουργικού εξόδου"),
                    ("operational_expense_deleted", "Διαγραφή λειτουργικού εξόδου"),
                    ("operational_income_created", "Καταχώρηση λειτουργικού εσόδου"),
                    ("operational_income_deleted", "Διαγραφή λειτουργικού εσόδου"),
                    ("customer_created", "Δημιουργία πελάτη"),
                    ("customer_updated", "Επεξεργασία πελάτη"),
                    ("customer_deactivated", "Απενεργοποίηση πελάτη"),
                ],
                max_length=40,
                verbose_name="Ενέργεια",
            ),
        ),
    ]
