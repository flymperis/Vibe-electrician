"""Κατάλογος δικαιωμάτων και προεπιλεγμένες τιμές ανά ρόλο."""

from __future__ import annotations

from dataclasses import dataclass

PERM_ACCESS_DJANGO_ADMIN = "access_django_admin"
PERM_VIEW_DASHBOARD = "view_dashboard"
PERM_MANAGE_PROJECTS = "manage_projects"
PERM_MANAGE_CUSTOMERS = "manage_customers"
PERM_MANAGE_QUOTES = "manage_quotes"
PERM_MANAGE_PROJECT_FINANCES = "manage_project_finances"
PERM_MANAGE_OPERATIONAL = "manage_operational"
PERM_VIEW_CALENDAR = "view_calendar"
PERM_MANAGE_SCHEDULES = "manage_schedules"
PERM_VIEW_REPORTS = "view_reports"
PERM_EXPORT_REPORTS = "export_reports"

ALL_PERMISSION_CODES = (
    PERM_ACCESS_DJANGO_ADMIN,
    PERM_VIEW_DASHBOARD,
    PERM_MANAGE_PROJECTS,
    PERM_MANAGE_CUSTOMERS,
    PERM_MANAGE_QUOTES,
    PERM_MANAGE_PROJECT_FINANCES,
    PERM_MANAGE_OPERATIONAL,
    PERM_VIEW_CALENDAR,
    PERM_MANAGE_SCHEDULES,
    PERM_VIEW_REPORTS,
    PERM_EXPORT_REPORTS,
)

SYSTEM_ROLE_DEFAULTS: dict[str, dict[str, object]] = {
    "admin": {
        "name": "Διαχειριστής",
        "description": "Πλήρης πρόσβαση στο σύστημα και Django admin.",
        "is_system": True,
        "is_assignable": False,
        "sort_order": 1,
        "permissions": {code: True for code in ALL_PERMISSION_CODES},
    },
    "owner": {
        "name": "Ιδιοκτήτης",
        "description": "Διαχείριση έργων, οικονομικών, προσφορών και αναφορών.",
        "is_system": True,
        "is_assignable": True,
        "sort_order": 2,
        "permissions": {
            PERM_ACCESS_DJANGO_ADMIN: False,
            PERM_VIEW_DASHBOARD: True,
            PERM_MANAGE_PROJECTS: True,
            PERM_MANAGE_CUSTOMERS: True,
            PERM_MANAGE_QUOTES: True,
            PERM_MANAGE_PROJECT_FINANCES: True,
            PERM_MANAGE_OPERATIONAL: True,
            PERM_VIEW_CALENDAR: True,
            PERM_MANAGE_SCHEDULES: True,
            PERM_VIEW_REPORTS: True,
            PERM_EXPORT_REPORTS: True,
        },
    },
    "worker": {
        "name": "Εργαζόμενος",
        "description": "Πρόσβαση μόνο στο ημερολόγιο εργασιών.",
        "is_system": True,
        "is_assignable": True,
        "sort_order": 3,
        "permissions": {
            PERM_ACCESS_DJANGO_ADMIN: False,
            PERM_VIEW_DASHBOARD: False,
            PERM_MANAGE_PROJECTS: False,
            PERM_MANAGE_CUSTOMERS: False,
            PERM_MANAGE_QUOTES: False,
            PERM_MANAGE_PROJECT_FINANCES: False,
            PERM_MANAGE_OPERATIONAL: False,
            PERM_VIEW_CALENDAR: True,
            PERM_MANAGE_SCHEDULES: False,
            PERM_VIEW_REPORTS: False,
            PERM_EXPORT_REPORTS: False,
        },
    },
}


@dataclass(frozen=True)
class PermissionDefinition:
    code: str
    label: str
    group: str
    description: str = ""


