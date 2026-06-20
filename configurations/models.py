from projects.models import LookupOption


class IncomeTypeOption(LookupOption):
    class Meta:
        proxy = True
        verbose_name = "Τύπος εσόδου"
        verbose_name_plural = "Τύποι εσόδου"


class IncomePaymentTypeOption(LookupOption):
    class Meta:
        proxy = True
        verbose_name = "Τύπος πληρωμής"
        verbose_name_plural = "Τύποι πληρωμής"


class ProjectExpenseCategoryOption(LookupOption):
    class Meta:
        proxy = True
        verbose_name = "Κατηγορία εξόδου έργου"
        verbose_name_plural = "Κατηγορίες εξόδου έργου"


class OperationalExpenseCategoryOption(LookupOption):
    class Meta:
        proxy = True
        verbose_name = "Κατηγορία λειτουργικού εξόδου"
        verbose_name_plural = "Κατηγορίες λειτουργικού εξόδου"


class OperationalIncomeCategoryOption(LookupOption):
    class Meta:
        proxy = True
        verbose_name = "Κατηγορία λειτουργικού εσόδου"
        verbose_name_plural = "Κατηγορίες λειτουργικού εσόδου"


class QuoteLineCategoryOption(LookupOption):
    class Meta:
        proxy = True
        verbose_name = "Κατηγορία γραμμής προσφοράς"
        verbose_name_plural = "Κατηγορίες γραμμής προσφοράς"


class QuoteUnitOption(LookupOption):
    class Meta:
        proxy = True
        verbose_name = "Μονάδα μέτρησης"
        verbose_name_plural = "Μονάδες μέτρησης"
