from datetime import date, timedelta
from decimal import Decimal
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .calendar_utils import (
    WEEKDAY_LABELS,
    build_calendar_weeks,
    build_forward_days,
    format_week_range_label,
    parse_calendar_month,
    parse_selected_date,
    weekday_label,
)
from .ui_strings import get_ui
from .permissions import (
    can_manage_schedules,
    owner_required,
    schedule_manager_required,
    user_display_name,
)
from .filters import (
    build_projects_summary,
    filter_customers,
    filter_operational_expenses,
    filter_operational_incomes,
    filter_projects,
    filter_quotes,
    get_filter_params,
)
from .forms import (
    CustomerFilterForm,
    CustomerForm,
    OperationalExpenseForm,
    OperationalIncomeForm,
    OperationalPageFilterForm,
    ProjectExpenseForm,
    ProjectFilterForm,
    ProjectForm,
    ProjectIncomeForm,
    QuoteFilterForm,
    QuoteForm,
    make_quote_line_formset,
    WorkHoursForm,
    WorkScheduleForm,
    UserPreferencesForm,
)
from .activity_log import (
    customer_field_snapshot,
    expense_snapshot,
    income_snapshot,
    log_customer_created,
    log_customer_deactivated,
    log_customer_updated,
    log_expense_created,
    log_expense_deleted,
    log_expense_updated,
    log_income_created,
    log_income_deleted,
    log_income_updated,
    log_operational_expense_created,
    log_operational_income_created,
    log_project_created,
    log_project_deleted,
    log_project_status_updated,
    log_project_updated,
    log_quote_created,
    log_quote_deleted,
    log_quote_updated,
    log_work_hours_created,
    log_work_schedule_created,
    log_work_schedule_deleted,
    log_work_schedule_updated,
    project_field_snapshot,
    quote_field_snapshot,
    quote_lines_snapshot,
    work_schedule_snapshot,
)
from .delete_confirm import password_confirmed_for_delete, redirect_after_failed_delete
from .models import (
    Customer,
    Expense,
    Income,
    OperationalExpense,
    OperationalIncome,
    Project,
    Quote,
    WorkHours,
    WorkSchedule,
)

User = get_user_model()

from .report_period import MONTH_NAMES, month_choices, parse_report_period

OPEN_DASHBOARD_STATUSES = (Project.STATUS_QUOTE, Project.STATUS_IN_PROGRESS)


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return start, end


def _redirect_preserve_get(request, view_name, **kwargs):
    url = reverse(view_name, kwargs=kwargs)
    if request.GET:
        url = f"{url}?{request.GET.urlencode()}"
    return redirect(url)


def _project_detail_url(project_pk, request):
    url = reverse("projects:project_detail", kwargs={"pk": project_pk})
    if request.GET:
        url = f"{url}?{request.GET.urlencode()}"
    return url


def _require_project_tracking(request, project):
    if project.accepts_work_entries:
        return True
    messages.warning(
        request,
        "Έσοδα και έξοδα διαχειρίζονται αφού ο πελάτης αποδεχτεί την προσφορά.",
    )
    return False


OPERATIONAL_PAGE_SIZE = 15


def _paginate(
    request,
    queryset,
    page_param: str,
    *,
    per_page: int = OPERATIONAL_PAGE_SIZE,
    anchor: str = "",
):
    paginator = Paginator(queryset, per_page)
    page_obj = paginator.get_page(request.GET.get(page_param))
    nav: dict[str, str] = {}
    hash_suffix = f"#{anchor}" if anchor else ""
    if page_obj.has_previous():
        params = request.GET.copy()
        params[page_param] = page_obj.previous_page_number()
        nav["previous"] = "?" + params.urlencode() + hash_suffix
    if page_obj.has_next():
        params = request.GET.copy()
        params[page_param] = page_obj.next_page_number()
        nav["next"] = "?" + params.urlencode() + hash_suffix
    return page_obj, nav


def _calendar_url(
    *,
    year: int,
    month: int,
    day: date | None = None,
    filter_params: dict[str, str] | None = None,
) -> str:
    params: dict[str, str | int] = {"year": year, "month": month}
    if day:
        params["day"] = day.isoformat()
    if filter_params:
        params.update(filter_params)
    query = urlencode(params)
    return f"{reverse('projects:work_calendar')}?{query}"


def _resolve_customer_prefill(request):
    raw = (request.GET.get("customer") or "").strip()
    if not raw.isdigit():
        return None
    return Customer.objects.filter(pk=int(raw), is_active=True).first()


@owner_required
def customer_list(request):
    filter_form = CustomerFilterForm(request.GET or None)
    customers = Customer.objects.all()
    filter_active = False
    if filter_form.is_valid():
        data = filter_form.cleaned_data
        customers = filter_customers(
            customers,
            q=data["q"],
            show_inactive=data.get("show_inactive"),
        )
        filter_active = bool(data["q"] or data.get("show_inactive"))
    else:
        customers = customers.filter(is_active=True).order_by("name")

    return render(
        request,
        "projects/customer_list.html",
        {
            "customers": customers,
            "filter_form": filter_form,
            "filter_active": filter_active,
            "result_count": customers.count(),
            "clear_url": reverse("projects:customer_list"),
        },
    )


@owner_required
def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    quotes = customer.quotes.select_related("project").order_by("-date", "-created_at")
    projects = customer.projects.order_by("-updated_at")
    return render(
        request,
        "projects/customer_detail.html",
        {
            "customer": customer,
            "quotes": quotes,
            "projects": projects,
        },
    )


@owner_required
def customer_create(request):
    form = CustomerForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        customer = form.save()
        log_customer_created(request, customer)
        messages.success(request, f"Δημιουργήθηκε ο πελάτης «{customer.name}».")
        next_url = request.GET.get("next")
        if next_url == "quote":
            return redirect(f"{reverse('projects:quote_create')}?customer={customer.pk}")
        return redirect("projects:customer_detail", pk=customer.pk)
    return render(
        request,
        "projects/customer_form.html",
        {
            "form": form,
            "title": "Νέος πελάτης",
            "subtitle": "Καταχώρηση στο πελατολόγιο",
            "cancel_url": reverse("projects:customer_list"),
        },
    )


