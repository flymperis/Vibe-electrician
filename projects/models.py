from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.utils import timezone


def default_local_date():
    return timezone.localdate()


class Role(models.Model):
    code = models.SlugField(
        "Κωδικός",
        max_length=30,
        unique=True,
        help_text="Μοναδικό αναγνωριστικό, π.χ. owner, worker",
    )
    name = models.CharField("Όνομα", max_length=100)
    description = models.TextField("Περιγραφή", blank=True)
    is_system = models.BooleanField(
        "Συστημικός",
        default=False,
        help_text="Οι συστημικοί ρόλοι δεν διαγράφονται.",
    )
    is_assignable = models.BooleanField(
        "Εμφάνιση ως εργαζόμενος",
        default=False,
        help_text="Εμφανίζεται στις επιλογές εργαζομένων (ώρες, ημερολόγιο).",
    )
    sort_order = models.PositiveSmallIntegerField("Σειρά", default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Ρόλος"
        verbose_name_plural = "Ρόλοι"

    def __str__(self):
        return self.name

    @classmethod
    def by_code(cls, code: str):
        return cls.objects.get(code=code)


class AuthRole(Role):
    """Proxy για CRUD ρόλων στο admin tab «Πιστοποίηση και Εξουσιοδότηση»."""

    class Meta:
        proxy = True
        app_label = "auth"
        verbose_name = "Ρόλος"
        verbose_name_plural = "Ρόλοι"


class UserProfile(models.Model):
    CODE_ADMIN = "admin"
    CODE_OWNER = "owner"
    CODE_WORKER = "worker"

    LANG_EL = "el"
    LANG_EN = "en"
    LANGUAGE_CHOICES = [
        (LANG_EL, "Ελληνικά"),
        (LANG_EN, "English"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="Χρήστης",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name="user_profiles",
        verbose_name="Ρόλος",
    )
    language = models.CharField(
        "Γλώσσα",
        max_length=5,
        choices=LANGUAGE_CHOICES,
        default=LANG_EL,
    )
    dark_mode = models.BooleanField("Dark mode", default=False)
    must_change_password = models.BooleanField(
        "Αλλαγή κωδικού στο επόμενο login",
        default=False,
        help_text="Ο χρήστης ορίζει δικό του κωδικό μετά την πρώτη σύνδεση.",
    )

    class Meta:
        verbose_name = "Προφίλ χρήστη"
        verbose_name_plural = "Προφίλ χρηστών"

    def __str__(self):
        return f"{self.display_name} ({self.role.name})"

    @property
    def display_name(self) -> str:
        full = (self.user.get_full_name() or "").strip()
        return full or self.user.username


class RolePermission(models.Model):
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="permissions",
        verbose_name="Ρόλος",
    )
    permission = models.CharField("Δικαίωμα", max_length=50)
    allowed = models.BooleanField("Επιτρέπεται", default=False)

    class Meta:
        verbose_name = "Δικαίωμα ρόλου"
        verbose_name_plural = "Δικαιώματα ρόλων"
        constraints = [
            models.UniqueConstraint(
                fields=["role", "permission"],
                name="unique_role_permission",
            ),
        ]
        ordering = ["role", "permission"]

    def __str__(self):
        state = "Ναι" if self.allowed else "Όχι"
        return f"{self.role.name} — {self.permission}: {state}"


class AuthRolePermission(RolePermission):
    """Proxy για matrix δικαιωμάτων στο admin tab «Πιστοποίηση και Εξουσιοδότηση»."""

    class Meta:
        proxy = True
        app_label = "auth"
        verbose_name = "Δικαιώματα ρόλων"
        verbose_name_plural = "Δικαιώματα ρόλων"


class Customer(models.Model):
    """Κεντρικό πελατολόγιο — στοιχεία επικοινωνίας πελάτη."""

    name = models.CharField("Όνομα / Επωνυμία", max_length=200)
    vat = models.CharField("ΑΦΜ", max_length=20, blank=True)
    phone = models.CharField("Τηλέφωνο", max_length=30, blank=True)
    email = models.EmailField("Email", blank=True)
    address = models.CharField("Διεύθυνση", max_length=300, blank=True)
    notes = models.TextField("Σημειώσεις", blank=True)
    is_active = models.BooleanField("Ενεργός", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Πελάτης"
        verbose_name_plural = "Πελάτες"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["vat"]),
        ]

    def __str__(self):
        return self.name

    @property
    def display_label(self) -> str:
        if self.vat:
            return f"{self.name} (ΑΦΜ {self.vat})"
        return self.name

    def to_quote_snapshot(self) -> dict[str, str]:
        return {
            "client_name": self.name,
            "client_vat": self.vat or "",
            "client_phone": self.phone or "",
            "client_email": self.email or "",
            "address": self.address or "",
        }


