from django.contrib import admin

from projects.models import LookupOption

from .models import (
    IncomePaymentTypeOption,
    IncomeTypeOption,
    OperationalExpenseCategoryOption,
    OperationalIncomeCategoryOption,
    ProjectExpenseCategoryOption,
    QuoteLineCategoryOption,
    QuoteUnitOption,
)


class LookupOptionAdminBase(admin.ModelAdmin):
    group: str = ""
    list_display = ("label", "code", "sort_order", "is_active")
    list_editable = ("sort_order", "is_active")
    ordering = ("sort_order", "label")
    fields = ("code", "label", "sort_order", "is_active")

    def get_queryset(self, request):
        return super().get_queryset(request).filter(group=self.group)

    def save_model(self, request, obj, form, change):
        obj.group = self.group
        super().save_model(request, obj, form, change)


@admin.register(IncomeTypeOption)
class IncomeTypeOptionAdmin(LookupOptionAdminBase):
    group = LookupOption.GROUP_INCOME_TYPE


@admin.register(IncomePaymentTypeOption)
class IncomePaymentTypeOptionAdmin(LookupOptionAdminBase):
    group = LookupOption.GROUP_PAYMENT_TYPE


@admin.register(ProjectExpenseCategoryOption)
class ProjectExpenseCategoryOptionAdmin(LookupOptionAdminBase):
    group = LookupOption.GROUP_PROJECT_EXPENSE


@admin.register(OperationalExpenseCategoryOption)
class OperationalExpenseCategoryOptionAdmin(LookupOptionAdminBase):
    group = LookupOption.GROUP_OPERATIONAL_EXPENSE


@admin.register(OperationalIncomeCategoryOption)
class OperationalIncomeCategoryOptionAdmin(LookupOptionAdminBase):
    group = LookupOption.GROUP_OPERATIONAL_INCOME


@admin.register(QuoteLineCategoryOption)
class QuoteLineCategoryOptionAdmin(LookupOptionAdminBase):
    group = LookupOption.GROUP_QUOTE_LINE_CATEGORY


@admin.register(QuoteUnitOption)
class QuoteUnitOptionAdmin(LookupOptionAdminBase):
    group = LookupOption.GROUP_QUOTE_UNIT
