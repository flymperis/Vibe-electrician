"""Κοινή λογική περιόδου για σελίδα & exports αναφορών."""

from datetime import date

from django.utils import timezone

MONTH_NAMES = (
    "",
    "Ιανουάριος",
    "Φεβρουάριος",
    "Μάρτιος",
    "Απρίλιος",
    "Μάιος",
    "Ιούνιος",
    "Ιούλιος",
    "Αύγουστος",
    "Σεπτέμβριος",
    "Οκτώβριος",
    "Νοέμβριος",
    "Δεκέμβριος",
)


def month_choices():
    return [(m, MONTH_NAMES[m]) for m in range(1, 13)]


def month_bounds(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return start, end


def year_bounds(year: int) -> tuple[date, date]:
    return date(year, 1, 1), date(year + 1, 1, 1)


def parse_report_period(request) -> dict:
    today = timezone.localdate()
    year = int(request.GET.get("year", today.year))
    month_raw = request.GET.get("month", str(today.month))

    if month_raw == "all":
        start, end = year_bounds(year)
        month: int | str = "all"
        period_label = f"Ολόκληρο το έτος {year}"
        period_slug = f"{year}_olo"
        is_full_year = True
    else:
        month = int(month_raw)
        start, end = month_bounds(year, month)
        period_label = f"{MONTH_NAMES[month]} {year}"
        period_slug = f"{year}_{month:02d}"
        is_full_year = False

    return {
        "year": year,
        "month": month,
        "start": start,
        "end": end,
        "period_label": period_label,
        "period_slug": period_slug,
        "is_full_year": is_full_year,
    }