class Project(models.Model):
    STATUS_QUOTE = "quote"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_QUOTE, "Προσφορά"),
        (STATUS_IN_PROGRESS, "Σε εξέλιξη"),
        (STATUS_COMPLETED, "Ολοκληρωμένο"),
        (STATUS_CANCELLED, "Ακυρωμένο"),
    ]

    name = models.CharField("Όνομα έργου", max_length=200)
    client_name = models.CharField("Πελάτης", max_length=200)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
        verbose_name="Πελάτης (πελατολόγιο)",
    )
    address = models.CharField("Διεύθυνση", max_length=300, blank=True)
    status = models.CharField(
        "Κατάσταση",
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_QUOTE,
    )
    start_date = models.DateField("Ημ. έναρξης", null=True, blank=True)
    end_date = models.DateField("Ημ. ολοκλήρωσης", null=True, blank=True)
    quoted_amount = models.DecimalField(
        "Προσφορά (€)",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    notes = models.TextField("Σημειώσεις", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Έργο"
        verbose_name_plural = "Έργα"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.name} ({self.client_name})"

    @property
    def total_income(self) -> Decimal:
        total = self.incomes.aggregate(total=Sum("amount"))["total"]
        return total or Decimal("0.00")

    @property
    def total_expenses(self) -> Decimal:
        total = self.expenses.aggregate(total=Sum("amount"))["total"]
        return total or Decimal("0.00")

    @property
    def profit(self) -> Decimal:
        return self.total_income - self.total_expenses

    @property
    def profit_margin(self) -> Decimal | None:
        if self.total_income <= 0:
            return None
        return (self.profit / self.total_income) * 100

    @property
    def total_hours(self) -> Decimal:
        total = self.work_hours.aggregate(total=Sum("hours"))["total"]
        return total or Decimal("0.00")

    @property
    def is_pre_job(self) -> bool:
        """Πριν την έναρξη εργασιών — φάση προσφοράς."""
        return self.status == self.STATUS_QUOTE

    @property
    def accepts_work_entries(self) -> bool:
        """Έσοδα, έξοδα και εργατοώρες μόνο μετά την έναρξη έργου."""
        return self.status in (self.STATUS_IN_PROGRESS, self.STATUS_COMPLETED)


class LookupOption(models.Model):
    """Επιλογή λίστας (dropdown) — διαχείριση από το διαχειριστικό."""

    GROUP_INCOME_TYPE = "income_type"
    GROUP_PAYMENT_TYPE = "payment_type"
    GROUP_PROJECT_EXPENSE = "project_expense"
    GROUP_OPERATIONAL_EXPENSE = "operational_expense"
    GROUP_OPERATIONAL_INCOME = "operational_income"
    GROUP_QUOTE_LINE_CATEGORY = "quote_line_category"
    GROUP_QUOTE_UNIT = "quote_unit"

    GROUP_CHOICES = [
        (GROUP_INCOME_TYPE, "Τύπος εσόδου"),
        (GROUP_PAYMENT_TYPE, "Τύπος πληρωμής"),
        (GROUP_PROJECT_EXPENSE, "Κατηγορία εξόδου έργου"),
        (GROUP_OPERATIONAL_EXPENSE, "Κατηγορία λειτουργικού εξόδου"),
        (GROUP_OPERATIONAL_INCOME, "Κατηγορία λειτουργικού εσόδου"),
        (GROUP_QUOTE_LINE_CATEGORY, "Κατηγορία γραμμής προσφοράς"),
        (GROUP_QUOTE_UNIT, "Μονάδα μέτρησης προσφοράς"),
    ]

    group = models.CharField("Ομάδα", max_length=30, choices=GROUP_CHOICES, editable=False)
    code = models.SlugField(
        "Κωδικός",
        max_length=40,
        help_text="Μόνιμος κωδικός (λατινικά, π.χ. invoice). Μην τον αλλάζεις μετά τη χρήση.",
    )
    label = models.CharField("Ετικέτα", max_length=100)
    sort_order = models.PositiveSmallIntegerField("Σειρά", default=0)
    is_active = models.BooleanField("Ενεργή", default=True)

    class Meta:
        verbose_name = "Επιλογή λίστας"
        verbose_name_plural = "Επιλογές λιστών"
        ordering = ["group", "sort_order", "label"]
        constraints = [
            models.UniqueConstraint(fields=["group", "code"], name="uniq_lookup_group_code"),
        ]

    def __str__(self):
        return self.label

    @classmethod
    def get_by_code(cls, group: str, code: str) -> "LookupOption":
        return cls.objects.get(group=group, code=code)


def default_income_type_id():
    return (
        LookupOption.objects.filter(
            group=LookupOption.GROUP_INCOME_TYPE,
            code="invoice",
        )
        .values_list("pk", flat=True)
        .first()
    )


def default_payment_method_id():
    return (
        LookupOption.objects.filter(
            group=LookupOption.GROUP_PAYMENT_TYPE,
            code="cash",
        )
        .values_list("pk", flat=True)
        .first()
    )


def default_project_expense_category_id():
    return (
        LookupOption.objects.filter(
            group=LookupOption.GROUP_PROJECT_EXPENSE,
            code="materials",
        )
        .values_list("pk", flat=True)
        .first()
    )


def default_operational_expense_category_id():
    return (
        LookupOption.objects.filter(
            group=LookupOption.GROUP_OPERATIONAL_EXPENSE,
            code="other",
        )
        .values_list("pk", flat=True)
        .first()
    )


def default_operational_income_category_id():
    return (
        LookupOption.objects.filter(
            group=LookupOption.GROUP_OPERATIONAL_INCOME,
            code="other",
        )
        .values_list("pk", flat=True)
        .first()
    )


def default_quote_line_category_id():
    return (
        LookupOption.objects.filter(
            group=LookupOption.GROUP_QUOTE_LINE_CATEGORY,
            code="materials",
        )
        .values_list("pk", flat=True)
        .first()
    )


def default_quote_unit_id():
    return (
        LookupOption.objects.filter(
            group=LookupOption.GROUP_QUOTE_UNIT,
            code="piece",
        )
        .values_list("pk", flat=True)
        .first()
    )


class Income(models.Model):
    TYPE_DEPOSIT = "deposit"
    TYPE_INVOICE = "invoice"
    TYPE_FINAL = "final"
    TYPE_OTHER = "other"

    PAY_CASH = "cash"
    PAY_CARD = "card"

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="incomes",
        verbose_name="Έργο",
    )
    amount = models.DecimalField("Ποσό (€)", max_digits=10, decimal_places=2)
    date = models.DateField("Ημερομηνία", default=default_local_date)
    income_type = models.ForeignKey(
        LookupOption,
        on_delete=models.PROTECT,
        limit_choices_to={"group": LookupOption.GROUP_INCOME_TYPE},
        related_name="incomes",
        verbose_name="Τύπος",
        default=default_income_type_id,
    )
    payment_method = models.ForeignKey(
        LookupOption,
        on_delete=models.PROTECT,
        limit_choices_to={"group": LookupOption.GROUP_PAYMENT_TYPE},
        related_name="income_payments",
        verbose_name="Τύπος πληρωμής",
        default=default_payment_method_id,
    )
    description = models.CharField("Περιγραφή", max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Έσοδο έργου"
        verbose_name_plural = "Έσοδα έργων"
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.project.name} — {self.amount}€ ({self.date})"