@owner_required
def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    before = None
    if request.method == "POST":
        before = customer_field_snapshot(customer)
    form = CustomerForm(request.POST or None, instance=customer)
    if request.method == "POST" and form.is_valid():
        customer = form.save()
        log_customer_updated(request, customer, before)
        messages.success(request, f"Ο πελάτης «{customer.name}» ενημερώθηκε.")
        return redirect("projects:customer_detail", pk=customer.pk)
    return render(
        request,
        "projects/customer_form.html",
        {
            "form": form,
            "customer": customer,
            "title": f"Επεξεργασία — {customer.name}",
            "cancel_url": reverse("projects:customer_detail", kwargs={"pk": customer.pk}),
        },
    )


@owner_required
def customer_deactivate(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method != "POST":
        return redirect("projects:customer_detail", pk=pk)
    if not customer.is_active:
        messages.info(request, "Ο πελάτης είναι ήδη ανενεργός.")
        return redirect("projects:customer_detail", pk=pk)
    customer.is_active = False
    customer.save(update_fields=["is_active", "updated_at"])
    log_customer_deactivated(request, customer)
    messages.success(request, f"Ο πελάτης «{customer.name}» απενεργοποιήθηκε.")
    return redirect("projects:customer_list")


@owner_required
def customer_json(request, pk):
    customer = get_object_or_404(Customer, pk=pk, is_active=True)
    return JsonResponse(customer.to_quote_snapshot())


@owner_required
def customer_search(request):
    q = request.GET.get("q", "").strip()
    if len(q) < 2:
        return JsonResponse({"results": []})
    customers = filter_customers(
        Customer.objects.filter(is_active=True),
        q=q,
        show_inactive=False,
    )[:20]
    results = [
        {
            "id": customer.pk,
            "label": customer.display_label,
            **customer.to_quote_snapshot(),
        }
        for customer in customers
    ]
    return JsonResponse({"results": results})


def _apply_project_filters(request):
    filter_form = ProjectFilterForm(request.GET or None)
    if filter_form.is_valid():
        data = filter_form.cleaned_data
        statuses = data.get("status") or []
        qs = filter_projects(
            Project.objects.all(),
            q=data["q"],
            statuses=statuses,
            date_from=data.get("date_from"),
            date_to=data.get("date_to"),
            sort=data["sort"] or "-updated",
        )
        filter_active = bool(
            data["q"]
            or statuses
            or data.get("date_from")
            or data.get("date_to")
            or data["sort"] not in ("", "-updated")
        )
        return qs, filter_form, filter_active, qs.count()
    return Project.objects.all().order_by("-updated_at"), filter_form, False, Project.objects.count()


@owner_required
def dashboard(request):
    today = timezone.localdate()
    week_days = build_forward_days(today)
    week_start = week_days[0]
    week_end = week_days[-1] + timedelta(days=1)

    schedules_qs = (
        WorkSchedule.objects.filter(date__gte=week_start, date__lt=week_end)
        .select_related("project")
        .prefetch_related("workers")
        .order_by("date", "start_time", "title")
    )
    schedules_by_date: dict[date, list[WorkSchedule]] = {}
    for schedule in schedules_qs:
        schedules_by_date.setdefault(schedule.date, []).append(schedule)

    dashboard_week_days = []
    for day in week_days:
        day_schedules = schedules_by_date.get(day, [])
        dashboard_week_days.append(
            {
                "date": day,
                "is_today": day == today,
                "schedules": day_schedules[:3],
                "extra_count": max(0, len(day_schedules) - 3),
                "url": _calendar_url(year=day.year, month=day.month, day=day),
            }
        )

    context = {
        "today": today,
        "weekday_labels": [weekday_label(day) for day in week_days],
        "dashboard_week_days": dashboard_week_days,
        "current_week_label": format_week_range_label(week_days),
        "calendar_url": _calendar_url(year=today.year, month=today.month, day=today),
        "active_projects_count": Project.objects.filter(
            status__in=OPEN_DASHBOARD_STATUSES
        ).count(),
        "open_quotes_count": Quote.objects.filter(
            status__in=(Quote.STATUS_DRAFT, Quote.STATUS_SENT)
        ).count(),
        "open_projects_url": (
            f"{reverse('projects:project_list')}?{urlencode([('status', Project.STATUS_QUOTE), ('status', Project.STATUS_IN_PROGRESS)], doseq=True)}"
        ),
        "open_quotes_url": (
            f"{reverse('projects:quote_list')}?{urlencode([('status', Quote.STATUS_DRAFT), ('status', Quote.STATUS_SENT)], doseq=True)}"
        ),
    }
    return render(request, "projects/dashboard.html", context)


@owner_required
def project_list(request):
    projects_qs, filter_form, filter_active, result_count = _apply_project_filters(request)
    projects_qs = projects_qs.select_related("quote")
    context = {
        "projects": projects_qs,
        "filter_form": filter_form,
        "filter_active": filter_active,
        "result_count": result_count,
        "clear_url": reverse("projects:project_list"),
    }
    return render(request, "projects/project_list.html", context)


@owner_required
def project_create(request):
    if request.GET.get("manual"):
        form = ProjectForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            project = form.save()
            log_project_created(request, project)
            messages.success(request, f"Δημιουργήθηκε το έργο «{project.name}».")
            return redirect("projects:project_detail", pk=project.pk)
        return render(
            request,
            "projects/project_form.html",
            {
                "form": form,
                "title": "Νέο έργο (χειροκίνητα)",
                "subtitle": "Κανονικά το έργο δημιουργείται από προσφορά. Χρησιμοποίησε αυτό μόνο για εξαιρέσεις.",
            },
        )

    quotes = (
        Quote.objects.filter(project__isnull=True)
        .exclude(status=Quote.STATUS_REJECTED)
        .order_by("-date", "-created_at")
    )
    return render(
        request,
        "projects/project_create.html",
        {
            "quotes": quotes,
        },
    )


@owner_required
def project_edit(request, pk):
    project = get_object_or_404(Project, pk=pk)
    before = None
    if request.method == "POST":
        before = project_field_snapshot(project)
    form = ProjectForm(request.POST or None, instance=project)
    if request.method == "POST" and form.is_valid():
        project = form.save()
        log_project_updated(request, project, before)
        messages.success(request, f"Το έργο «{project.name}» ενημερώθηκε.")
        return redirect("projects:project_detail", pk=project.pk)
    return render(
        request,
        "projects/project_form.html",
        {
            "form": form,
            "project": project,
            "title": f"Επεξεργασία — {project.name}",
        },
    )


@owner_required
def project_update_status(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method != "POST":
        return redirect("projects:project_detail", pk=pk)

    new_status = request.POST.get("status")
    valid = {s[0] for s in Project.STATUS_CHOICES}
    if new_status in valid and new_status != project.status:
        before = project_field_snapshot(project)
        quote = getattr(project, "quote", None)
        if new_status == Project.STATUS_IN_PROGRESS and project.is_pre_job:
            messages.warning(
                request,
                "Το έργο ξεκινά από την προσφορά με «Δημιουργία έργου».",
            )
            return redirect("projects:project_detail", pk=pk)

        project.status = new_status
        today = timezone.localdate()
        if new_status == Project.STATUS_IN_PROGRESS and not project.start_date:
            project.start_date = today
        if new_status == Project.STATUS_COMPLETED:
            if not project.end_date:
                project.end_date = today
        else:
            project.end_date = None
        project.save(update_fields=["status", "start_date", "end_date", "updated_at"])
        log_project_status_updated(request, project, before)
        messages.success(request, f"Κατάσταση έργου: {project.get_status_display()}.")

    return redirect("projects:project_detail", pk=pk)


@owner_required
def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method != "POST":
        return redirect("projects:project_detail", pk=pk)

    if not password_confirmed_for_delete(request):
        return redirect_after_failed_delete(
            request,
            fallback=reverse("projects:project_detail", kwargs={"pk": pk}),
        )

    project_name = project.name
    log_project_deleted(request, project)
    project.delete()
    messages.success(request, f"Διαγράφηκε το έργο «{project_name}».")
    return redirect("projects:project_list")


@owner_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    post_url = request.path

    incomes = project.incomes.select_related("income_type", "payment_method").order_by("-date", "-pk")
    expenses = project.expenses.select_related("category").order_by("-date", "-pk")
    work_hours_entries = (
        project.work_hours.select_related("worker", "worker__profile").order_by("-date", "-pk")
    )

    expense_form = ProjectExpenseForm(project=project)
    income_form = ProjectIncomeForm(project=project)
    work_hours_form = WorkHoursForm(project=project)

    quote = getattr(project, "quote", None)

    if request.method == "POST":
        form_type = request.POST.get("form_type")
        if form_type in ("expense", "income", "work_hours") and not project.accepts_work_entries:
            messages.warning(
                request,
                "Έσοδα, έξοδα και εργατοώρες καταχωρούνται αφού ο πελάτης αποδεχτεί την προσφορά.",
            )
            return _redirect_preserve_get(request, "projects:project_detail", pk=project.pk)
        if form_type == "expense":
            expense_form = ProjectExpenseForm(request.POST, project=project)
            if expense_form.is_valid():
                expense = expense_form.save()
                log_expense_created(request, expense)
                messages.success(request, "Το έξοδο καταχωρήθηκε στο έργο.")
                return _redirect_preserve_get(request, "projects:project_detail", pk=project.pk)
        elif form_type == "income":
            income_form = ProjectIncomeForm(request.POST, project=project)
            if income_form.is_valid():
                income = income_form.save()
                log_income_created(request, income)
                messages.success(request, "Το έσοδο καταχωρήθηκε στο έργο.")
                return _redirect_preserve_get(request, "projects:project_detail", pk=project.pk)
        elif form_type == "work_hours":
            work_hours_form = WorkHoursForm(request.POST, project=project)
            if work_hours_form.is_valid():
                entry = work_hours_form.save()
                log_work_hours_created(request, entry)
                messages.success(request, "Οι εργατοώρες καταχωρήθηκαν.")
                return _redirect_preserve_get(request, "projects:project_detail", pk=project.pk)

    expenses_by_category = (
        expenses.values("category__code", "category__label")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )
    category_breakdown = [
        {
            "label": row["category__label"] or row["category__code"],
            "total": row["total"],
        }
        for row in expenses_by_category
    ]

    hours_by_worker_rows = (
        work_hours_entries.filter(worker__isnull=False)
        .values("worker")
        .annotate(total=Sum("hours"))
        .order_by("-total")
    )
    worker_ids = [row["worker"] for row in hours_by_worker_rows]
    worker_names = {
        user.pk: user_display_name(user)
        for user in get_user_model()
        .objects.filter(pk__in=worker_ids)
        .select_related("profile")
    }
    hours_by_worker = [
        {
            "worker_display": worker_names.get(row["worker"], "—"),
            "total": row["total"],
        }
        for row in hours_by_worker_rows
    ]

    upcoming_schedules = (
        project.work_schedules.filter(
            date__gte=timezone.localdate(),
            status=WorkSchedule.STATUS_SCHEDULED,
        )
        .order_by("date", "start_time", "title")[:5]
    )

    context = {
        "project": project,
        "quote": quote,
        "pre_job_phase": project.is_pre_job,
        "can_track_work": project.accepts_work_entries,
        "incomes": incomes,
        "expenses": expenses,
        "work_hours_entries": work_hours_entries,
        "hours_by_worker": hours_by_worker,
        "category_breakdown": category_breakdown,
        "expense_form": expense_form,
        "income_form": income_form,
        "work_hours_form": work_hours_form,
        "upcoming_schedules": upcoming_schedules,
        "post_url": post_url,
    }
    return render(request, "projects/project_detail.html", context)


@owner_required
def project_income_edit(request, project_pk, pk):
    project = get_object_or_404(Project, pk=project_pk)
    if not _require_project_tracking(request, project):
        return redirect("projects:project_detail", pk=project_pk)
    income = get_object_or_404(Income, pk=pk, project_id=project_pk)
    before = None
    if request.method == "POST":
        before = income_snapshot(income)
    form = ProjectIncomeForm(request.POST or None, instance=income, project=project)
    if request.method == "POST" and form.is_valid():
        income = form.save(commit=False)
        income.project = project
        income.save()
        log_income_updated(request, income, before)
        messages.success(request, "Το έσοδο ενημερώθηκε.")
        return _redirect_preserve_get(request, "projects:project_detail", pk=project_pk)
    return render(
        request,
        "projects/project_income_form.html",
        {
            "form": form,
            "project": project,
            "income": income,
            "title": "Επεξεργασία εσόδου",
            "cancel_url": _project_detail_url(project_pk, request),
        },
    )


@owner_required
def project_income_delete(request, project_pk, pk):
    project = get_object_or_404(Project, pk=project_pk)
    if not _require_project_tracking(request, project):
        return redirect("projects:project_detail", pk=project_pk)
    income = get_object_or_404(Income, pk=pk, project_id=project_pk)
    if request.method != "POST":
        return _redirect_preserve_get(request, "projects:project_detail", pk=project_pk)
    log_income_deleted(request, income)
    income.delete()
    messages.success(request, "Το έσοδο διαγράφηκε.")
    return _redirect_preserve_get(request, "projects:project_detail", pk=project_pk)


@owner_required
def project_expense_edit(request, project_pk, pk):
    project = get_object_or_404(Project, pk=project_pk)
    if not _require_project_tracking(request, project):
        return redirect("projects:project_detail", pk=project_pk)
    expense = get_object_or_404(Expense, pk=pk, project_id=project_pk)
    before = None
    if request.method == "POST":
        before = expense_snapshot(expense)
    form = ProjectExpenseForm(request.POST or None, instance=expense, project=project)
    if request.method == "POST" and form.is_valid():
        expense = form.save(commit=False)
        expense.project = project
        expense.save()
        log_expense_updated(request, expense, before)
        messages.success(request, "Το έξοδο ενημερώθηκε.")
        return _redirect_preserve_get(request, "projects:project_detail", pk=project_pk)
    return render(
        request,
        "projects/project_expense_form.html",
        {
            "form": form,
            "project": project,
            "expense": expense,
            "title": "Επεξεργασία εξόδου",
            "cancel_url": _project_detail_url(project_pk, request),
        },
    )


@owner_required
def project_expense_delete(request, project_pk, pk):
    project = get_object_or_404(Project, pk=project_pk)
    if not _require_project_tracking(request, project):
        return redirect("projects:project_detail", pk=project_pk)
    expense = get_object_or_404(Expense, pk=pk, project_id=project_pk)
    if request.method != "POST":
        return _redirect_preserve_get(request, "projects:project_detail", pk=project_pk)
    log_expense_deleted(request, expense)
    expense.delete()
    messages.success(request, "Το έξοδο διαγράφηκε.")
    return _redirect_preserve_get(request, "projects:project_detail", pk=project_pk)


@owner_required
def add_project_expense(request):
    form = ProjectExpenseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        project = form.cleaned_data["project"]
        if not project.accepts_work_entries:
            messages.warning(
                request,
                "Τα έξοδα καταχωρούνται μόνο σε έργα που έχουν ξεκινήσει (μετά αποδοχή προσφοράς).",
            )
            return redirect("projects:project_detail", pk=project.pk)
        expense = form.save()
        log_expense_created(request, expense)
        messages.success(
            request,
            f"Έξοδο {expense.amount}€ καταχωρήθηκε στο έργο «{expense.project.name}».",
        )
        return redirect("projects:project_detail", pk=expense.project.pk)
    return render(
        request,
        "projects/expense_form.html",
        {"form": form, "title": "Νέο έξοδο έργου"},
    )


@owner_required
def operational_expenses(request):
    filter_form = OperationalPageFilterForm(request.GET or None)
    expense_form = OperationalExpenseForm()
    income_form = OperationalIncomeForm()

    if request.method == "POST":
        form_type = request.POST.get("form_type", "expense")
        filter_params = {
            k.removeprefix("_filter_"): v
            for k, v in request.POST.items()
            if k.startswith("_filter_") and v
        }
        url = reverse("projects:operational_expenses")
        if filter_params:
            url = f"{url}?{urlencode(filter_params)}"

        if form_type == "income":
            income_form = OperationalIncomeForm(request.POST)
            if income_form.is_valid():
                operational_income = income_form.save()
                log_operational_income_created(request, operational_income)
                messages.success(request, "Το λειτουργικό έσοδο καταχωρήθηκε.")
                return redirect(url)
        else:
            expense_form = OperationalExpenseForm(request.POST)
            if expense_form.is_valid():
                operational = expense_form.save()
                log_operational_expense_created(request, operational)
                messages.success(request, "Το λειτουργικό έξοδο καταχωρήθηκε.")
                return redirect(url)

    expenses = OperationalExpense.objects.select_related("category").all()
    incomes = OperationalIncome.objects.select_related("category").all()
    filter_active = False
    shared_q = shared_date_from = shared_date_to = ""
    expense_category = income_category = ""

    if filter_form.is_valid():
        data = filter_form.cleaned_data
        shared_q = data["q"]
        shared_date_from = data["date_from"]
        shared_date_to = data["date_to"]
        expense_category = data["expense_category"]
        income_category = data["income_category"]
        filter_active = any(data.values())

    expenses = filter_operational_expenses(
        expenses,
        q=shared_q,
        category=expense_category,
        date_from=shared_date_from,
        date_to=shared_date_to,
    )
    incomes = filter_operational_incomes(
        incomes,
        q=shared_q,
        category=income_category,
        date_from=shared_date_from,
        date_to=shared_date_to,
    )

    expense_page, expense_pagination = _paginate(
        request,
        expenses,
        "expense_page",
        anchor="operational-expense-history",
    )
    income_page, income_pagination = _paginate(
        request,
        incomes,
        "income_page",
        anchor="operational-income-history",
    )

    today = timezone.localdate()
    month_expenses = OperationalExpense.objects.filter(
        date__year=today.year,
        date__month=today.month,
    )
    month_incomes = OperationalIncome.objects.filter(
        date__year=today.year,
        date__month=today.month,
    )
    month_expense_total = month_expenses.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    month_income_total = month_incomes.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    expense_by_category = (
        month_expenses.values("category__code", "category__label")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )
    income_by_category = (
        month_incomes.values("category__code", "category__label")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )

    context = {
        "expense_page": expense_page,
        "income_page": income_page,
        "expense_pagination": expense_pagination,
        "income_pagination": income_pagination,
        "expense_form": expense_form,
        "income_form": income_form,
        "filter_form": filter_form,
        "filter_active": filter_active,
        "result_count": expense_page.paginator.count + income_page.paginator.count,
        "clear_url": reverse("projects:operational_expenses"),
        "query_string": dict(request.GET.items()),
        "month_expense_total": month_expense_total,
        "month_income_total": month_income_total,
        "month_net_total": month_income_total - month_expense_total,
        "current_month_label": today.strftime("%B %Y"),
        "expense_category_breakdown": [
            {
                "label": row["category__label"] or row["category__code"],
                "total": row["total"],
            }
            for row in expense_by_category
        ],
        "income_category_breakdown": [
            {
                "label": row["category__label"] or row["category__code"],
                "total": row["total"],
            }
            for row in income_by_category
        ],
    }
    return render(request, "projects/operational.html", context)


@login_required
def work_calendar(request):
    period = parse_calendar_month(request)
    year = period["year"]
    month = period["month"]
    today = period["today"]

    weeks = build_calendar_weeks(year, month)
    grid_start = weeks[0][0]
    grid_end = weeks[-1][-1] + timedelta(days=1)

    schedules_qs = WorkSchedule.objects.filter(
        date__gte=grid_start,
        date__lt=grid_end,
    ).select_related("project").prefetch_related("workers")

    schedules_by_date: dict[date, list[WorkSchedule]] = {}
    for schedule in schedules_qs.order_by("date", "start_time", "title"):
        schedules_by_date.setdefault(schedule.date, []).append(schedule)

    selected_date = parse_selected_date(request, year=year, month=month, today=today)
    calendar_weeks = []
    for week in weeks:
        days = []
        for day in week:
            day_schedules = schedules_by_date.get(day, [])
            days.append(
                {
                    "date": day,
                    "in_month": day.month == month,
                    "is_today": day == today,
                    "is_selected": selected_date == day,
                    "schedules": day_schedules[:3],
                    "extra_count": max(0, len(day_schedules) - 3),
                    "url": _calendar_url(
                        year=year,
                        month=month,
                        day=day,
                    ),
                }
            )
        calendar_weeks.append(days)

    day_schedules = schedules_by_date.get(selected_date, []) if selected_date else []

    today_schedules = (
        WorkSchedule.objects.filter(date=today)
        .select_related("project")
        .prefetch_related("workers")
        .order_by("start_time", "title")
    )

    context = {
        "period": period,
        "weekday_labels": WEEKDAY_LABELS,
        "calendar_weeks": calendar_weeks,
        "selected_date": selected_date,
        "day_schedules": day_schedules,
        "today_schedules": today_schedules,
        "prev_url": _calendar_url(
            year=period["prev_year"],
            month=period["prev_month"],
            day=selected_date if selected_date and selected_date.month == period["prev_month"] else None,
        ),
        "next_url": _calendar_url(
            year=period["next_year"],
            month=period["next_month"],
            day=selected_date if selected_date and selected_date.month == period["next_month"] else None,
        ),
        "today_url": _calendar_url(year=today.year, month=today.month, day=today),
        "create_url": reverse("projects:work_schedule_create"),
        "can_manage_schedules": can_manage_schedules(request.user),
    }
    return render(request, "projects/work_calendar.html", context)


@schedule_manager_required
def work_schedule_create(request):
    default_date = None
    raw_day = (request.GET.get("day") or request.GET.get("date") or "").strip()
    if raw_day:
        try:
            parts = raw_day.split("-")
            if len(parts) == 3:
                default_date = date(int(parts[0]), int(parts[1]), int(parts[2]))
        except (TypeError, ValueError):
            default_date = None

    project = None
    project_id = (request.GET.get("project") or "").strip()
    if project_id.isdigit():
        project = Project.objects.filter(pk=int(project_id)).first()

    form = WorkScheduleForm(project=project, default_date=default_date, show_status=False)
    if request.method == "POST":
        form = WorkScheduleForm(request.POST, project=project, show_status=False)
        if form.is_valid():
            schedule = form.save()
            log_work_schedule_created(request, schedule)
            messages.success(request, "Η εργασία προγραμματίστηκε.")
            return redirect(
                _calendar_url(
                    year=schedule.date.year,
                    month=schedule.date.month,
                    day=schedule.date,
                )
            )

    cancel_url = reverse("projects:work_calendar")
    if default_date:
        cancel_url = _calendar_url(
            year=default_date.year,
            month=default_date.month,
            day=default_date,
        )

    return render(
        request,
        "projects/work_schedule_form.html",
        {
            "form": form,
            "title": "Νέα προγραμματισμένη εργασία",
            "cancel_url": cancel_url,
        },
    )


@schedule_manager_required
def work_schedule_edit(request, pk):
    schedule = get_object_or_404(WorkSchedule.objects.select_related("project"), pk=pk)
    before = None
    if request.method == "POST":
        before = work_schedule_snapshot(schedule)
    form = WorkScheduleForm(
        request.POST or None,
        instance=schedule,
        project=schedule.project,
        show_status=True,
    )
    if request.method == "POST" and form.is_valid():
        schedule = form.save()
        log_work_schedule_updated(request, schedule, before)
        messages.success(request, "Η εργασία ενημερώθηκε.")
        return redirect(
            _calendar_url(
                year=schedule.date.year,
                month=schedule.date.month,
                day=schedule.date,
            )
        )
    return render(
        request,
        "projects/work_schedule_form.html",
        {
            "form": form,
            "schedule": schedule,
            "title": "Επεξεργασία εργασίας",
            "cancel_url": _calendar_url(
                year=schedule.date.year,
                month=schedule.date.month,
                day=schedule.date,
            ),
        },
    )


@schedule_manager_required
def work_schedule_delete(request, pk):
    schedule = get_object_or_404(WorkSchedule, pk=pk)
    redirect_url = _calendar_url(year=schedule.date.year, month=schedule.date.month, day=schedule.date)
    if request.method == "POST":
        log_work_schedule_deleted(request, schedule)
        schedule.delete()
        messages.success(request, "Η εργασία διαγράφηκε.")
        return redirect(redirect_url)
    return render(
        request,
        "projects/work_schedule_confirm_delete.html",
        {"schedule": schedule, "cancel_url": redirect_url},
    )


@schedule_manager_required
def work_schedule_complete(request, pk):
    schedule = get_object_or_404(WorkSchedule.objects.select_related("project"), pk=pk)
    redirect_url = _calendar_url(year=schedule.date.year, month=schedule.date.month, day=schedule.date)
    if request.method != "POST":
        return redirect(redirect_url)
    before = work_schedule_snapshot(schedule)
    schedule.status = WorkSchedule.STATUS_COMPLETED
    schedule.save(update_fields=["status", "updated_at"])
    log_work_schedule_updated(request, schedule, before)
    messages.success(request, "Η εργασία σημειώθηκε ως ολοκληρωμένη.")
    if schedule.project_id:
        messages.info(
            request,
            f'Μπορείς να καταχωρήσεις εργατοώρες στο έργο «{schedule.project.name}».',
        )
    return redirect(redirect_url)


@owner_required
def monthly_report(request):
    period = parse_report_period(request)
    year = period["year"]
    month = period["month"]
    start = period["start"]
    end = period["end"]
    project_id = request.GET.get("project", "")
    search_q = request.GET.get("q", "").strip()

    incomes = Income.objects.filter(date__gte=start, date__lt=end)
    project_expenses = Expense.objects.filter(date__gte=start, date__lt=end)
    operational_expenses = OperationalExpense.objects.filter(date__gte=start, date__lt=end)
    operational_incomes = OperationalIncome.objects.filter(date__gte=start, date__lt=end)
    work_hours = WorkHours.objects.filter(date__gte=start, date__lt=end)

    if project_id:
        incomes = incomes.filter(project_id=project_id)
        project_expenses = project_expenses.filter(project_id=project_id)
        work_hours = work_hours.filter(project_id=project_id)
    if search_q:
        incomes = incomes.filter(
            Q(project__name__icontains=search_q) | Q(description__icontains=search_q)
        )
        project_expenses = project_expenses.filter(
            Q(project__name__icontains=search_q)
            | Q(supplier__icontains=search_q)
            | Q(description__icontains=search_q)
        )
        operational_expenses = operational_expenses.filter(
            Q(supplier__icontains=search_q) | Q(description__icontains=search_q)
        )
        operational_incomes = operational_incomes.filter(
            Q(source__icontains=search_q) | Q(description__icontains=search_q)
        )
        work_hours = work_hours.filter(
            Q(project__name__icontains=search_q) | Q(description__icontains=search_q)
        )

    total_income = incomes.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    total_income_cash = _sum_incomes_by_payment(incomes, Income.PAY_CASH)
    total_income_card = _sum_incomes_by_payment(incomes, Income.PAY_CARD)
    total_operational_incomes = operational_incomes.aggregate(total=Sum("amount"))[
        "total"
    ] or Decimal("0.00")
    total_project_expenses = project_expenses.aggregate(total=Sum("amount"))[
        "total"
    ] or Decimal("0.00")
    total_operational_expenses = operational_expenses.aggregate(total=Sum("amount"))[
        "total"
    ] or Decimal("0.00")
    total_work_hours = work_hours.aggregate(total=Sum("hours"))["total"] or Decimal("0.00")
    total_expenses = total_project_expenses + total_operational_expenses
    total_all_income = total_income + total_operational_incomes
    total_profit = total_all_income - total_expenses

    trend_data = _build_report_trend(year, period["is_full_year"], project_id, search_q)

    filter_active = bool(project_id or search_q)
    month_param = month if month == "all" else str(month)

    context = {
        "year": year,
        "month": month,
        "month_param": month_param,
        "month_label": period["period_label"],
        "is_full_year": period["is_full_year"],
        "trend_data": trend_data,
        "total_income": total_income,
        "total_income_cash": total_income_cash,
        "total_income_card": total_income_card,
        "total_operational_incomes": total_operational_incomes,
        "total_project_expenses": total_project_expenses,
        "total_operational_expenses": total_operational_expenses,
        "total_work_hours": total_work_hours,
        "total_profit": total_profit,
        "total_profit_margin": _profit_margin(total_all_income, total_profit),
        "years": range(timezone.localdate().year - 2, timezone.localdate().year + 2),
        "month_options": month_choices(),
        "projects": Project.objects.all(),
        "selected_project": project_id,
        "search_q": search_q,
        "filter_active": filter_active,
        "clear_url": f"{reverse('projects:monthly_report')}?year={year}&month={month_param}",
    }
    return render(request, "projects/monthly_report.html", context)


def _profit_margin(income: Decimal, profit: Decimal) -> Decimal | None:
    if income <= 0:
        return None
    return (profit / income) * 100


def _sum_incomes_by_payment(incomes, code: str) -> Decimal:
    return incomes.filter(payment_method__code=code).aggregate(total=Sum("amount"))[
        "total"
    ] or Decimal("0.00")


def _build_report_trend(year, is_full_year, project_id, search_q):
    today = timezone.localdate()
    last_month = 12 if year < today.year else today.month

    def totals_for_range(start, end):
        incomes = Income.objects.filter(date__gte=start, date__lt=end)
        project_exp = Expense.objects.filter(date__gte=start, date__lt=end)
        operational_exp = OperationalExpense.objects.filter(date__gte=start, date__lt=end)
        operational_inc = OperationalIncome.objects.filter(date__gte=start, date__lt=end)
        if project_id:
            incomes = incomes.filter(project_id=project_id)
            project_exp = project_exp.filter(project_id=project_id)
        if search_q:
            incomes = incomes.filter(
                Q(project__name__icontains=search_q) | Q(description__icontains=search_q)
            )
            project_exp = project_exp.filter(
                Q(project__name__icontains=search_q)
                | Q(supplier__icontains=search_q)
                | Q(description__icontains=search_q)
            )
            operational_exp = operational_exp.filter(
                Q(supplier__icontains=search_q) | Q(description__icontains=search_q)
            )
            operational_inc = operational_inc.filter(
                Q(source__icontains=search_q) | Q(description__icontains=search_q)
            )
        project_income = incomes.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        operational_income = operational_inc.aggregate(total=Sum("amount"))["total"] or Decimal(
            "0.00"
        )
        project_exp_total = project_exp.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        operational_exp_total = operational_exp.aggregate(total=Sum("amount"))["total"] or Decimal(
            "0.00"
        )
        return project_income, operational_income, project_exp_total, operational_exp_total

    def append_trend_row(label, project_income, operational_income, project_exp, operational_exp):
        total_income = project_income + operational_income
        expenses = project_exp + operational_exp
        profit = total_income - expenses
        trend_data.append(
            {
                "label": label,
                "income": project_income,
                "operational_incomes": operational_income,
                "project_expenses": project_exp,
                "operational_expenses": operational_exp,
                "expenses": expenses,
                "profit": profit,
                "margin": _profit_margin(total_income, profit),
            }
        )

    trend_data = []
    if is_full_year:
        for m in range(1, last_month + 1):
            start, end = _month_bounds(year, m)
            project_income, operational_income, project_exp, operational_exp = totals_for_range(
                start, end
            )
            append_trend_row(MONTH_NAMES[m], project_income, operational_income, project_exp, operational_exp)
    else:
        month_dates = _recent_report_months(project_id, search_q)
        for month_date in month_dates:
            start, end = _month_bounds(month_date.year, month_date.month)
            project_income, operational_income, project_exp, operational_exp = totals_for_range(
                start, end
            )
            append_trend_row(
                month_date.strftime("%m/%Y"),
                project_income,
                operational_income,
                project_exp,
                operational_exp,
            )

    return trend_data


def _recent_report_months(project_id, search_q, *, limit: int = 6):
    income_qs = Income.objects.all()
    project_exp_qs = Expense.objects.all()
    operational_exp_qs = OperationalExpense.objects.all()
    operational_inc_qs = OperationalIncome.objects.all()
    if project_id:
        income_qs = income_qs.filter(project_id=project_id)
        project_exp_qs = project_exp_qs.filter(project_id=project_id)
    if search_q:
        income_qs = income_qs.filter(
            Q(project__name__icontains=search_q) | Q(description__icontains=search_q)
        )
        project_exp_qs = project_exp_qs.filter(
            Q(project__name__icontains=search_q)
            | Q(supplier__icontains=search_q)
            | Q(description__icontains=search_q)
        )
        operational_exp_qs = operational_exp_qs.filter(
            Q(supplier__icontains=search_q) | Q(description__icontains=search_q)
        )
        operational_inc_qs = operational_inc_qs.filter(
            Q(source__icontains=search_q) | Q(description__icontains=search_q)
        )

    months: set[date] = set()
    for qs in (income_qs, project_exp_qs, operational_exp_qs, operational_inc_qs):
        for month_date in qs.annotate(month=TruncMonth("date")).values_list("month", flat=True):
            if month_date:
                months.add(month_date)
    return sorted(months, reverse=True)[:limit]


def _project_notes_from_quote(quote: Quote) -> str:
    parts = []
    if quote.notes:
        parts.append(quote.notes.strip())
    contact = []
    if quote.client_phone:
        contact.append(f"Τηλ.: {quote.client_phone}")
    if quote.client_vat:
        contact.append(f"ΑΦΜ: {quote.client_vat}")
    if quote.client_email:
        contact.append(f"Email: {quote.client_email}")
    if contact:
        parts.append(" · ".join(contact))
    return "\n".join(parts)


def _create_project_from_quote(quote: Quote) -> Project:
    """Δημιουργία έργου από αποδεκτή προσφορά — όλη η διαχείριση μετά από το έργο."""
    if quote.project_id:
        return quote.project

    today = timezone.localdate()
    project = Project.objects.create(
        name=quote.title.strip(),
        client_name=quote.client_name.strip(),
        customer=quote.customer,
        address=(quote.address or "").strip(),
        status=Project.STATUS_IN_PROGRESS,
        start_date=today,
        quoted_amount=quote.total,
        notes=_project_notes_from_quote(quote),
    )
    quote.project = project
    quote.status = Quote.STATUS_ACCEPTED
    quote.save(update_fields=["project", "status", "updated_at"])
    return project


def _sync_project_from_quote(quote: Quote) -> None:
    """Ενημέρωση έργου όταν αλλάζει η προσφορά (μόνο πριν ολοκληρωθεί)."""
    if not quote.project_id or quote.project.status == Project.STATUS_COMPLETED:
        return
    project = quote.project
    project.name = quote.title
    project.client_name = quote.client_name
    project.customer = quote.customer
    project.address = quote.address
    project.quoted_amount = quote.total
    project.notes = _project_notes_from_quote(quote)
    project.save(
        update_fields=[
            "name",
            "client_name",
            "customer",
            "address",
            "quoted_amount",
            "notes",
            "updated_at",
        ]
    )


def _save_quote_with_lines(request, quote=None, prefill_customer=None):
    is_create = quote is None
    before_quote = None
    before_lines = None
    if quote is not None and request.method == "POST":
        before_quote = quote_field_snapshot(quote)
        before_lines = quote_lines_snapshot(quote)

    FormSet = make_quote_line_formset(extra=1 if is_create else 0)
    form = QuoteForm(
        request.POST or None,
        instance=quote,
        prefill_customer=prefill_customer,
    )
    formset = FormSet(request.POST or None, instance=quote)
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        quote = form.save()
        formset.instance = quote
        formset.save()
        if quote.project_id:
            _sync_project_from_quote(quote)
        created_customer = getattr(form, "created_customer", None)
        if created_customer:
            log_customer_created(request, created_customer)
        if is_create:
            log_quote_created(request, quote)
        else:
            log_quote_updated(request, quote, before_quote, before_lines)
        return quote, form, formset, True, created_customer
    return quote, form, formset, False, None


@owner_required
def quote_list(request):
    filter_form = QuoteFilterForm(request.GET or None)
    quotes = Quote.objects.select_related("project").prefetch_related("line_items")
    filter_active = False
    if filter_form.is_valid():
        data = filter_form.cleaned_data
        statuses = data.get("status") or []
        quotes = filter_quotes(
            quotes,
            q=data["q"],
            statuses=statuses,
            date_from=data.get("date_from"),
            date_to=data.get("date_to"),
        )
        filter_active = bool(
            data["q"] or statuses or data.get("date_from") or data.get("date_to")
        )

    context = {
        "quotes": quotes,
        "filter_form": filter_form,
        "filter_active": filter_active,
        "result_count": quotes.count(),
        "clear_url": reverse("projects:quote_list"),
    }
    return render(request, "projects/quote_list.html", context)


@owner_required
def quote_select_project(request):
    return redirect("projects:quote_create")


@owner_required
def quote_create(request):
    prefill_customer = _resolve_customer_prefill(request)
    quote, form, formset, saved, created_customer = _save_quote_with_lines(
        request, prefill_customer=prefill_customer
    )
    if saved:
        if created_customer:
            messages.info(
                request,
                f"Δημιουργήθηκε νέος πελάτης «{created_customer.name}» στο πελατολόγιο.",
            )
        messages.success(request, f"Δημιουργήθηκε η προσφορά {quote.quote_number}.")
        return redirect("projects:quote_detail", pk=quote.pk)

    return render(
        request,
        "projects/quote_form.html",
        {
            "form": form,
            "formset": formset,
            "title": "Νέα προσφορά",
            "subtitle": "Στοιχεία πελάτη, γραμμές και κατάσταση (πρόχειρο / απεσταλμένη). Το έργο δημιουργείται όταν ο πελάτης το πάρει.",
            "is_create": True,
        },
    )


@owner_required
def quote_edit(request, pk):
    quote = get_object_or_404(Quote.objects.prefetch_related("line_items"), pk=pk)
    quote, form, formset, saved, created_customer = _save_quote_with_lines(request, quote=quote)
    if saved:
        if created_customer:
            messages.info(
                request,
                f"Δημιουργήθηκε νέος πελάτης «{created_customer.name}» στο πελατολόγιο.",
            )
        messages.success(request, "Η προσφορά ενημερώθηκε.")
        return redirect("projects:quote_detail", pk=quote.pk)
    return render(
        request,
        "projects/quote_form.html",
        {
            "form": form,
            "formset": formset,
            "quote": quote,
            "title": f"Επεξεργασία {quote.quote_number}",
            "is_create": False,
        },
    )


@owner_required
def quote_detail(request, pk):
    quote = get_object_or_404(
        Quote.objects.select_related("project").prefetch_related("line_items"), pk=pk
    )
    line_items = quote.line_items.all()
    return render(
        request,
        "projects/quote_detail.html",
        {
            "quote": quote,
            "line_items": line_items,
            "can_create_project": (
                not quote.project_id
                and quote.status != Quote.STATUS_REJECTED
            ),
            "has_project": bool(quote.project_id),
            "can_delete": quote.can_be_deleted,
        },
    )


@owner_required
def quote_delete(request, pk):
    quote = get_object_or_404(Quote, pk=pk)
    if request.method != "POST":
        return redirect("projects:quote_detail", pk=pk)

    if not quote.can_be_deleted:
        messages.error(
            request,
            "Δεν διαγράφεται — έχει ήδη δημιουργηθεί έργο από αυτή την προσφορά.",
        )
        return redirect("projects:quote_detail", pk=pk)

    if not password_confirmed_for_delete(request):
        return redirect_after_failed_delete(
            request,
            fallback=reverse("projects:quote_detail", kwargs={"pk": pk}),
        )

    quote_number = quote.quote_number
    log_quote_deleted(request, quote)
    quote.delete()
    messages.success(request, f"Διαγράφηκε η προσφορά {quote_number}.")
    return redirect("projects:quote_list")


@owner_required
def quote_link_project(request, pk):
    return redirect("projects:quote_detail", pk=pk)


@owner_required
def quote_create_project(request, pk):
    quote = get_object_or_404(
        Quote.objects.select_related("project").prefetch_related("line_items"), pk=pk
    )
    if request.method != "POST":
        return redirect("projects:quote_detail", pk=pk)

    if quote.project_id:
        messages.info(request, "Το έργο έχει ήδη δημιουργηθεί.")
        return redirect("projects:project_detail", pk=quote.project.pk)

    if quote.status == Quote.STATUS_REJECTED:
        messages.error(request, "Η προσφορά είναι απορριφθείσα — δεν δημιουργείται έργο.")
        return redirect("projects:quote_detail", pk=pk)

    project = _create_project_from_quote(quote)
    log_project_created(request, project, from_quote=quote)
    messages.success(
        request,
        f"Δημιουργήθηκε το έργο «{project.name}» — η διαχείριση γίνεται από εκεί.",
    )
    return redirect("projects:project_detail", pk=project.pk)


@owner_required
def quote_accept(request, pk):
    return quote_create_project(request, pk)


@owner_required
def quote_update_status(request, pk):
    quote = get_object_or_404(Quote, pk=pk)
    if request.method != "POST":
        return redirect("projects:quote_detail", pk=pk)

    new_status = request.POST.get("status")
    valid = {s[0] for s in Quote.STATUS_CHOICES}
    if quote.project_id:
        messages.warning(request, "Η κατάσταση της προσφοράς δεν αλλάζει μετά τη δημιουργία έργου.")
        return redirect("projects:quote_detail", pk=pk)

    if new_status in valid and new_status != Quote.STATUS_ACCEPTED:
        quote.status = new_status
        quote.save()
        messages.success(request, f"Κατάσταση: {quote.get_status_display()}.")
    return redirect("projects:quote_detail", pk=pk)


@login_required
def user_settings(request):
    from .permissions import get_user_profile
    from .role_permissions import ensure_system_roles

    ensure_system_roles()
    profile = get_user_profile(request.user)
    if profile is None:
        from .models import Role, UserProfile
        from .permissions import ROLE_ADMIN

        role = Role.by_code(ROLE_ADMIN if request.user.is_superuser else UserProfile.CODE_WORKER)
        profile = UserProfile.objects.create(user=request.user, role=role)

    ui = get_ui(profile.language)

    if request.method == "POST":
        form = UserPreferencesForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            ui = get_ui(profile.language)
            messages.success(request, ui.settings_saved)
            return redirect("projects:user_settings")
    else:
        form = UserPreferencesForm(instance=profile)

    return render(
        request,
        "projects/user_settings.html",
        {
            "form": form,
            "profile": profile,
            "page_ui": ui,
        },
    )
