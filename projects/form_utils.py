"""Κοινά widgets & έλεγχος ημερομηνιών για φόρμες."""

from datetime import date, datetime

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

DATE_INPUT_FORMAT = "%Y-%m-%d"
DATE_INPUT_FORMATS = [
    DATE_INPUT_FORMAT,
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d.%m.%Y",
]

MIN_YEAR = 1990


def _max_year(offset: int = 10) -> int:
    return timezone.localdate().year + offset


def date_widget(**attrs):
    merged = {
        "type": "date",
        "min": f"{MIN_YEAR}-01-01",
        "max": f"{_max_year()}-12-31",
    }
    merged.update(attrs)
    return forms.DateInput(format=DATE_INPUT_FORMAT, attrs=merged)


class ReasonableDateField(forms.DateField):
    """Έγκυρη ημερολογιακή ημερομηνία και λογικό εύρος ετών."""

    default_error_messages = {
        "invalid": (
            "Μη έγκυρη ημερομηνία. Χρησιμοποίησε μορφή ΗΗ/ΜΜ/ΕΕΕΕ "
            "(π.χ. 31/05/2026) ή το ημερολόγιο."
        ),
        "year_out_of_range": "Το έτος πρέπει να είναι μεταξύ %(min)s και %(max)s.",
    }

    def __init__(self, *, min_year: int = MIN_YEAR, max_year: int | None = None, **kwargs):
        self.min_year = min_year
        self.max_year = max_year if max_year is not None else _max_year()
        kwargs.setdefault("input_formats", DATE_INPUT_FORMATS)
        if "widget" not in kwargs:
            kwargs["widget"] = date_widget(
                min=f"{self.min_year}-01-01",
                max=f"{self.max_year}-12-31",
            )
        super().__init__(**kwargs)

    def to_python(self, value):
        if value in self.empty_values:
            return None
        if isinstance(value, datetime):
            value = value.date()
        if isinstance(value, date):
            parsed = value
        else:
            text = str(value).strip()
            parsed = None
            for fmt in self.input_formats:
                try:
                    parsed = datetime.strptime(text, fmt).date()
                    break
                except ValueError:
                    continue
            if parsed is None:
                raise ValidationError(self.error_messages["invalid"], code="invalid")

        if parsed.year < self.min_year or parsed.year > self.max_year:
            raise ValidationError(
                self.error_messages["year_out_of_range"],
                code="year_out_of_range",
                params={"min": self.min_year, "max": self.max_year},
            )
        return parsed


def apply_reasonable_date_fields(form, *field_names: str, **field_options):
    """Αντικαθιστά πεδία ημερομηνίας με ReasonableDateField."""
    for name in field_names:
        if name not in form.fields:
            continue
        old = form.fields[name]
        form.fields[name] = ReasonableDateField(
            required=old.required,
            label=old.label,
            help_text=old.help_text,
            initial=old.initial,
            **field_options,
        )


def validate_date_range_order(form, cleaned_data, from_key="date_from", to_key="date_to"):
    """Το «Από» πρέπει να είναι ≤ «Έως»."""
    start = cleaned_data.get(from_key)
    end = cleaned_data.get(to_key)
    if start and end and start > end:
        message = "Το «Από» πρέπει να είναι πριν ή ίσο με το «Έως»."
        form.add_error(from_key, message)
        form.add_error(to_key, message)
        return False
    return True


def set_default_today(form, *field_names):
    """Προεπιλογή σημερινής ημερομηνίας σε κενά πεδία (μόνο GET / νέα φόρμα)."""
    if form.data:
        return
    today = timezone.localdate()
    instance = getattr(form, "instance", None)
    for name in field_names:
        if name not in form.fields:
            continue
        if form.initial.get(name) is not None:
            continue
        if instance is not None and getattr(instance, name, None):
            continue
        form.fields[name].initial = today