class Expense(models.Model):
    """Έξοδο που ανήκει σε συγκεκριμένο έργο."""

    CAT_MATERIALS = "materials"
    CAT_LABOR = "labor"
    CAT_SUBCONTRACTOR = "subcontractor"
    CAT_TRANSPORT = "transport"
    CAT_EQUIPMENT = "equipment"
    CAT_OTHER = "other"

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="expenses",
        verbose_name="Έργο",
    )
    category = models.ForeignKey(
        LookupOption,
        on_delete=models.PROTECT,
        limit_choices_to={"group": LookupOption.GROUP_PROJECT_EXPENSE},
        related_name="project_expenses",
        verbose_name="Κατηγορία",
        default=default_project_expense_category_id,
    )
    amount = models.DecimalField("Ποσό (€)", max_digits=10, decimal_places=2)
    date = models.DateField("Ημερομηνία", default=default_local_date)
    supplier = models.CharField("Προμηθευτής", max_length=200, blank=True)
    description = models.CharField("Περιγραφή", max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Έξοδο έργου"
        verbose_name_plural = "Έξοδα έργων"
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.project.name} — {self.amount}€ ({self.category.label})"


class OperationalExpense(models.Model):
    """Λειτουργικά έξοδα εταιρείας — όχι δεμένα με έργο."""

    CAT_ACCOUNTING = "accounting"
    CAT_INSURANCE = "insurance"
    CAT_RENT = "rent"
    CAT_UTILITIES = "utilities"
    CAT_VEHICLE = "vehicle"
    CAT_TOOLS = "tools"
    CAT_SUBSCRIPTIONS = "subscriptions"
    CAT_OTHER = "other"

    category = models.ForeignKey(
        LookupOption,
        on_delete=models.PROTECT,
        limit_choices_to={"group": LookupOption.GROUP_OPERATIONAL_EXPENSE},
        related_name="operational_expenses",
        verbose_name="Κατηγορία",
        default=default_operational_expense_category_id,
    )
    amount = models.DecimalField("Ποσό (€)", max_digits=10, decimal_places=2)
    date = models.DateField("Ημερομηνία", default=default_local_date)
    supplier = models.CharField("Προμηθευτής / Πάροχος", max_length=200, blank=True)
    description = models.CharField("Περιγραφή", max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Λειτουργικό έξοδο"
        verbose_name_plural = "Λειτουργικά έξοδα"
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.category.label} — {self.amount}€ ({self.date})"