PERMISSION_REGISTRY: tuple[PermissionDefinition, ...] = (
    PermissionDefinition(
        PERM_ACCESS_DJANGO_ADMIN,
        "Django Admin",
        "Σύστημα",
        "Πρόσβαση στο /admin/ (ρυθμίσεις, χρήστες, καταλόγοι).",
    ),
    PermissionDefinition(
        PERM_VIEW_DASHBOARD,
        "Dashboard",
        "Γενικά",
        "Αρχική σελίδα με σύνοψη εργασιών και οικονομικών.",
    ),
    PermissionDefinition(
        PERM_MANAGE_PROJECTS,
        "Έργα",
        "Έργα",
        "Προβολή, δημιουργία και επεξεργασία έργων.",
    ),
    PermissionDefinition(
        PERM_MANAGE_CUSTOMERS,
        "Πελάτες",
        "Πελάτες",
        "Διαχείριση καταλόγου πελατών.",
    ),
    PermissionDefinition(
        PERM_MANAGE_QUOTES,
        "Προσφορές",
        "Προσφορές",
        "Δημιουργία και διαχείριση προσφορών.",
    ),
    PermissionDefinition(
        PERM_MANAGE_PROJECT_FINANCES,
        "Έσοδα / έξοδα / ώρες έργου",
        "Οικονομικά",
        "Καταχώρηση εσόδων, εξόδων και εργατοωρών ανά έργο.",
    ),
    PermissionDefinition(
        PERM_MANAGE_OPERATIONAL,
        "Λειτουργικά",
        "Οικονομικά",
        "Λειτουργικά έσοδα και έξοδα.",
    ),
    PermissionDefinition(
        PERM_VIEW_CALENDAR,
        "Προβολή ημερολογίου",
        "Ημερολόγιο",
        "Προβολή προγραμματισμένων εργασιών.",
    ),
    PermissionDefinition(
        PERM_MANAGE_SCHEDULES,
        "Διαχείριση εργασιών",
        "Ημερολόγιο",
        "Δημιουργία, επεξεργασία και διαγραφή εργασιών.",
    ),
    PermissionDefinition(
        PERM_VIEW_REPORTS,
        "Αναφορές",
        "Αναφορές",
        "Μηνιαίες αναφορές και τάσεις.",
    ),
    PermissionDefinition(
        PERM_EXPORT_REPORTS,
        "Εξαγωγές PDF / Excel",
        "Αναφορές",
        "Λήψη αναφορών και προσφορών σε PDF ή Excel.",
    ),
)

