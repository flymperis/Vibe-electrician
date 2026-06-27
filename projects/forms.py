from datetime import timedelta
from decimal import Decimal

from django import forms
from django.contrib.auth import get_user_model
from django.forms import inlineformset_factory
from django.utils import timezone

from .form_utils import (
    ReasonableDateField,
    apply_reasonable_date_fields,
    date_widget,
    set_default_today,
    validate_date_range_order,
)
from .company import (
    LOGO_MAX_UPLOAD_HEIGHT,
    LOGO_MAX_UPLOAD_WIDTH,
    LOGO_MIN_HEIGHT,
    LOGO_MIN_WIDTH,
    LOGO_RECOMMENDED_HEIGHT,
    LOGO_RECOMMENDED_WIDTH,
)
from .models import (
    CompanyProfile,
    Customer,
    Expense,
    Income,
    LookupOption,
    OperationalExpense,
    OperationalIncome,
    Project,
    Quote,
    QuoteLineItem,
    WorkHours,
    WorkSchedule,
)
from .lookup import active_queryset, filter_choices
from .permissions import assignable_workers_queryset, user_display_name

User = get_user_model()


def _set_lookup_queryset(form, field_name: str, group: str) -> None:
    form.fields[field_name].queryset = active_queryset(group)


def _projects_available_for_quote(exclude_quote_pk=None):
    """Έργα που δεν έχουν ήδη προσφορά."""
    used = Quote.objects.exclude(project__isnull=True)
    if exclude_quote_pk:
        used = used.exclude(pk=exclude_quote_pk)
    used_ids = used.values_list("project_id", flat=True)
    return Project.objects.exclude(pk__in=used_ids).order_by("name")


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            "name",
            "client_name",
            "address",
            "status",
            "start_date",
            "end_date",
            "quoted_amount",
            "notes",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "π.χ. Ηλεκτρολογική εγκατάσταση κατοικίας"}),
            "client_name": forms.TextInput(attrs={"placeholder": "Όνομα πελάτη"}),
            "address": forms.TextInput(attrs={"placeholder": "Διεύθυνση έργου"}),
            "start_date": date_widget(),
            "end_date": date_widget(),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            for name in ("status", "start_date", "end_date", "quoted_amount"):
                self.fields.pop(name, None)
        else:
            apply_reasonable_date_fields(self, "start_date", "end_date")
            set_default_today(self, "start_date", "end_date")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("status") != Project.STATUS_COMPLETED:
            cleaned["end_date"] = None
        start = cleaned.get("start_date")
        end = cleaned.get("end_date")
        if start and end and end < start:
            self.add_error(
                "end_date",
                "Η ημερομηνία ολοκλήρωσης δεν μπορεί να είναι πριν την έναρξη.",
            )
        return cleaned


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ["name", "vat", "phone", "email", "address", "notes"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Όνομα ή επωνυμία"}),
            "vat": forms.TextInput(attrs={"placeholder": "π.χ. 123456789 (προαιρετικό)"}),
            "phone": forms.TextInput(attrs={"placeholder": "69xxxxxxxx"}),
            "email": forms.EmailInput(attrs={"placeholder": "email@example.com"}),
            "address": forms.TextInput(attrs={"placeholder": "Διεύθυνση / έδρα"}),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": "Σημειώσεις για τον πελάτη…"}),
        }

    def clean_vat(self):
        vat = (self.cleaned_data.get("vat") or "").strip()
        if not vat:
            return ""
        qs = Customer.objects.filter(vat__iexact=vat, is_active=True)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Υπάρχει ήδη ενεργός πελάτης με αυτό το ΑΦΜ.")
        return vat


class CustomerFilterForm(forms.Form):
    q = forms.CharField(
        label="Αναζήτηση",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Όνομα, ΑΦΜ, τηλέφωνο, email…"}),
    )
    show_inactive = forms.BooleanField(
        label="Εμφάνιση ανενεργών",
        required=False,
    )


class ProjectExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ["project", "category", "amount", "date", "supplier", "description"]
        widgets = {
            "date": date_widget(),
            "description": forms.TextInput(attrs={"placeholder": "π.χ. Καλώδια, πίνακας"}),
            "supplier": forms.TextInput(attrs={"placeholder": "Προμηθευτής"}),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = Project.objects.exclude(
            status=Project.STATUS_CANCELLED
        )
        self.fields["project"].label = "Έργο"
        if project:
            self.fields["project"].initial = project
            self.fields["project"].widget = forms.HiddenInput()
        _set_lookup_queryset(self, "category", LookupOption.GROUP_PROJECT_EXPENSE)
        apply_reasonable_date_fields(self, "date")
        set_default_today(self, "date")


class ProjectIncomeForm(forms.ModelForm):
    class Meta:
        model = Income
        fields = ["project", "income_type", "payment_method", "amount", "date", "description"]
        widgets = {
            "date": date_widget(),
            "description": forms.TextInput(attrs={"placeholder": "π.χ. Προκαταβολή 30%"}),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = Project.objects.exclude(
            status=Project.STATUS_CANCELLED
        )
        if project:
            self.fields["project"].initial = project
            self.fields["project"].widget = forms.HiddenInput()
        _set_lookup_queryset(self, "income_type", LookupOption.GROUP_INCOME_TYPE)
        _set_lookup_queryset(self, "payment_method", LookupOption.GROUP_PAYMENT_TYPE)
        apply_reasonable_date_fields(self, "date")
        set_default_today(self, "date")


class OperationalExpenseForm(forms.ModelForm):
    class Meta:
        model = OperationalExpense
        fields = ["category", "amount", "date", "supplier", "description"]
        widgets = {
            "date": date_widget(),
            "description": forms.TextInput(attrs={"placeholder": "π.χ. Μηνιαία αμοιβή λογιστή"}),
            "supplier": forms.TextInput(attrs={"placeholder": "Πάροχος / Εταιρεία"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _set_lookup_queryset(self, "category", LookupOption.GROUP_OPERATIONAL_EXPENSE)
        apply_reasonable_date_fields(self, "date")
        set_default_today(self, "date")


class OperationalIncomeForm(forms.ModelForm):
    class Meta:
        model = OperationalIncome
        fields = ["category", "amount", "date", "source", "description"]
        widgets = {
            "date": date_widget(),
            "description": forms.TextInput(attrs={"placeholder": "π.χ. Επιστροφή ΦΠΑ τριμήνου"}),
            "source": forms.TextInput(attrs={"placeholder": "π.χ. ΑΑΔΕ, ΔΥΠΑ"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _set_lookup_queryset(self, "category", LookupOption.GROUP_OPERATIONAL_INCOME)
        apply_reasonable_date_fields(self, "date")
        set_default_today(self, "date")


class WorkHoursForm(forms.ModelForm):
    class Meta:
        model = WorkHours
        fields = ["project", "date", "hours", "worker", "description"]
        widgets = {
            "date": date_widget(),
            "hours": forms.NumberInput(
                attrs={
                    "step": "0.5",
                    "min": "0.5",
                    "placeholder": "π.χ. 8",
                    "inputmode": "decimal",
                }
            ),
            "description": forms.TextInput(attrs={"placeholder": "π.χ. Τοποθέτηση πίνακα"}),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = Project.objects.exclude(
            status=Project.STATUS_CANCELLED
        )
        self.fields["worker"].queryset = assignable_workers_queryset()
        self.fields["worker"].required = False
        self.fields["worker"].label_from_instance = user_display_name
        if project:
            self.fields["project"].initial = project
            self.fields["project"].widget = forms.HiddenInput()
        apply_reasonable_date_fields(self, "date")
        set_default_today(self, "date")

    def clean_hours(self):
        hours = self.cleaned_data["hours"]
        if hours <= 0:
            raise forms.ValidationError("Οι ώρες πρέπει να είναι μεγαλύτερες από 0.")
        return hours


class WorkScheduleForm(forms.ModelForm):
    workers = forms.ModelMultipleChoiceField(
        label="Εργαζόμενοι",
        required=False,
        queryset=User.objects.none(),
        widget=forms.SelectMultiple(attrs={"size": 6}),
    )

    class Meta:
        model = WorkSchedule
        fields = [
            "project",
            "title",
            "date",
            "all_day",
            "start_time",
            "end_time",
            "workers",
            "location",
            "notes",
            "status",
        ]
        widgets = {
            "date": date_widget(),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
            "location": forms.TextInput(attrs={"placeholder": "Διεύθυνση ή τοποθεσία"}),
            "title": forms.TextInput(
                attrs={"placeholder": "Κενό = όνομα έργου"}
            ),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, project=None, default_date=None, show_status=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = Project.objects.exclude(
            status=Project.STATUS_CANCELLED
        ).order_by("name")
        self.fields["project"].required = False
        self.fields["title"].required = False
        self.fields["workers"].queryset = assignable_workers_queryset()
        self.fields["workers"].label_from_instance = user_display_name
        if project:
            self.fields["project"].initial = project
        if default_date and not self.data:
            self.fields["date"].initial = default_date
        apply_reasonable_date_fields(self, "date")
        if not show_status:
            self.fields.pop("status")
        elif not self.instance.pk:
            self.fields["status"].initial = WorkSchedule.STATUS_SCHEDULED
        if self.instance.pk:
            self.fields["workers"].initial = self.instance.workers.all()

    def clean_title(self):
        return (self.cleaned_data.get("title") or "").strip()

    def clean(self):
        cleaned = super().clean()
        all_day = cleaned.get("all_day")
        start = cleaned.get("start_time")
        end = cleaned.get("end_time")
        if not all_day and not start:
            self.add_error("start_time", "Ορίσε ώρα έναρξης ή επίλεξε «Ολόημερη».")
        if start and end and end <= start:
            self.add_error("end_time", "Η ώρα λήξης πρέπει να είναι μετά την έναρξη.")
        project = cleaned.get("project")
        if project and not cleaned.get("location") and project.address:
            cleaned["location"] = project.address
        if project and not cleaned.get("title"):
            cleaned["title"] = project.name
        if not cleaned.get("title"):
            self.add_error("title", "Συμπλήρωσε τίτλο ή επίλεξε έργο.")
        return cleaned

    def save(self, commit=True):
        schedule = super().save(commit=False)
        workers = self.cleaned_data.get("workers")
        if commit:
            schedule.save()
            if workers is not None:
                schedule.workers.set(workers)
        return schedule


class WorkScheduleFilterForm(forms.Form):
    q = forms.CharField(
        label="Αναζήτηση",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Τίτλος, τοποθεσία, σημειώσεις…"}),
    )
    project = forms.ModelChoiceField(
        label="Έργο",
        required=False,
        queryset=Project.objects.none(),
        empty_label="Όλα τα έργα",
    )
    status = forms.ChoiceField(
        label="Κατάσταση",
        required=False,
        choices=[
            ("", "Όλες"),
            (WorkSchedule.STATUS_SCHEDULED, "Προγραμματισμένες"),
            (WorkSchedule.STATUS_COMPLETED, "Ολοκληρωμένες"),
            (WorkSchedule.STATUS_CANCELLED, "Ακυρωμένες"),
        ],
    )
    worker = forms.ModelChoiceField(
        label="Εργαζόμενος",
        required=False,
        queryset=User.objects.none(),
        empty_label="Όλοι",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = Project.objects.exclude(
            status=Project.STATUS_CANCELLED
        ).order_by("name")
        self.fields["worker"].queryset = assignable_workers_queryset()
        self.fields["worker"].label_from_instance = user_display_name


class ProjectFilterForm(forms.Form):
    q = forms.CharField(
        label="Αναζήτηση",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Έργο, πελάτης, διεύθυνση…"}),
    )
    status = forms.MultipleChoiceField(
        label="Κατάσταση",
        required=False,
        choices=Project.STATUS_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "status-checkboxes"}),
    )
    date_from = ReasonableDateField(label="Από", required=False)
    date_to = ReasonableDateField(label="Έως", required=False)
    sort = forms.ChoiceField(
        label="Ταξινόμηση",
        required=False,
        choices=[
            ("-updated", "Πιο πρόσφατα"),
            ("name", "Όνομα Α-Ω"),
            ("-name", "Όνομα Ω-A"),
            ("client", "Πελάτης"),
            ("-start", "Ημ. έναρξης ↓"),
            ("start", "Ημ. έναρξης ↑"),
        ],
        initial="-updated",
    )

    def clean(self):
        cleaned = super().clean()
        validate_date_range_order(self, cleaned)
        return cleaned


class OperationalPageFilterForm(forms.Form):
    q = forms.CharField(
        label="Αναζήτηση",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Περιγραφή, πηγή, προμηθευτής…"}),
    )
    expense_category = forms.ChoiceField(
        label="Κατηγορία εξόδου",
        required=False,
        choices=[("", "Όλες")],
    )
    income_category = forms.ChoiceField(
        label="Κατηγορία εσόδου",
        required=False,
        choices=[("", "Όλες")],
    )
    date_from = ReasonableDateField(label="Από", required=False)
    date_to = ReasonableDateField(label="Έως", required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["expense_category"].choices = filter_choices(
            LookupOption.GROUP_OPERATIONAL_EXPENSE, "Όλες"
        )
        self.fields["income_category"].choices = filter_choices(
            LookupOption.GROUP_OPERATIONAL_INCOME, "Όλες"
        )

    def clean(self):
        cleaned = super().clean()
        validate_date_range_order(self, cleaned)
        return cleaned


class DateRangeFilterForm(forms.Form):
    date_from = ReasonableDateField(label="Από", required=False)
    date_to = ReasonableDateField(label="Έως", required=False)
    income_type = forms.ChoiceField(
        label="Τύπος εσόδου",
        required=False,
        choices=[("", "Όλα")],
    )
    expense_category = forms.ChoiceField(
        label="Κατηγορία εξόδου",
        required=False,
        choices=[("", "Όλες")],
    )
    worker = forms.ModelChoiceField(
        label="Εργαζόμενος",
        required=False,
        queryset=User.objects.none(),
        empty_label="Όλοι",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["income_type"].choices = filter_choices(
            LookupOption.GROUP_INCOME_TYPE, "Όλα"
        )
        self.fields["expense_category"].choices = filter_choices(
            LookupOption.GROUP_PROJECT_EXPENSE, "Όλες"
        )
        self.fields["worker"].queryset = assignable_workers_queryset()
        self.fields["worker"].label_from_instance = user_display_name

    def clean(self):
        cleaned = super().clean()
        validate_date_range_order(self, cleaned)
        return cleaned


QUOTE_OPEN_STATUS_CHOICES = [
    (Quote.STATUS_DRAFT, "Πρόχειρο"),
    (Quote.STATUS_SENT, "Απεσταλμένη"),
    (Quote.STATUS_REJECTED, "Απορριφθείσα"),
]


QUOTE_CUSTOMER_SNAPSHOT_FIELDS = (
    "client_name",
    "client_vat",
    "client_phone",
    "client_email",
    "address",
)


class QuoteForm(forms.ModelForm):
    class Meta:
        model = Quote
        fields = [
            "customer",
            "title",
            "client_name",
            "client_vat",
            "client_phone",
            "client_email",
            "address",
            "date",
            "valid_until",
            "status",
            "notes",
            "manual_total",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "π.χ. Ηλεκτρολογική εγκατάσταση κατοικίας"}),
            "client_name": forms.TextInput(attrs={"placeholder": "Όνομα πελάτη"}),
            "client_vat": forms.TextInput(attrs={"placeholder": "π.χ. 123456789 (προαιρετικό)"}),
            "client_phone": forms.TextInput(attrs={"placeholder": "69xxxxxxxx"}),
            "client_email": forms.EmailInput(attrs={"placeholder": "email@example.com"}),
            "address": forms.TextInput(attrs={"placeholder": "Διεύθυνση έργου"}),
            "date": date_widget(),
            "valid_until": date_widget(),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": "Όροι, σημειώσεις, προϋποθέσεις…"}),
            "manual_total": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0",
                    "class": "quote-manual-total",
                    "placeholder": "π.χ. 8500 (προαιρετικό)",
                }
            ),
        }

    def __init__(self, *args, prefill_customer=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.linked_project = self.instance.project if self.instance.pk else None

        self.fields["customer"].queryset = Customer.objects.filter(is_active=True).order_by("name")
        self.fields["customer"].label = "Πελάτης"
        self.fields["customer"].required = False
        self.fields["customer"].widget = forms.HiddenInput()
        self.fields["customer"].widget.attrs["id"] = "id_customer"
        self.selected_customer = self._resolve_selected_customer(prefill_customer)

        if prefill_customer and not self.data:
            self.initial["customer"] = prefill_customer.pk
            for key, value in prefill_customer.to_quote_snapshot().items():
                self.initial.setdefault(key, value)
        elif self.instance.pk and self.instance.customer_id and not self.data:
            self.initial.setdefault("customer", self.instance.customer_id)

        if not self.instance.pk and "status" in self.fields:
            self.fields["status"].initial = Quote.STATUS_DRAFT

        if self.instance.pk and self.instance.project_id:
            self.fields.pop("status", None)
        elif "status" in self.fields:
            self.fields["status"].choices = QUOTE_OPEN_STATUS_CHOICES

        apply_reasonable_date_fields(self, "date", "valid_until")
        set_default_today(self, "date")
        if not self.data and not self.initial.get("valid_until"):
            self.fields["valid_until"].initial = timezone.localdate() + timedelta(days=30)

        if self.selected_customer:
            self._set_customer_snapshot_fields_readonly(True)

        self.created_customer = None

    def _set_customer_snapshot_fields_readonly(self, readonly: bool) -> None:
        for name in QUOTE_CUSTOMER_SNAPSHOT_FIELDS:
            field = self.fields.get(name)
            if not field:
                continue
            if readonly:
                field.widget.attrs["readonly"] = "readonly"
                css = field.widget.attrs.get("class", "")
                if "is-readonly" not in css.split():
                    field.widget.attrs["class"] = f"{css} is-readonly".strip()
            else:
                field.widget.attrs.pop("readonly", None)
                css = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = " ".join(
                    part for part in css.split() if part != "is-readonly"
                )

    def clean(self):
        cleaned = super().clean()
        quote_date = cleaned.get("date")
        valid_until = cleaned.get("valid_until")
        if quote_date and valid_until and valid_until < quote_date:
            self.add_error(
                "valid_until",
                "Η «Ισχύς έως» δεν μπορεί να είναι πριν την ημερομηνία προσφοράς.",
            )
        customer = cleaned.get("customer")
        if customer:
            cleaned.update(customer.to_quote_snapshot())
        else:
            client_name = (cleaned.get("client_name") or "").strip()
            if not client_name:
                self.add_error(
                    "client_name",
                    "Συμπλήρωσε στοιχεία πελάτη ή επίλεξε από το πελατολόγιο.",
                )
            else:
                cleaned["client_name"] = client_name
                vat = (cleaned.get("client_vat") or "").strip()
                cleaned["client_vat"] = vat
                if vat and Customer.objects.filter(vat__iexact=vat, is_active=True).exists():
                    self.add_error(
                        "client_vat",
                        "Υπάρχει ήδη ενεργός πελάτης με αυτό το ΑΦΜ — επίλεξέ τον από το πελατολόγιο.",
                    )
        return cleaned

    def save(self, commit=True):
        quote = super().save(commit=False)
        if not quote.customer_id:
            quote.customer = Customer.objects.create(
                name=self.cleaned_data["client_name"],
                vat=self.cleaned_data.get("client_vat") or "",
                phone=(self.cleaned_data.get("client_phone") or "").strip(),
                email=(self.cleaned_data.get("client_email") or "").strip(),
                address=(self.cleaned_data.get("address") or "").strip(),
            )
            self.created_customer = quote.customer
        if commit:
            quote.save()
        return quote

    def clean_manual_total(self):
        value = self.cleaned_data.get("manual_total")
        if value in (None, ""):
            return None
        if value < 0:
            raise forms.ValidationError("Το σύνολο δεν μπορεί να είναι αρνητικό.")
        return value

    def _resolve_selected_customer(self, prefill_customer):
        if self.is_bound:
            raw = self.data.get(self.add_prefix("customer")) or self.data.get("customer")
            if raw:
                return Customer.objects.filter(pk=raw, is_active=True).first()
        if prefill_customer:
            return prefill_customer
        if self.instance.pk and self.instance.customer_id:
            return self.instance.customer
        return None


class QuoteLineItemForm(forms.ModelForm):
    class Meta:
        model = QuoteLineItem
        fields = ["description", "category", "quantity", "unit", "unit_price"]
        widgets = {
            "description": forms.TextInput(
                attrs={"placeholder": "π.χ. Πίνακας 12 θέσεων", "class": "line-description"}
            ),
            "quantity": forms.NumberInput(
                attrs={"step": "0.01", "min": "0", "class": "line-qty", "value": "1"}
            ),
            "unit_price": forms.NumberInput(
                attrs={"step": "0.01", "min": "0", "class": "line-price", "placeholder": "προαιρετικό"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["unit_price"].required = False
        _set_lookup_queryset(self, "category", LookupOption.GROUP_QUOTE_LINE_CATEGORY)
        _set_lookup_queryset(self, "unit", LookupOption.GROUP_QUOTE_UNIT)

    def clean_unit_price(self):
        value = self.cleaned_data.get("unit_price")
        if value in (None, ""):
            return Decimal("0.00")
        return value

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("DELETE"):
            return cleaned
        if not cleaned.get("description"):
            return cleaned
        if not cleaned.get("quantity"):
            cleaned["quantity"] = 1
        return cleaned


class BaseQuoteLineItemFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        active_lines = 0
        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                continue
            if not form.cleaned_data.get("description"):
                continue
            active_lines += 1
        if active_lines == 0:
            raise forms.ValidationError("Πρόσθεσε τουλάχιστον μία γραμμή στην προσφορά.")


def make_quote_line_formset(extra=1):
    return inlineformset_factory(
        Quote,
        QuoteLineItem,
        form=QuoteLineItemForm,
        formset=BaseQuoteLineItemFormSet,
        extra=extra,
        can_delete=True,
    )


class QuoteFilterForm(forms.Form):
    q = forms.CharField(
        label="Αναζήτηση",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Αρ. προσφοράς, πελάτης, έργο…"}),
    )
    status = forms.MultipleChoiceField(
        label="Κατάσταση",
        required=False,
        choices=Quote.STATUS_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "status-checkboxes"}),
    )
    date_from = ReasonableDateField(label="Από", required=False)
    date_to = ReasonableDateField(label="Έως", required=False)

    def clean(self):
        cleaned = super().clean()
        validate_date_range_order(self, cleaned)
        return cleaned


class CompanyProfileForm(forms.ModelForm):
    class Meta:
        model = CompanyProfile
        fields = [
            "name",
            "tagline",
            "logo",
            "address",
            "phone",
            "email",
            "website",
            "vat",
        ]

    def clean_logo(self):
        logo = self.cleaned_data.get("logo")
        if not logo or not hasattr(logo, "read"):
            return logo

        try:
            from PIL import Image

            image = Image.open(logo)
            width, height = image.size
        except Exception as exc:
            raise forms.ValidationError("Το αρχείο δεν είναι έγκυρη εικόνα.") from exc
        finally:
            if hasattr(logo, "seek"):
                logo.seek(0)

        if width < LOGO_MIN_WIDTH or height < LOGO_MIN_HEIGHT:
            raise forms.ValidationError(
                f"Πολύ μικρό λογότυπο ({width}×{height} px). "
                f"Ελάχιστο: {LOGO_MIN_WIDTH}×{LOGO_MIN_HEIGHT} px."
            )
        if width > LOGO_MAX_UPLOAD_WIDTH or height > LOGO_MAX_UPLOAD_HEIGHT:
            raise forms.ValidationError(
                f"Πολύ μεγάλο λογότυπο ({width}×{height} px). "
                f"Μέγιστο: {LOGO_MAX_UPLOAD_WIDTH}×{LOGO_MAX_UPLOAD_HEIGHT} px."
            )

        target_ratio = LOGO_RECOMMENDED_WIDTH / LOGO_RECOMMENDED_HEIGHT
        actual_ratio = width / height
        if abs(actual_ratio - target_ratio) / target_ratio > 0.35:
            raise forms.ValidationError(
                f"Η αναλογία ({width}×{height} px) απομακρύνεται από την προτεινόμενη "
                f"{LOGO_RECOMMENDED_WIDTH}×{LOGO_RECOMMENDED_HEIGHT} px."
            )

        return logo


class UserPreferencesForm(forms.ModelForm):
    class Meta:
        from .models import UserProfile

        model = UserProfile
        fields = ["language", "dark_mode"]
        widgets = {
            "language": forms.Select(),
            "dark_mode": forms.CheckboxInput(),
        }
