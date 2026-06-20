from datetime import date

from django.db.models import Q, QuerySet

from .models import Customer, OperationalExpense, OperationalIncome, Project, Quote, WorkSchedule


def filter_projects(
    qs: QuerySet[Project],
    *,
    q: str = "",
    statuses: list[str] | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    sort: str = "-updated",
) -> QuerySet[Project]:
    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(client_name__icontains=q)
            | Q(address__icontains=q)
            | Q(notes__icontains=q)
        )
    if statuses:
        qs = qs.filter(status__in=statuses)
    if date_from:
        qs = qs.filter(
            Q(start_date__gte=date_from)
            | Q(start_date__isnull=True, created_at__date__gte=date_from)
        )
    if date_to:
        qs = qs.filter(
            Q(start_date__lte=date_to)
            | Q(start_date__isnull=True, created_at__date__lte=date_to)
        )

    sort_map = {
        "-updated": "-updated_at",
        "name": "name",
        "-name": "-name",
        "client": "client_name",
        "-start": "-start_date",
        "start": "start_date",
    }
    return qs.order_by(sort_map.get(sort, "-updated_at"))


def filter_operational_expenses(
    qs: QuerySet[OperationalExpense],
    *,
    q: str = "",
    category: str = "",
    date_from: date | None = None,
    date_to: date | None = None,
) -> QuerySet[OperationalExpense]:
    if q:
        qs = qs.filter(
            Q(supplier__icontains=q)
            | Q(description__icontains=q)
        )
    if category:
        qs = qs.filter(category__code=category)
    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)
    return qs


def filter_operational_incomes(
    qs: QuerySet[OperationalIncome],
    *,
    q: str = "",
    category: str = "",
    date_from: date | None = None,
    date_to: date | None = None,
) -> QuerySet[OperationalIncome]:
    if q:
        qs = qs.filter(
            Q(source__icontains=q)
            | Q(description__icontains=q)
        )
    if category:
        qs = qs.filter(category__code=category)
    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)
    return qs


def filter_work_schedules(
    qs: QuerySet[WorkSchedule],
    *,
    q: str = "",
    project=None,
    status: str = "",
    worker=None,
) -> QuerySet[WorkSchedule]:
    if q:
        qs = qs.filter(
            Q(title__icontains=q)
            | Q(location__icontains=q)
            | Q(notes__icontains=q)
            | Q(workers__first_name__icontains=q)
            | Q(workers__last_name__icontains=q)
            | Q(workers__username__icontains=q)
            | Q(project__name__icontains=q)
        ).distinct()
    if project:
        qs = qs.filter(project=project)
    if status:
        qs = qs.filter(status=status)
    if worker:
        qs = qs.filter(workers=worker)
    return qs


def filter_by_date_range(
    qs: QuerySet,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
) -> QuerySet:
    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)
    return qs


def parse_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def get_filter_params(request, keys: list[str]) -> dict[str, str]:
    return {key: request.GET.get(key, "").strip() for key in keys}


def build_projects_summary(projects: QuerySet[Project]) -> list[dict]:
    return [
        {
            "project": project,
            "income": project.total_income,
            "expenses": project.total_expenses,
            "hours": project.total_hours,
            "profit": project.profit,
            "margin": project.profit_margin,
        }
        for project in projects
    ]


def filter_quotes(
    qs: QuerySet[Quote],
    *,
    q: str = "",
    statuses: list[str] | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> QuerySet[Quote]:
    if q:
        qs = qs.filter(
            Q(quote_number__icontains=q)
            | Q(title__icontains=q)
            | Q(client_name__icontains=q)
            | Q(address__icontains=q)
        )
    if statuses:
        qs = qs.filter(status__in=statuses)
    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)
    return qs


def _fold_text(value: str | None) -> str:
    return (value or "").casefold()


def _customer_matches_query(
    *,
    name: str,
    vat: str,
    phone: str,
    email: str,
    address: str,
    q_fold: str,
) -> bool:
    return any(
        q_fold in _fold_text(value)
        for value in (name, vat, phone, email, address)
    )


def filter_customers(
    qs: QuerySet[Customer],
    *,
    q: str = "",
    show_inactive: bool = False,
) -> QuerySet[Customer]:
    if not show_inactive:
        qs = qs.filter(is_active=True)
    q = (q or "").strip()
    if q:
        q_fold = q.casefold()
        rows = qs.values_list("pk", "name", "vat", "phone", "email", "address")
        pks = [
            pk
            for pk, name, vat, phone, email, address in rows
            if _customer_matches_query(
                name=name,
                vat=vat,
                phone=phone,
                email=email,
                address=address,
                q_fold=q_fold,
            )
        ]
        qs = Customer.objects.filter(pk__in=pks)
        if not show_inactive:
            qs = qs.filter(is_active=True)
    return qs.order_by("name")
