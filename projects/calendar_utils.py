"""Βοηθητικά για το ημερολόγιο εργασιών."""

from __future__ import annotations

import calendar
from datetime import date, timedelta

from django.utils import timezone

from .report_period import MONTH_NAMES

WEEKDAY_LABELS = ("Δευ", "Τρί", "Τετ", "Πέμ", "Παρ", "Σάβ", "Κυρ")


def parse_calendar_month(request) -> dict:
    today = timezone.localdate()
    try:
        year = int(request.GET.get("year", today.year))
    except (TypeError, ValueError):
        year = today.year
    try:
        month = int(request.GET.get("month", today.month))
    except (TypeError, ValueError):
        month = today.month
    if month < 1:
        month = 1
    if month > 12:
        month = 12
    if year < 1990:
        year = 1990
    if year > today.year + 10:
        year = today.year + 10

    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1

    return {
        "year": year,
        "month": month,
        "month_label": f"{MONTH_NAMES[month]} {year}",
        "today": today,
        "prev_year": prev_year,
        "prev_month": prev_month,
        "next_year": next_year,
        "next_month": next_month,
    }


def parse_selected_date(request, *, year: int, month: int, today: date) -> date | None:
    raw = (request.GET.get("day") or "").strip()
    if raw:
        try:
            parts = raw.split("-")
            if len(parts) == 3:
                selected = date(int(parts[0]), int(parts[1]), int(parts[2]))
                return selected
        except (TypeError, ValueError):
            pass
    if today.year == year and today.month == month:
        return today
    return None


def build_calendar_weeks(year: int, month: int) -> list[list[date]]:
    cal = calendar.Calendar(firstweekday=0)
    return cal.monthdatescalendar(year, month)


def weekday_label(day: date) -> str:
    return WEEKDAY_LABELS[day.weekday()]


def build_forward_days(today: date, *, extra_days: int = 6) -> list[date]:
    """Σήμερα και τις επόμενες extra_days ημέρες (7 σύνολο με default)."""
    return [today + timedelta(days=offset) for offset in range(extra_days + 1)]


def format_week_range_label(week_days: list[date]) -> str:
    start = week_days[0]
    end = week_days[-1]
    if start.year != end.year:
        return (
            f"{start.day} {MONTH_NAMES[start.month]} {start.year} – "
            f"{end.day} {MONTH_NAMES[end.month]} {end.year}"
        )
    if start.month != end.month:
        return f"{start.day} {MONTH_NAMES[start.month]} – {end.day} {MONTH_NAMES[end.month]} {end.year}"
    return f"{start.day}–{end.day} {MONTH_NAMES[start.month]} {start.year}"