class OperationalIncome(models.Model):
    """Λειτουργικά έσοδα εταιρείας — όχι δεμένα με έργο (π.χ. επιστροφή φόρου)."""

    CAT_TAX_REFUND = "tax_refund"
    CAT_SUBSIDY = "subsidy"
    CAT_INSURANCE_REFUND = "insurance_refund"
    CAT_GRANT = "grant"
    CAT_OTHER = "other"

    category = models.ForeignKey(
        LookupOption,
        on_delete=models.PROTECT,
        limit_choices_to={"group": LookupOption.GROUP_OPERATIONAL_INCOME},
        related_name="operational_incomes",
        verbose_name="Κατηγορία",
        default=default_operational_income_category_id,
    )
    amount = models.DecimalField("Ποσό (€)", max_digits=10, decimal_places=2)
    date = models.DateField("Ημερομηνία", default=default_local_date)
    source = models.CharField("Πηγή / Φορέας", max_length=200, blank=True)
    description = models.CharField("Περιγραφή", max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Λειτουργικό έσοδο"
        verbose_name_plural = "Λειτουργικά έσοδα"
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.category.label} — {self.amount}€ ({self.date})"


class WorkHours(models.Model):
    """Καταχώρηση εργατοωρών ανά έργο."""

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="work_hours",
        verbose_name="Έργο",
    )
    date = models.DateField("Ημερομηνία", default=default_local_date)
    hours = models.DecimalField(
        "Ώρες",
        max_digits=6,
        decimal_places=2,
        help_text="π.χ. 8 ή 4.5",
    )
    worker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="work_hour_entries",
        verbose_name="Εργαζόμενος",
    )
    description = models.CharField("Περιγραφή", max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Εργατοώρα"
        verbose_name_plural = "Εργατοώρες"
        ordering = ["-date", "-created_at"]

    def __str__(self):
        from .permissions import user_display_name

        worker = user_display_name(self.worker)
        return f"{self.project.name} — {self.hours}ωρ. ({worker}, {self.date})"

    @property
    def worker_display(self) -> str:
        from .permissions import user_display_name

        return user_display_name(self.worker)


class WorkSchedule(models.Model):
    """Προγραμματισμένη εργασία — ημερολόγιο εργασιών."""

    STATUS_SCHEDULED = "scheduled"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_SCHEDULED, "Προγραμματισμένη"),
        (STATUS_COMPLETED, "Ολοκληρωμένη"),
        (STATUS_CANCELLED, "Ακυρωμένη"),
    ]

    project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="work_schedules",
        verbose_name="Έργο",
    )
    title = models.CharField("Τίτλος", max_length=200)
    date = models.DateField("Ημερομηνία", default=default_local_date)
    all_day = models.BooleanField("Ολόημερη", default=True)
    start_time = models.TimeField("Ώρα έναρξης", null=True, blank=True)
    end_time = models.TimeField("Ώρα λήξης", null=True, blank=True)
    workers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="assigned_schedules",
        verbose_name="Εργαζόμενοι",
    )
    location = models.CharField("Τοποθεσία", max_length=300, blank=True)
    notes = models.TextField("Σημειώσεις", blank=True)
    status = models.CharField(
        "Κατάσταση",
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_SCHEDULED,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Προγραμματισμένη εργασία"
        verbose_name_plural = "Προγραμματισμένες εργασίες"
        ordering = ["date", "start_time", "title"]

    def __str__(self):
        return f"{self.title} ({self.date})"

    @property
    def is_active(self) -> bool:
        return self.status == self.STATUS_SCHEDULED

    @property
    def display_location(self) -> str:
        if self.location:
            return self.location
        if self.project_id and self.project.address:
            return self.project.address
        return ""

    @property
    def time_label(self) -> str:
        if self.all_day or not self.start_time:
            return "Ολόημερη"
        if self.end_time:
            return f"{self.start_time.strftime('%H:%M')}–{self.end_time.strftime('%H:%M')}"
        return self.start_time.strftime("%H:%M")

    @property
    def calendar_color_index(self) -> int:
        if self.project_id:
            return self.project_id % 6
        return 0

    @property
    def workers_label(self) -> str:
        from .permissions import user_display_name

        names = [user_display_name(user) for user in self.workers.all()]
        return ", ".join(names) if names else "—"


class Quote(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_SENT = "sent"
    STATUS_ACCEPTED = "accepted"
    STATUS_REJECTED = "rejected"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Πρόχειρο"),
        (STATUS_SENT, "Απεσταλμένη"),
        (STATUS_ACCEPTED, "Αποδεκτή"),
        (STATUS_REJECTED, "Απορριφθείσα"),
    ]

    quote_number = models.CharField("Αρ. προσφοράς", max_length=20, unique=True, blank=True)
    title = models.CharField("Τίτλος / Έργο", max_length=200)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quotes",
        verbose_name="Πελάτης (πελατολόγιο)",
    )
    client_name = models.CharField("Πελάτης", max_length=200)
    client_vat = models.CharField("ΑΦΜ", max_length=20, blank=True)
    client_phone = models.CharField("Τηλέφωνο", max_length=30, blank=True)
    client_email = models.EmailField("Email", blank=True)
    address = models.CharField("Διεύθυνση", max_length=300, blank=True)
    date = models.DateField("Ημερομηνία", default=default_local_date)
    valid_until = models.DateField("Ισχύς έως", null=True, blank=True)
    status = models.CharField(
        "Κατάσταση",
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
    )
    notes = models.TextField("Σημειώσεις / Όροι", blank=True)
    manual_total = models.DecimalField(
        "Σύνολο (χειροκίνητο)",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    project = models.OneToOneField(
        Project,
        on_delete=models.CASCADE,
        related_name="quote",
        verbose_name="Έργο",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Προσφορά"
        verbose_name_plural = "Προσφορές"
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.quote_number or '—'} — {self.title} ({self.client_name})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.quote_number:
            self.quote_number = f"PROS-{self.date.year}-{self.pk:04d}"
            Quote.objects.filter(pk=self.pk).update(quote_number=self.quote_number)

    @property
    def lines_subtotal(self) -> Decimal:
        return sum(
            (item.line_total for item in self.line_items.all()),
            Decimal("0.00"),
        )

    @property
    def total(self) -> Decimal:
        if self.manual_total is not None:
            return Decimal(self.manual_total)
        return self.lines_subtotal

    @property
    def uses_manual_total(self) -> bool:
        return self.manual_total is not None

    @property
    def can_be_deleted(self) -> bool:
        """Διαγραφή μόνο όταν δεν έχει δημιουργηθεί έργο από αυτή την προσφορά."""
        return self.project_id is None


class QuoteLineItem(models.Model):
    CAT_MATERIALS = "materials"
    CAT_LABOR = "labor"
    CAT_SUBCONTRACTOR = "subcontractor"
    CAT_EQUIPMENT = "equipment"
    CAT_OTHER = "other"

    UNIT_PIECE = "piece"
    UNIT_METER = "meter"
    UNIT_HOUR = "hour"
    UNIT_SET = "set"
    UNIT_LUMP = "lump"

    quote = models.ForeignKey(
        Quote,
        on_delete=models.CASCADE,
        related_name="line_items",
        verbose_name="Προσφορά",
    )
    description = models.CharField("Περιγραφή", max_length=300, blank=True)
    category = models.ForeignKey(
        LookupOption,
        on_delete=models.PROTECT,
        limit_choices_to={"group": LookupOption.GROUP_QUOTE_LINE_CATEGORY},
        related_name="quote_line_categories",
        verbose_name="Κατηγορία",
        default=default_quote_line_category_id,
    )
    quantity = models.DecimalField("Ποσότητα", max_digits=10, decimal_places=2, default=1)
    unit = models.ForeignKey(
        LookupOption,
        on_delete=models.PROTECT,
        limit_choices_to={"group": LookupOption.GROUP_QUOTE_UNIT},
        related_name="quote_line_units",
        verbose_name="Μονάδα",
        default=default_quote_unit_id,
    )
    unit_price = models.DecimalField(
        "Τιμή μονάδας (€)",
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        blank=True,
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Γραμμή προσφοράς"
        verbose_name_plural = "Γραμμές προσφοράς"
        ordering = ["sort_order", "pk"]

    def __str__(self):
        return f"{self.description} — {self.line_total}€"

    @property
    def line_total(self) -> Decimal:
        return (self.quantity * self.unit_price).quantize(Decimal("0.01"))


class CompanyProfile(models.Model):
    """Singleton — στοιχεία εταιρείας για PDF προσφοράς (διαχείριση από admin)."""

    name = models.CharField("Επωνυμία", max_length=200, default="Vibe Electrician")
    tagline = models.CharField(
        "Υπότιτλος",
        max_length=200,
        blank=True,
        default="Ηλεκτρολογικές Εγκαταστάσεις",
    )
    logo = models.ImageField(
        "Λογότυπο",
        upload_to="company/",
        blank=True,
        help_text=(
            "Προτεινόμενο: 360×112 px (PNG διαφανές). "
            "Εμφάνιση στο PDF: έως 180×56 px."
        ),
    )
    address = models.CharField("Διεύθυνση", max_length=300, blank=True)
    phone = models.CharField("Τηλέφωνο", max_length=30, blank=True)
    email = models.EmailField("Email", blank=True)
    vat = models.CharField("ΑΦΜ", max_length=20, blank=True)
    website = models.CharField("Website", max_length=200, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Στοιχεία εταιρείας"
        verbose_name_plural = "Στοιχεία εταιρείας"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "CompanyProfile":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class ActivityLog(models.Model):
    """Ιστορικό κινήσεων — προβολή μόνο από Django admin."""

    ACTION_QUOTE_CREATED = "quote_created"
    ACTION_QUOTE_UPDATED = "quote_updated"
    ACTION_QUOTE_DELETED = "quote_deleted"
    ACTION_PROJECT_CREATED = "project_created"
    ACTION_PROJECT_UPDATED = "project_updated"
    ACTION_PROJECT_DELETED = "project_deleted"
    ACTION_INCOME_CREATED = "income_created"
    ACTION_INCOME_UPDATED = "income_updated"
    ACTION_INCOME_DELETED = "income_deleted"
    ACTION_EXPENSE_CREATED = "expense_created"
    ACTION_EXPENSE_UPDATED = "expense_updated"
    ACTION_EXPENSE_DELETED = "expense_deleted"
    ACTION_WORK_HOURS_CREATED = "work_hours_created"
    ACTION_WORK_SCHEDULE_CREATED = "work_schedule_created"
    ACTION_WORK_SCHEDULE_UPDATED = "work_schedule_updated"
    ACTION_WORK_SCHEDULE_DELETED = "work_schedule_deleted"
    ACTION_OPERATIONAL_EXPENSE_CREATED = "operational_expense_created"
    ACTION_OPERATIONAL_INCOME_CREATED = "operational_income_created"
    ACTION_CUSTOMER_CREATED = "customer_created"
    ACTION_CUSTOMER_UPDATED = "customer_updated"
    ACTION_CUSTOMER_DEACTIVATED = "customer_deactivated"

    ACTION_CHOICES = [
        (ACTION_QUOTE_CREATED, "Δημιουργία προσφοράς"),
        (ACTION_QUOTE_UPDATED, "Επεξεργασία προσφοράς"),
        (ACTION_QUOTE_DELETED, "Διαγραφή προσφοράς"),
        (ACTION_PROJECT_CREATED, "Δημιουργία έργου"),
        (ACTION_PROJECT_UPDATED, "Επεξεργασία έργου"),
        (ACTION_PROJECT_DELETED, "Διαγραφή έργου"),
        (ACTION_INCOME_CREATED, "Καταχώρηση εσόδου"),
        (ACTION_INCOME_UPDATED, "Επεξεργασία εσόδου"),
        (ACTION_INCOME_DELETED, "Διαγραφή εσόδου"),
        (ACTION_EXPENSE_CREATED, "Καταχώρηση εξόδου έργου"),
        (ACTION_EXPENSE_UPDATED, "Επεξεργασία εξόδου έργου"),
        (ACTION_EXPENSE_DELETED, "Διαγραφή εξόδου έργου"),
        (ACTION_WORK_HOURS_CREATED, "Καταχώρηση εργατοωρών"),
        (ACTION_WORK_SCHEDULE_CREATED, "Προγραμματισμός εργασίας"),
        (ACTION_WORK_SCHEDULE_UPDATED, "Επεξεργασία προγραμματισμένης εργασίας"),
        (ACTION_WORK_SCHEDULE_DELETED, "Διαγραφή προγραμματισμένης εργασίας"),
        (ACTION_OPERATIONAL_EXPENSE_CREATED, "Καταχώρηση λειτουργικού εξόδου"),
        (ACTION_OPERATIONAL_INCOME_CREATED, "Καταχώρηση λειτουργικού εσόδου"),
        (ACTION_CUSTOMER_CREATED, "Δημιουργία πελάτη"),
        (ACTION_CUSTOMER_UPDATED, "Επεξεργασία πελάτη"),
        (ACTION_CUSTOMER_DEACTIVATED, "Απενεργοποίηση πελάτη"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Χρήστης",
        related_name="activity_logs",
    )
    action = models.CharField("Ενέργεια", max_length=40, choices=ACTION_CHOICES)
    object_type = models.CharField("Τύπος αντικειμένου", max_length=40)
    object_id = models.PositiveIntegerField("ID αντικειμένου")
    object_repr = models.CharField("Αντικείμενο", max_length=200)
    summary = models.CharField("Σύνοψη", max_length=300)
    details = models.JSONField(
        "Λεπτομέρειες αλλαγών",
        default=list,
        blank=True,
        help_text="Λίστα αλλαγών (πεδία προσφοράς / γραμμές).",
    )
    created_at = models.DateTimeField("Ημερομηνία", auto_now_add=True)

    class Meta:
        verbose_name = "Κίνηση"
        verbose_name_plural = "Κινήσεις (log)"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["object_type", "object_id"]),
            models.Index(fields=["action"]),
        ]

    def __str__(self):
        return f"{self.created_at:%d/%m/%Y %H:%M} — {self.summary}"
