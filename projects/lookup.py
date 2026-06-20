"""Επιλογές dropdown από τη βάση — φόρτωση για φόρμες και φίλτρα."""

from __future__ import annotations

from django.db.models import QuerySet

from .models import LookupOption


def active_queryset(group: str) -> QuerySet[LookupOption]:
    return LookupOption.objects.filter(group=group, is_active=True)


def filter_choices(group: str, blank_label: str) -> list[tuple[str, str]]:
    return [("", blank_label)] + list(
        active_queryset(group).values_list("code", "label")
    )


def labels_map(group: str) -> dict[str, str]:
    return dict(LookupOption.objects.filter(group=group).values_list("code", "label"))


def label_for_id(option_id: int | None) -> str:
    if not option_id:
        return "—"
    return (
        LookupOption.objects.filter(pk=option_id).values_list("label", flat=True).first()
        or str(option_id)
    )