URL_PERMISSION_MAP: dict[str, str | None] = {
    "dashboard": PERM_VIEW_DASHBOARD,
    "project_list": PERM_MANAGE_PROJECTS,
    "project_create": PERM_MANAGE_PROJECTS,
    "project_detail": PERM_MANAGE_PROJECTS,
    "project_edit": PERM_MANAGE_PROJECTS,
    "project_update_status": PERM_MANAGE_PROJECTS,
    "project_delete": PERM_MANAGE_PROJECTS,
    "project_income_edit": PERM_MANAGE_PROJECT_FINANCES,
    "project_income_delete": PERM_MANAGE_PROJECT_FINANCES,
    "project_expense_edit": PERM_MANAGE_PROJECT_FINANCES,
    "project_expense_delete": PERM_MANAGE_PROJECT_FINANCES,
    "add_project_expense": PERM_MANAGE_PROJECT_FINANCES,
    "customer_list": PERM_MANAGE_CUSTOMERS,
    "customer_create": PERM_MANAGE_CUSTOMERS,
    "customer_detail": PERM_MANAGE_CUSTOMERS,
    "customer_edit": PERM_MANAGE_CUSTOMERS,
    "customer_deactivate": PERM_MANAGE_CUSTOMERS,
    "customer_json": PERM_MANAGE_CUSTOMERS,
    "customer_search": PERM_MANAGE_CUSTOMERS,
    "operational_expenses": PERM_MANAGE_OPERATIONAL,
    "operational_expense_delete": PERM_MANAGE_OPERATIONAL,
    "operational_income_delete": PERM_MANAGE_OPERATIONAL,
    "work_calendar": PERM_VIEW_CALENDAR,
    "work_schedule_create": PERM_MANAGE_SCHEDULES,
    "work_schedule_edit": PERM_MANAGE_SCHEDULES,
    "work_schedule_delete": PERM_MANAGE_SCHEDULES,
    "work_schedule_complete": PERM_MANAGE_SCHEDULES,
    "monthly_report": PERM_VIEW_REPORTS,
    "quote_list": PERM_MANAGE_QUOTES,
    "quote_create": PERM_MANAGE_QUOTES,
    "quote_select_project": PERM_MANAGE_QUOTES,
    "quote_detail": PERM_MANAGE_QUOTES,
    "quote_link_project": PERM_MANAGE_QUOTES,
    "quote_edit": PERM_MANAGE_QUOTES,
    "quote_create_project": PERM_MANAGE_QUOTES,
    "quote_accept": PERM_MANAGE_QUOTES,
    "quote_update_status": PERM_MANAGE_QUOTES,
    "quote_delete": PERM_MANAGE_QUOTES,
    "project_pdf": PERM_EXPORT_REPORTS,
    "monthly_excel": PERM_EXPORT_REPORTS,
    "monthly_pdf": PERM_EXPORT_REPORTS,
    "quote_pdf": PERM_EXPORT_REPORTS,
    "login": None,
    "logout": None,
    "user_settings": None,
    "password_change_required": None,
}


def permissions_by_group() -> list[tuple[str, list[PermissionDefinition]]]:
    groups: dict[str, list[PermissionDefinition]] = {}
    order: list[str] = []
    for perm in PERMISSION_REGISTRY:
        if perm.group not in groups:
            groups[perm.group] = []
            order.append(perm.group)
        groups[perm.group].append(perm)
    return [(group, groups[group]) for group in order]


def ensure_system_roles() -> None:
    from .models import Role, RolePermission

    for code, spec in SYSTEM_ROLE_DEFAULTS.items():
        role, _ = Role.objects.update_or_create(
            code=code,
            defaults={
                "name": spec["name"],
                "description": spec["description"],
                "is_system": spec["is_system"],
                "is_assignable": spec["is_assignable"],
                "sort_order": spec["sort_order"],
            },
        )
        permission_map = spec["permissions"]
        for perm_code in ALL_PERMISSION_CODES:
            allowed = permission_map.get(perm_code, False)
            RolePermission.objects.update_or_create(
                role=role,
                permission=perm_code,
                defaults={"allowed": allowed},
            )


def ensure_role_permissions(role) -> None:
    from .models import RolePermission

    for code in ALL_PERMISSION_CODES:
        RolePermission.objects.get_or_create(
            role=role,
            permission=code,
            defaults={"allowed": False},
        )


def ensure_default_role_permissions() -> None:
    ensure_system_roles()


def permission_groups_for_role(role=None) -> list[tuple[str, list[dict]]]:
    from .models import RolePermission

    if role is not None and role.pk:
        ensure_role_permissions(role)
        matrix = {
            row.permission: row.allowed
            for row in RolePermission.objects.filter(role=role)
        }
    else:
        matrix = {}

    return [
        (
            group_name,
            [
                {
                    "definition": perm,
                    "allowed": matrix.get(perm.code, False),
                }
                for perm in perms
            ],
        )
        for group_name, perms in permissions_by_group()
    ]


def save_role_permissions(role, post_data) -> None:
    from .models import RolePermission
    from .permissions import clear_permission_cache

    ensure_role_permissions(role)
    for code in ALL_PERMISSION_CODES:
        allowed = post_data.get(f"perm_{code}") == "on"
        RolePermission.objects.update_or_create(
            role=role,
            permission=code,
            defaults={"allowed": allowed},
        )
    clear_permission_cache()
