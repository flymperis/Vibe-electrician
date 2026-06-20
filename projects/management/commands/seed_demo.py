from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User

from django.core.management.base import BaseCommand
from django.utils import timezone

from projects.models import (
    Expense,
    Income,
    LookupOption,
    OperationalExpense,
    Project,
    Quote,
    QuoteLineItem,
    Role,
    UserProfile,
    WorkHours,
)
from projects.role_permissions import ensure_system_roles

DEMO_TAG = "[demo]"

MONTH_LABELS = (
    "",
    "Ιανουαρίου",
    "Φεβρουαρίου",
    "Μαρτίου",
    "Απριλίου",
    "Μαΐου",
    "Ιουνίου",
    "Ιουλίου",
    "Αυγούστου",
    "Σεπτεμβρίου",
    "Οκτωβρίου",
    "Νοεμβρίου",
    "Δεκεμβρίου",
)


def _day_in_month(year: int, month: int, day: int) -> date:
    import calendar

    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(day, last))


class Command(BaseCommand):
    help = "Δημιουργεί demo δεδομένα και χρήστες για παρουσίαση"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Διαγραφή υπαρχόντων demo δεδομένων πριν τη δημιουργία",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            Project.objects.all().delete()
            self.stdout.write("Deleted all projects.")

        self._create_users()
        projects = self._create_projects()
        self._create_monthly_examples(projects)
        self._create_quotes()

        self.stdout.write(self.style.SUCCESS("Demo data created successfully."))
        self.stdout.write("")
        self.stdout.write("Login credentials:")
        self.stdout.write("  partner1 / demo1234  (owner)")
        self.stdout.write("  partner2 / demo1234  (owner)")
        self.stdout.write("  giannis / demo1234   (worker)")
        self.stdout.write("  nikos / demo1234     (worker)")
        self.stdout.write("  admin / admin1234    (admin)")

    def _ensure_profile(self, user, role_code: str) -> None:
        ensure_system_roles()
        role = Role.by_code(role_code)
        profile, _ = UserProfile.objects.get_or_create(user=user, defaults={"role": role})
        if profile.role_id != role.pk:
            profile.role = role
            profile.save(update_fields=["role"])
        profile.must_change_password = False
        profile.save(update_fields=["must_change_password"])

    def _create_worker_user(self, username: str, first_name: str, password: str = "demo1234"):
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"first_name": first_name},
        )
        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(f"Created worker: {username}")
        elif not user.first_name:
            user.first_name = first_name
            user.save(update_fields=["first_name"])
        self._ensure_profile(user, UserProfile.CODE_WORKER)
        return user

    def _create_users(self):
        for username in ("partner1", "partner2"):
            user, created = User.objects.get_or_create(username=username)
            if created:
                user.set_password("demo1234")
                user.save()
                self.stdout.write(f"Created user: {username}")
            self._ensure_profile(user, UserProfile.CODE_OWNER)

        admin, created = User.objects.get_or_create(username="admin")
        if created or not admin.is_superuser:
            admin.set_password("admin1234")
            admin.is_staff = True
            admin.is_superuser = True
            admin.save()
            self.stdout.write("Created superuser: admin")
        self._ensure_profile(admin, UserProfile.CODE_ADMIN)

        self.worker_giannis = self._create_worker_user("giannis", "Γιάννης")
        self.worker_nikos = self._create_worker_user("nikos", "Νίκος")

    def _create_projects(self):
        if Project.objects.exists():
            self.stdout.write("Projects already exist — skipping creation.")
            return list(Project.objects.all())

        today = timezone.localdate()
        year = today.year

        p1 = Project.objects.create(
            name="Ηλεκτρολογική εγκατάσταση κατοικίας",
            client_name="Γιώργος Παπαδόπουλος",
            address="Κηφισιά, Αττική",
            status=Project.STATUS_IN_PROGRESS,
            start_date=_day_in_month(year, max(1, today.month - 2), 5),
            quoted_amount=Decimal("8500.00"),
            notes="Πλήρης ηλεκτρολογική εγκατάσταση νέας κατοικίας 120τ.μ.",
        )

        p2 = Project.objects.create(
            name="Ανακαίνιση πίνακα γραφείου",
            client_name="Tech Solutions AE",
            address="Μαρούσι, Αττική",
            status=Project.STATUS_COMPLETED,
            start_date=_day_in_month(year, 1, 10),
            end_date=_day_in_month(year, min(3, today.month), 28),
            quoted_amount=Decimal("3200.00"),
        )

        p3 = Project.objects.create(
            name="Φωτισμός καταστήματος",
            client_name="Μαρία Κωνσταντίνου",
            address="Χαλάνδρι, Αττική",
            status=Project.STATUS_QUOTE,
            quoted_amount=Decimal("4800.00"),
            notes="Προσφορά για LED φωτισμό και πίνακα.",
        )

        p4 = Project.objects.create(
            name="Ηλεκτρολογική επέκταση αποθήκης",
            client_name="Logistics Pro",
            address="Θεσσαλονίκη",
            status=Project.STATUS_IN_PROGRESS,
            start_date=_day_in_month(year, max(1, today.month - 1), 3),
            quoted_amount=Decimal("12000.00"),
        )

        past_projects = []
        past_specs = [
            (
                "Αντικατάσταση πίνακα διαμερίσματος",
                "Κώστας Δημητρίου",
                "Πειραιάς",
                1,
                Decimal("1850.00"),
            ),
            (
                "Εγκατάσταση θερμοσίφωνα & πρίζες",
                "Ελένη Νικολάου",
                "Γλυφάδα",
                2,
                Decimal("920.00"),
            ),
            (
                "Φωτισμός αίθριου καφετέριας",
                "Coffee House AE",
                "Κολωνάκι, Αθήνα",
                4,
                Decimal("5400.00"),
            ),
        ]
        for name, client, address, month, quoted in past_specs:
            if month > today.month:
                continue
            end_month = month
            past_projects.append(
                Project.objects.create(
                    name=name,
                    client_name=client,
                    address=address,
                    status=Project.STATUS_COMPLETED,
                    start_date=_day_in_month(year, month, 4),
                    end_date=_day_in_month(year, end_month, 22),
                    quoted_amount=quoted,
                    notes=f"{DEMO_TAG} Ολοκληρωμένο έργο {MONTH_LABELS[month]}.",
                )
            )

        return [p1, p2, p3, p4, *past_projects]

    def _create_monthly_examples(self, projects):
        if not projects:
            projects = list(Project.objects.all())
        if not projects:
            return

        if Income.objects.filter(description__startswith=DEMO_TAG).exists():
            self.stdout.write("Monthly demo data already exists — skipping.")
            return

        today = timezone.localdate()
        year = today.year
        p1, p2, p4 = projects[0], projects[1], projects[3]

        past_by_month = {
            p.start_date.month: p
            for p in projects
            if p.start_date and p.status == Project.STATUS_COMPLETED and p.pk != p2.pk
        }
        past_by_month[3] = p2

        op_categories = [
            OperationalExpense.CAT_ACCOUNTING,
            OperationalExpense.CAT_VEHICLE,
            OperationalExpense.CAT_INSURANCE,
            OperationalExpense.CAT_UTILITIES,
            OperationalExpense.CAT_SUBSCRIPTIONS,
        ]
        op_suppliers = [
            "Λογιστικό γραφείο Παπαδάκη",
            "Συνεργείο AutoService",
            "Insurance Co",
            "ΔΕΗ",
            "Γραφείο ειδών",
        ]

        income_count = expense_count = op_count = hours_count = 0

        for month in range(1, today.month + 1):
            label = MONTH_LABELS[month]
            d_income = _day_in_month(year, month, 8)
            d_expense = _day_in_month(year, month, 14)
            d_hours = _day_in_month(year, month, 10)
            d_op = _day_in_month(year, month, 5)

            if month in past_by_month:
                project_income = past_by_month[month]
                income_amount = project_income.quoted_amount or Decimal("1000.00")
                income_type = LookupOption.get_by_code(
                    LookupOption.GROUP_INCOME_TYPE, Income.TYPE_FINAL
                )
            elif month <= 3:
                project_income = p2
                income_amount = Decimal("800.00") + month * Decimal("100.00")
                income_type = LookupOption.get_by_code(
                    LookupOption.GROUP_INCOME_TYPE,
                    Income.TYPE_INVOICE if month == 1 else Income.TYPE_FINAL,
                )
            else:
                project_income = p1 if month % 2 else p4
                income_amount = Decimal("1200.00") + month * Decimal("150.00")
                income_type = LookupOption.get_by_code(
                    LookupOption.GROUP_INCOME_TYPE,
                    Income.TYPE_DEPOSIT if month % 2 else Income.TYPE_INVOICE,
                )

            Income.objects.create(
                project=project_income,
                amount=income_amount,
                date=d_income,
                income_type=income_type,
                payment_method=LookupOption.get_by_code(
                    LookupOption.GROUP_PAYMENT_TYPE,
                    Income.PAY_CASH if month % 2 else Income.PAY_CARD,
                ),
                description=f"{DEMO_TAG} Έσοδο {label}",
            )
            income_count += 1

            if month in past_by_month:
                expense_project = past_by_month[month]
            elif month <= 3:
                expense_project = p2
            else:
                expense_project = p1 if month % 2 else p4
            Expense.objects.create(
                project=expense_project,
                category=LookupOption.get_by_code(
                    LookupOption.GROUP_PROJECT_EXPENSE,
                    Expense.CAT_MATERIALS if month % 2 else Expense.CAT_LABOR,
                ),
                amount=Decimal("400.00") + month * Decimal("80.00"),
                date=d_expense,
                supplier="Ηλεκτρολογικά ΑΕ" if month % 2 else "",
                description=f"{DEMO_TAG} Έξοδο {label}",
            )
            expense_count += 1

            OperationalExpense.objects.create(
                category=LookupOption.get_by_code(
                    LookupOption.GROUP_OPERATIONAL_EXPENSE,
                    op_categories[(month - 1) % len(op_categories)],
                ),
                amount=Decimal("90.00") + month * Decimal("12.00"),
                date=d_op,
                supplier=op_suppliers[(month - 1) % len(op_suppliers)],
                description=f"{DEMO_TAG} Λειτουργικό έξοδο {label}",
            )
            op_count += 1

            if month in past_by_month:
                hours_project = past_by_month[month]
            elif month <= 2:
                hours_project = p2
            else:
                hours_project = p1 if month % 2 else p4
            WorkHours.objects.create(
                project=hours_project,
                date=d_hours,
                hours=Decimal("6.0") + (month % 3),
                worker=self.worker_giannis if month % 2 else self.worker_nikos,
                description=f"{DEMO_TAG} Εργασίες {label}",
            )
            hours_count += 1

            if month >= 4:
                WorkHours.objects.create(
                    project=p4 if month % 2 else p1,
                    date=_day_in_month(year, month, 18),
                    hours=Decimal("8.0"),
                    worker=self.worker_nikos if month % 2 else self.worker_giannis,
                    description=f"{DEMO_TAG} Δεύτερη καταχώρηση {label}",
                )
                hours_count += 1

        self.stdout.write(
            f"Created monthly demo ({year}/01–{year}/{today.month:02d}): "
            f"{income_count} incomes, {expense_count} project expenses, "
            f"{op_count} operational, {hours_count} work hours, "
            f"{len(past_by_month)} past-month projects."
        )

    def _create_quotes(self):
        if Quote.objects.exists():
            return

        today = timezone.localdate()
        project = Project.objects.filter(name="Φωτισμός καταστήματος").first()
        if not project:
            return

        quote = Quote.objects.create(
            project=project,
            title=project.name,
            client_name=project.client_name,
            client_vat="998877665",
            client_phone="6944123456",
            address=project.address,
            date=today - timedelta(days=3),
            valid_until=today + timedelta(days=27),
            status=Quote.STATUS_SENT,
            notes="Η προσφορά περιλαμβάνει υλικά και εργατικά. Ισχύει για 30 ημέρες.",
        )
        QuoteLineItem.objects.create(
            quote=quote,
            description="Πίνακας 24 θέσεων",
            category=LookupOption.get_by_code(
                LookupOption.GROUP_QUOTE_LINE_CATEGORY, QuoteLineItem.CAT_MATERIALS
            ),
            quantity=Decimal("1"),
            unit=LookupOption.get_by_code(
                LookupOption.GROUP_QUOTE_UNIT, QuoteLineItem.UNIT_PIECE
            ),
            unit_price=Decimal("850.00"),
        )
        QuoteLineItem.objects.create(
            quote=quote,
            description="LED spots & καλωδιώσεις",
            category=LookupOption.get_by_code(
                LookupOption.GROUP_QUOTE_LINE_CATEGORY, QuoteLineItem.CAT_MATERIALS
            ),
            quantity=Decimal("1"),
            unit=LookupOption.get_by_code(
                LookupOption.GROUP_QUOTE_UNIT, QuoteLineItem.UNIT_SET
            ),
            unit_price=Decimal("2200.00"),
        )
        QuoteLineItem.objects.create(
            quote=quote,
            description="Εργατικά εγκατάστασης",
            category=LookupOption.get_by_code(
                LookupOption.GROUP_QUOTE_LINE_CATEGORY, QuoteLineItem.CAT_LABOR
            ),
            quantity=Decimal("32"),
            unit=LookupOption.get_by_code(
                LookupOption.GROUP_QUOTE_UNIT, QuoteLineItem.UNIT_HOUR
            ),
            unit_price=Decimal("35.00"),
        )
        self.stdout.write(f"Created demo quote {quote.quote_number}.")
