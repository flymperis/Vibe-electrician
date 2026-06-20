"""Καταγραφή κινήσεων (επίπεδο Γ) — προβολή μόνο από Django admin."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from typing import Any

from django.contrib.auth import get_user_model

from .lookup import label_for_id
from .permissions import get_user_profile
from .models import (
    ActivityLog,
    Customer,
    Expense,
    Income,
    OperationalExpense,
    OperationalIncome,
    Project,
    Quote,
    QuoteLineItem,
    WorkHours,
    WorkSchedule,
)

User = get_user_model()

# --- Γενικά βοηθήματα ---


def _values_equal(a: Any, b: Any) -> bool:
    if isinstance(a, Decimal) or isinstance(b, Decimal):
        try:
            return Decimal(a) == Decimal(b)
        except Exception:
            return a == b
    return a == b


def _format_default(_name: str, value: Any) -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    if hasattr(value, "isoformat"):
        return value.isoformat()
    text = str(value)
    if len(text) > 80:
        return text[:77] + "…"
    return text


def diff_tracked_fields(
    before: dict[str, Any],
    after: dict[str, Any],
    field_names: tuple[str, ...],
    labels: dict[str, str],
    formatters: dict[str, Callable[[str, Any], str]] | None = None,
) -> list[str]:
    formatters = formatters or {}
    changes: list[str] = []
    for name in field_names:
        old = before.get(name)
        new = after.get(name)
        if _values_equal(old, new):
            continue
        fmt = formatters.get(name, _format_default)
        label = labels[name]
        changes.append(f"{label}: {fmt(name, old)} → {fmt(name, new)}")
    return changes


def log_activity(
    *,
    user: User | None,
    action: str,
    object_type: str,
    object_id: int,
    object_repr: str,
    summary: str,
    details: list[str] | None = None,
) -> ActivityLog:
    return ActivityLog.objects.create(
        user=user if user and user.is_authenticated else None,
        action=action,
        object_type=object_type,
        object_id=object_id,
        object_repr=object_repr,
        summary=summary,
        details=details or [],
    )


def _log_updated(
    request,
    *,
    action: str,
    object_type: str,
    instance,
    object_repr: str,
    summary: str,
    before: dict[str, Any],
    field_names: tuple[str, ...],
    labels: dict[str, str],
    formatters: dict[str, Callable[[str, Any], str]] | None = None,
    snapshot_fn: Callable[[Any], dict[str, Any]],
) -> None:
    instance.refresh_from_db()
    after = snapshot_fn(instance)
    details = diff_tracked_fields(before, after, field_names, labels, formatters)
    if not details:
        return
    log_activity(
        user=request.user,
        action=action,
        object_type=object_type,
        object_id=instance.pk,
        object_repr=object_repr,
        summary=summary,
        details=details,
    )


# --- Προσφορές ---

QUOTE_FIELD_LABELS: dict[str, str] = {
    "title": "Τίτλος / Έργο",
    "client_name": "Πελάτης",
    "client_vat": "ΑΦΜ",
    "client_phone": "Τηλέφωνο",
    "client_email": "Email",
    "address": "Διεύθυνση",
    "date": "Ημερομηνία",
    "valid_until": "Ισχύς έως",
    "status": "Κατάσταση",
    "notes": "Σημειώσεις / Όροι",
    "manual_total": "Σύνολο (χειροκίνητο)",
}
QUOTE_TRACKED_FIELDS = tuple(QUOTE_FIELD_LABELS.keys())

LINE_FIELD_LABELS: dict[str, str] = {
    "description": "Περιγραφή",
    "category": "Κατηγορία",
    "quantity": "Ποσότητα",
    "unit": "Μονάδα",
    "unit_price": "Τιμή μονάδας",
}


def _format_quote_field(name: str, value: Any) -> str:
    if value is None or value == "":
        return "—"
    if name == "status":
        return dict(Quote.STATUS_CHOICES).get(value, str(value))
    if name in ("date", "valid_until"):
        return value.isoformat() if hasattr(value, "isoformat") else str(value)
    if name == "notes" and len(str(value)) > 80:
        return str(value)[:77] + "…"
    if name == "manual_total" and value is not None:
        return f"{Decimal(value):.2f}€"
    return str(value)


def _format_line_field(name: str, value: Any) -> str:
    if value is None or value == "":
        return "—"
    if name == "category":
        return label_for_id(value)
    if name == "unit":
        return label_for_id(value)
    if name in ("quantity", "unit_price"):
        if isinstance(value, Decimal):
            return f"{value:.2f}"
        return str(value)
    text = str(value)
    if len(text) > 60:
        return text[:57] + "…"
    return text


def quote_field_snapshot(quote: Quote) -> dict[str, Any]:
    return {name: getattr(quote, name) for name in QUOTE_TRACKED_FIELDS}


def quote_lines_snapshot(quote: Quote) -> dict[int, dict[str, Any]]:
    lines = QuoteLineItem.objects.filter(quote_id=quote.pk).order_by("sort_order", "pk")
    return {line.pk: line_field_snapshot(line) for line in lines}


def line_field_snapshot(line: QuoteLineItem) -> dict[str, Any]:
    return {
        "description": line.description,
        "category": line.category_id,
        "quantity": line.quantity,
        "unit": line.unit_id,
        "unit_price": line.unit_price,
    }


def diff_quote_lines(
    before: dict[int, dict[str, Any]], after: dict[int, dict[str, Any]]
) -> list[str]:
    changes: list[str] = []
    before_ids = set(before)
    after_ids = set(after)

    for pk in sorted(before_ids - after_ids):
        snap = before[pk]
        desc = _format_line_field("description", snap.get("description"))
        changes.append(f"Διαγράφηκε γραμμή ({desc})")

    for pk in sorted(after_ids - before_ids):
        snap = after[pk]
        desc = _format_line_field("description", snap.get("description"))
        changes.append(f"Προστέθηκε γραμμή ({desc})")

    for pk in sorted(before_ids & after_ids):
        old = before[pk]
        new = after[pk]
        line_changes: list[str] = []
        for field in LINE_FIELD_LABELS:
            if _values_equal(old.get(field), new.get(field)):
                continue
            label = LINE_FIELD_LABELS[field]
            line_changes.append(
                f"{label}: {_format_line_field(field, old.get(field))} → "
                f"{_format_line_field(field, new.get(field))}"
            )
        if not line_changes:
            continue
        desc = _format_line_field("description", new.get("description"))
        changes.append(f"Γραμμή ({desc}): " + "; ".join(line_changes))

    return changes


def build_quote_update_details(
    before_quote: dict[str, Any],
    after_quote: dict[str, Any],
    before_lines: dict[int, dict[str, Any]],
    after_lines: dict[int, dict[str, Any]],
) -> list[str]:
    quote_changes = diff_tracked_fields(
        before_quote,
        after_quote,
        QUOTE_TRACKED_FIELDS,
        QUOTE_FIELD_LABELS,
        {name: _format_quote_field for name in QUOTE_TRACKED_FIELDS},
    )
    return quote_changes + diff_quote_lines(before_lines, after_lines)


def _quote_repr(quote: Quote) -> str:
    return quote.quote_number or f"#{quote.pk}"


def log_quote_created(request, quote: Quote) -> None:
    quote.refresh_from_db()
    log_activity(
        user=request.user,
        action=ActivityLog.ACTION_QUOTE_CREATED,
        object_type="quote",
        object_id=quote.pk,
        object_repr=_quote_repr(quote),
        summary=f"Δημιουργία προσφοράς {_quote_repr(quote)}",
    )


def log_quote_updated(
    request,
    quote: Quote,
    before_quote: dict[str, Any],
    before_lines: dict[int, dict[str, Any]],
) -> None:
    quote.refresh_from_db()
    after_quote = quote_field_snapshot(quote)
    after_lines = quote_lines_snapshot(quote)
    details = build_quote_update_details(
        before_quote, after_quote, before_lines, after_lines
    )
    if not details:
        return
    log_activity(
        user=request.user,
        action=ActivityLog.ACTION_QUOTE_UPDATED,
        object_type="quote",
        object_id=quote.pk,
        object_repr=_quote_repr(quote),
        summary=f"Επεξεργασία προσφοράς {_quote_repr(quote)}",
        details=details,
    )


def log_quote_deleted(request, quote: Quote) -> None:
    log_activity(
        user=request.user,
        action=ActivityLog.ACTION_QUOTE_DELETED,
        object_type="quote",
        object_id=quote.pk,
        object_repr=_quote_repr(quote),
        summary=f"Διαγραφή προσφοράς {_quote_repr(quote)}",
    )


# --- Έργα ---

PROJECT_FIELD_LABELS: dict[str, str] = {
    "name": "Όνομα έργου",
    "client_name": "Πελάτης",
    "address": "Διεύθυνση",
    "status": "Κατάσταση",
    "start_date": "Ημ. έναρξης",
    "end_date": "Ημ. ολοκλήρωσης",
    "quoted_amount": "Προσφορά (€)",
    "notes": "Σημειώσεις",
}
PROJECT_EDIT_FIELDS = tuple(PROJECT_FIELD_LABELS.keys())
PROJECT_STATUS_FIELDS = ("status", "start_date", "end_date")


def _format_project_field(name: str, value: Any) -> str:
    if name == "status":
        return dict(Project.STATUS_CHOICES).get(value, _format_default(name, value))
    if name == "quoted_amount" and value is not None:
        return f"{Decimal(value):.2f}€"
    return _format_default(name, value)


def project_field_snapshot(project: Project) -> dict[str, Any]:
    return {name: getattr(project, name) for name in PROJECT_EDIT_FIELDS}


def _project_repr(project: Project) -> str:
    return project.name


def log_project_created(request, project: Project, *, from_quote: Quote | None = None) -> None:
    project.refresh_from_db()
    if from_quote:
        summary = (
            f"Δημιουργία έργου «{project.name}» από προσφορά {_quote_repr(from_quote)}"
        )
    else:
        summary = f"Δημιουργία έργου «{project.name}»"
    log_activity(
        user=request.user,
        action=ActivityLog.ACTION_PROJECT_CREATED,
        object_type="project",
        object_id=project.pk,
        object_repr=_project_repr(project),
        summary=summary,
    )


def log_project_updated(request, project: Project, before: dict[str, Any]) -> None:
    _log_updated(
        request,
        action=ActivityLog.ACTION_PROJECT_UPDATED,
        object_type="project",
        instance=project,
        object_repr=_project_repr(project),
        summary=f"Επεξεργασία έργου «{project.name}»",
        before=before,
        field_names=PROJECT_EDIT_FIELDS,
        labels=PROJECT_FIELD_LABELS,
        formatters={name: _format_project_field for name in PROJECT_EDIT_FIELDS},
        snapshot_fn=project_field_snapshot,
    )


def log_project_status_updated(request, project: Project, before: dict[str, Any]) -> None:
    _log_updated(
        request,
        action=ActivityLog.ACTION_PROJECT_UPDATED,
        object_type="project",
        instance=project,
        object_repr=_project_repr(project),
        summary=f"Επεξεργασία έργου «{project.name}» (κατάσταση)",
        before=before,
        field_names=PROJECT_STATUS_FIELDS,
        labels=PROJECT_FIELD_LABELS,
        formatters={name: _format_project_field for name in PROJECT_STATUS_FIELDS},
        snapshot_fn=project_field_snapshot,
    )


def log_project_deleted(request, project: Project) -> None:
    name = project.name
    log_activity(
        user=request.user,
        action=ActivityLog.ACTION_PROJECT_DELETED,
        object_type="project",
        object_id=project.pk,
        object_repr=name,
        summary=f"Διαγραφή έργου «{name}»",
    )


# --- Έσοδα / έξοδα έργου / εργατοώρες ---

def _format_money(_name: str, value: Any) -> str:
    if value is None:
        return "—"
    return f"{Decimal(value):.2f}€"


def _format_project_fk(_name: str, value: Any) -> str:
    if not value:
        return "—"
    project = Project.objects.filter(pk=value).first()
    return project.name if project else str(value)


def _format_user_fk(_name: str, value: Any) -> str:
    if not value:
        return "—"
    user = User.objects.filter(pk=value).first()
    if not user:
        return str(value)
    profile = get_user_profile(user)
    if profile is not None:
        return profile.display_name
    return user.get_full_name() or user.username


INCOME_FIELD_LABELS = {
    "project_id": "Έργο",
    "income_type_id": "Τύπος",
    "payment_method_id": "Τύπος πληρωμής",
    "amount": "Ποσό",
    "date": "Ημερομηνία",
    "description": "Περιγραφή",
}
INCOME_FIELDS = tuple(INCOME_FIELD_LABELS.keys())
INCOME_FORMATTERS = {
    "project_id": _format_project_fk,
    "income_type_id": lambda _n, v: label_for_id(v),
    "payment_method_id": lambda _n, v: label_for_id(v),
    "amount": _format_money,
}


def income_snapshot(income: Income) -> dict[str, Any]:
    return {name: getattr(income, name) for name in INCOME_FIELDS}


def _income_repr(income: Income) -> str:
    return f"{income.project.name} — {income.amount}€ ({income.date})"


def log_income_created(request, income: Income) -> None:
    income.refresh_from_db()
    log_activity(
        user=request.user,
        action=ActivityLog.ACTION_INCOME_CREATED,
        object_type="income",
        object_id=income.pk,
        object_repr=_income_repr(income),
        summary=f"Καταχώρηση εσόδου — έργο «{income.project.name}» ({income.amount}€)",
    )


def log_income_updated(request, income: Income, before: dict[str, Any]) -> None:
    _log_updated(
        request,
        action=ActivityLog.ACTION_INCOME_UPDATED,
        object_type="income",
        instance=income,
        object_repr=_income_repr(income),
        summary=f"Επεξεργασία εσόδου — έργο «{income.project.name}»",
        before=before,
        field_names=INCOME_FIELDS,
        labels=INCOME_FIELD_LABELS,
        formatters=INCOME_FORMATTERS,
        snapshot_fn=income_snapshot,
    )


def log_income_deleted(request, income: Income) -> None:
    project_name = income.project.name
    amount = income.amount
    log_activity(
        user=request.user,
        action=ActivityLog.ACTION_INCOME_DELETED,
        object_type="income",
        object_id=income.pk,
        object_repr=_income_repr(income),
        summary=f"Διαγραφή εσόδου — έργο «{project_name}» ({amount}€)",
    )


EXPENSE_FIELD_LABELS = {
    "project_id": "Έργο",
    "category_id": "Κατηγορία",
    "amount": "Ποσό",
    "date": "Ημερομηνία",
    "supplier": "Προμηθευτής",
    "description": "Περιγραφή",
}
EXPENSE_FIELDS = tuple(EXPENSE_FIELD_LABELS.keys())
EXPENSE_FORMATTERS = {
    "project_id": _format_project_fk,
    "category_id": lambda _n, v: label_for_id(v),
    "amount": _format_money,
}


def expense_snapshot(expense: Expense) -> dict[str, Any]:
    return {name: getattr(expense, name) for name in EXPENSE_FIELDS}


def _expense_repr(expense: Expense) -> str:
    return f"{expense.project.name} — {expense.amount}€ ({expense.date})"


def log_expense_created(request, expense: Expense) -> None:
    expense.refresh_from_db()
    log_activity(
        user=request.user,
        action=ActivityLog.ACTION_EXPENSE_CREATED,
        object_type="expense",
        object_id=expense.pk,
        object_repr=_expense_repr(expense),
        summary=f"Καταχώρηση εξόδου — έργο «{expense.project.name}» ({expense.amount}€)",
    )


def log_expense_updated(request, expense: Expense, before: dict[str, Any]) -> None:
    _log_updated(
        request,
        action=ActivityLog.ACTION_EXPENSE_UPDATED,
        object_type="expense",
        instance=expense,
        object_repr=_expense_repr(expense),
        summary=f"Επεξεργασία εξόδου — έργο «{expense.project.name}»",
        before=before,
        field_names=EXPENSE_FIELDS,
        labels=EXPENSE_FIELD_LABELS,
        formatters=EXPENSE_FORMATTERS,
        snapshot_fn=expense_snapshot,
    )


def log_expense_deleted(request, expense: Expense) -> None:
    project_name = expense.project.name
    amount = expense.amount
    log_activity(
        user=request.user,
        action=ActivityLog.ACTION_EXPENSE_DELETED,
        object_type="expense",
        object_id=expense.pk,
        object_repr=_expense_repr(expense),
        summary=f"Διαγραφή εξόδου — έργο «{project_name}» ({amount}€)",
    )


WORK_HOURS_FIELD_LABELS = {
    "project_id": "Έργο",
    "date": "Ημερομηνία",
    "hours": "Ώρες",
    "worker_id": "Εργαζόμενος",
    "description": "Περιγραφή",
}
WORK_HOURS_FIELDS = tuple(WORK_HOURS_FIELD_LABELS.keys())
WORK_HOURS_FORMATTERS = {
    "project_id": _format_project_fk,
    "worker_id": _format_user_fk,
    "hours": lambda _n, v: f"{Decimal(v):.1f}ωρ." if v is not None else "—",
}


def work_hours_snapshot(entry: WorkHours) -> dict[str, Any]:
    return {name: getattr(entry, name) for name in WORK_HOURS_FIELDS}


def _work_hours_repr(entry: WorkHours) -> str:
    from .permissions import user_display_name

    worker = user_display_name(entry.worker)
    return f"{entry.project.name} — {entry.hours}ωρ. ({worker}, {entry.date})"


def log_work_hours_created(request, entry: WorkHours) -> None:
    entry.refresh_from_db()
    log_activity(
        user=request.user,
        action=ActivityLog.ACTION_WORK_HOURS_CREATED,
        object_type="work_hours",
        object_id=entry.pk,
        object_repr=_work_hours_repr(entry),
        summary=(
            f"Καταχώρηση εργατοωρών — έργο «{entry.project.name}» ({entry.hours}ωρ.)"
        ),
    )


OPERATIONAL_FIELD_LABELS = {
    "category_id": "Κατηγορία",
    "amount": "Ποσό",
    "date": "Ημερομηνία",
    "supplier": "Προμηθευτής / Πάροχος",
    "description": "Περιγραφή",
}
OPERATIONAL_FIELDS = tuple(OPERATIONAL_FIELD_LABELS.keys())
OPERATIONAL_FORMATTERS = {
    "category_id": lambda _n, v: label_for_id(v),
    "amount": _format_money,
}


def _operational_repr(expense: OperationalExpense) -> str:
    return f"{expense.category.label} — {expense.amount}€ ({expense.date})"


def log_operational_expense_created(request, expense: OperationalExpense) -> None:
    expense.refresh_from_db()
    log_activity(
        user=request.user,
        action=ActivityLog.ACTION_OPERATIONAL_EXPENSE_CREATED,
        object_type="operational_expense",
        object_id=expense.pk,
        object_repr=_operational_repr(expense),
        summary=f"Καταχώρηση λειτουργικού εξόδου ({expense.amount}€)",
    )


def _operational_income_repr(income: OperationalIncome) -> str:
    return f"{income.category.label} — {income.amount}€ ({income.date})"


def log_operational_income_created(request, income: OperationalIncome) -> None:
    income.refresh_from_db()
    log_activity(
        user=request.user,
        action=ActivityLog.ACTION_OPERATIONAL_INCOME_CREATED,
        object_type="operational_income",
        object_id=income.pk,
        object_repr=_operational_income_repr(income),
        summary=f"Καταχώρηση λειτουργικού εσόδου ({income.amount}€)",
    )


# --- Πελάτες ---

CUSTOMER_FIELD_LABELS = {
    "name": "Όνομα / Επωνυμία",
    "vat": "ΑΦΜ",
    "phone": "Τηλέφωνο",
    "email": "Email",
    "address": "Διεύθυνση",
    "notes": "Σημειώσεις",
    "is_active": "Ενεργός",
}
CUSTOMER_FIELDS = tuple(CUSTOMER_FIELD_LABELS.keys())
CUSTOMER_FORMATTERS = {
    "is_active": lambda _n, v: "Ναι" if v else "Όχι",
}


def customer_field_snapshot(customer: Customer) -> dict[str, Any]:
    return {name: getattr(customer, name) for name in CUSTOMER_FIELDS}


def log_customer_created(request, customer: Customer) -> None:
    customer.refresh_from_db()
    log_activity(
        user=request.user,
        action=ActivityLog.ACTION_CUSTOMER_CREATED,
        object_type="customer",
        object_id=customer.pk,
        object_repr=customer.name,
        summary=f"Δημιουργία πελάτη «{customer.name}»",
    )


def log_customer_updated(request, customer: Customer, before: dict[str, Any]) -> None:
    _log_updated(
        request,
        action=ActivityLog.ACTION_CUSTOMER_UPDATED,
        object_type="customer",
        instance=customer,
        object_repr=customer.name,
        summary=f"Επεξεργασία πελάτη «{customer.name}»",
        before=before,
        field_names=CUSTOMER_FIELDS,
        labels=CUSTOMER_FIELD_LABELS,
        formatters=CUSTOMER_FORMATTERS,
        snapshot_fn=customer_field_snapshot,
    )


def log_customer_deactivated(request, customer: Customer) -> None:
    log_activity(
        user=request.user,
        action=ActivityLog.ACTION_CUSTOMER_DEACTIVATED,
        object_type="customer",
        object_id=customer.pk,
        object_repr=customer.name,
        summary=f"Απενεργοποίηση πελάτη «{customer.name}»",
    )


WORK_SCHEDULE_FIELD_LABELS = {
    "project_id": "Έργο",
    "title": "Τίτλος",
    "date": "Ημερομηνία",
    "all_day": "Ολόημερη",
    "start_time": "Ώρα έναρξης",
    "end_time": "Ώρα λήξης",
    "location": "Τοποθεσία",
    "notes": "Σημειώσεις",
    "status": "Κατάσταση",
}
WORK_SCHEDULE_FIELDS = tuple(WORK_SCHEDULE_FIELD_LABELS.keys())
WORK_SCHEDULE_FORMATTERS = {
    "project_id": _format_project_fk,
    "status": lambda _n, v: dict(WorkSchedule.STATUS_CHOICES).get(v, v or "—"),
}


def work_schedule_snapshot(schedule: WorkSchedule) -> dict[str, Any]:
    return {name: getattr(schedule, name) for name in WORK_SCHEDULE_FIELDS}


def _work_schedule_repr(schedule: WorkSchedule) -> str:
    return f"{schedule.title} ({schedule.date})"


def log_work_schedule_created(request, schedule: WorkSchedule) -> None:
    schedule.refresh_from_db()
    log_activity(
        user=request.user,
        action=ActivityLog.ACTION_WORK_SCHEDULE_CREATED,
        object_type="work_schedule",
        object_id=schedule.pk,
        object_repr=_work_schedule_repr(schedule),
        summary=f"Προγραμματισμός εργασίας «{schedule.title}» ({schedule.date})",
    )


def log_work_schedule_updated(request, schedule: WorkSchedule, before: dict[str, Any]) -> None:
    _log_updated(
        request,
        action=ActivityLog.ACTION_WORK_SCHEDULE_UPDATED,
        object_type="work_schedule",
        instance=schedule,
        object_repr=_work_schedule_repr(schedule),
        summary=f"Επεξεργασία προγραμματισμένης εργασίας «{schedule.title}»",
        before=before,
        field_names=WORK_SCHEDULE_FIELDS,
        labels=WORK_SCHEDULE_FIELD_LABELS,
        formatters=WORK_SCHEDULE_FORMATTERS,
        snapshot_fn=work_schedule_snapshot,
    )


def log_work_schedule_deleted(request, schedule: WorkSchedule) -> None:
    log_activity(
        user=request.user,
        action=ActivityLog.ACTION_WORK_SCHEDULE_DELETED,
        object_type="work_schedule",
        object_id=schedule.pk,
        object_repr=_work_schedule_repr(schedule),
        summary=f"Διαγραφή προγραμματισμένης εργασίας «{schedule.title}» ({schedule.date})",
    )
