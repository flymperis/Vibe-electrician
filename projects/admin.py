from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from .company import get_logo_spec
from .forms import CompanyProfileForm
from .models import (
    ActivityLog,
    CompanyProfile,
    Customer,
    Expense,
    Income,
    OperationalExpense,
    OperationalIncome,
    Project,
    Quote,
    QuoteLineItem,
    UserProfile,
    Role,
    AuthRole,
    WorkHours,
    WorkSchedule,
)
from .permissions import can_access_admin
from .role_permissions import (
    permission_groups_for_role,
    save_role_permissions,
)


class IncomeInline(admin.TabularInline):
    model = Income
    extra = 1
    fields = ("date", "amount", "income_type", "payment_method", "description")


class ExpenseInline(admin.TabularInline):
    model = Expense
    extra = 1
    fields = ("date", "amount", "category", "supplier", "description")
    verbose_name = "Έξοδο έργου"
    verbose_name_plural = "Έξοδα έργου"


class WorkHoursInline(admin.TabularInline):
    model = WorkHours
    extra = 1
    fields = ("date", "hours", "worker", "description")
    autocomplete_fields = ("worker",)


class CustomerResource(resources.ModelResource):
    class Meta:
        model = Customer
        fields = (
            "id",
            "name",
            "vat",
            "phone",
            "email",
            "address",
            "notes",
            "is_active",
        )


@admin.register(Customer)
class CustomerAdmin(ImportExportModelAdmin):
    resource_class = CustomerResource
    list_display = ("name", "vat", "phone", "email", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "vat", "phone", "email", "address")
    readonly_fields = ("created_at", "updated_at")


class ProjectResource(resources.ModelResource):
    class Meta:
        model = Project
        fields = (
            "id",
            "name",
            "client_name",
            "address",
            "status",
            "start_date",
            "end_date",
            "quoted_amount",
            "notes",
        )


@admin.register(Project)
class ProjectAdmin(ImportExportModelAdmin):
    resource_class = ProjectResource
    list_display = (
        "name",
        "client_name",
        "status",
        "start_date",
        "total_income_display",
        "total_expenses_display",
        "total_hours_display",
        "profit_display",
    )
    list_filter = ("status", "start_date")
    search_fields = ("name", "client_name", "address")
    inlines = [IncomeInline, ExpenseInline, WorkHoursInline]
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="Έσοδα")
    def total_income_display(self, obj):
        return f"{obj.total_income:.2f}€"

    @admin.display(description="Έξοδα έργου")
    def total_expenses_display(self, obj):
        return f"{obj.total_expenses:.2f}€"

    @admin.display(description="Εργατοώρες")
    def total_hours_display(self, obj):
        return f"{obj.total_hours:.1f}ωρ."

    @admin.display(description="Κέρδος έργου")
    def profit_display(self, obj):
        return f"{obj.profit:.2f}€"


class IncomeResource(resources.ModelResource):
    class Meta:
        model = Income
        fields = ("id", "project", "amount", "date", "income_type", "payment_method", "description")


@admin.register(Income)
class IncomeAdmin(ImportExportModelAdmin):
    resource_class = IncomeResource
    list_display = ("project", "date", "amount", "income_type", "payment_method", "description")
    list_filter = ("income_type", "payment_method", "date", "project")
    search_fields = ("project__name", "description")
    date_hierarchy = "date"


class ExpenseResource(resources.ModelResource):
    class Meta:
        model = Expense
        fields = (
            "id",
            "project",
            "category",
            "amount",
            "date",
            "supplier",
            "description",
        )


@admin.register(Expense)
class ExpenseAdmin(ImportExportModelAdmin):
    resource_class = ExpenseResource
    list_display = ("project", "date", "amount", "category", "supplier", "description")
    list_filter = ("category", "date", "project")
    search_fields = ("project__name", "supplier", "description")
    date_hierarchy = "date"


class OperationalExpenseResource(resources.ModelResource):
    class Meta:
        model = OperationalExpense
        fields = ("id", "category", "amount", "date", "supplier", "description")


@admin.register(OperationalExpense)
class OperationalExpenseAdmin(ImportExportModelAdmin):
    resource_class = OperationalExpenseResource
    list_display = ("date", "amount", "category", "supplier", "description")
    list_filter = ("category", "date")
    search_fields = ("supplier", "description")
    date_hierarchy = "date"


class OperationalIncomeResource(resources.ModelResource):
    class Meta:
        model = OperationalIncome
        fields = ("id", "category", "amount", "date", "source", "description")


@admin.register(OperationalIncome)
class OperationalIncomeAdmin(ImportExportModelAdmin):
    resource_class = OperationalIncomeResource
    list_display = ("date", "amount", "category", "source", "description")
    list_filter = ("category", "date")
    search_fields = ("source", "description")
    date_hierarchy = "date"


class WorkHoursResource(resources.ModelResource):
    class Meta:
        model = WorkHours
        fields = ("id", "project", "date", "hours", "worker", "description")


@admin.register(WorkHours)
class WorkHoursAdmin(ImportExportModelAdmin):
    resource_class = WorkHoursResource
    list_display = ("project", "date", "hours", "worker", "description")
    list_filter = ("date", "project")
    search_fields = (
        "project__name",
        "worker__username",
        "worker__first_name",
        "worker__last_name",
        "description",
    )
    autocomplete_fields = ("worker",)
    date_hierarchy = "date"


@admin.register(WorkSchedule)
class WorkScheduleAdmin(ImportExportModelAdmin):
    list_display = (
        "date",
        "title",
        "project",
        "status",
        "workers_display",
        "start_time",
        "end_time",
    )
    list_filter = ("status", "date", "project")
    search_fields = (
        "title",
        "location",
        "notes",
        "project__name",
        "workers__username",
        "workers__first_name",
        "workers__last_name",
    )
    filter_horizontal = ("workers",)
    date_hierarchy = "date"

    @admin.display(description="Εργαζόμενοι")
    def workers_display(self, obj):
        return obj.workers_label


class QuoteLineItemInline(admin.TabularInline):
    model = QuoteLineItem
    extra = 1
    fields = ("description", "category", "quantity", "unit", "unit_price")


@admin.register(Quote)
class QuoteAdmin(ImportExportModelAdmin):
    list_display = (
        "quote_number",
        "title",
        "client_name",
        "date",
        "status",
        "total_display",
    )
    list_filter = ("status", "date")
    search_fields = ("quote_number", "title", "client_name")
    inlines = [QuoteLineItemInline]
    readonly_fields = ("quote_number", "created_at", "updated_at")

    @admin.display(description="Σύνολο")
    def total_display(self, obj):
        return f"{obj.total:.2f}€"


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "summary", "details_preview")
    list_filter = ("action", "created_at")
    search_fields = ("summary", "object_repr", "details")
    date_hierarchy = "created_at"
    readonly_fields = (
        "created_at",
        "user",
        "action",
        "object_type",
        "object_id",
        "object_repr",
        "summary",
        "details_display",
    )
    fields = readonly_fields

    @admin.display(description="Λεπτομέρειες")
    def details_preview(self, obj):
        if not obj.details:
            return "—"
        first = obj.details[0]
        extra = len(obj.details) - 1
        if extra > 0:
            return f"{first} (+{extra})"
        return first

    @admin.display(description="Λεπτομέρειες αλλαγών")
    def details_display(self, obj):
        if not obj.details:
            return "—"
        return format_html(
            "<ul style='margin:0;padding-left:1.25rem'>{}</ul>",
            format_html_join(
                "",
                "<li>{}</li>",
                ((line,) for line in obj.details),
            ),
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    form = CompanyProfileForm
    fieldsets = (
        (
            "Ταυτότητα & λογότυπο",
            {
                "fields": ("name", "tagline", "logo_specs", "logo", "logo_preview"),
                "description": (
                    "Τα στοιχεία εμφανίζονται στην κεφαλίδα του PDF προσφοράς."
                ),
            },
        ),
        (
            "Επικοινωνία",
            {"fields": ("address", "phone", "email", "website", "vat")},
        ),
    )
    readonly_fields = ("logo_specs", "logo_preview")

    def has_add_permission(self, request):
        return not CompanyProfile.objects.filter(pk=1).exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        profile, _ = CompanyProfile.objects.get_or_create(pk=1)
        return redirect("admin:projects_companyprofile_change", profile.pk)

    @admin.display(description="Διαστάσεις λογότυπου")
    def logo_specs(self, obj):
        spec = get_logo_spec()
        current_html = ""
        if obj.logo:
            try:
                from PIL import Image

                with Image.open(obj.logo.path) as img:
                    w, h = img.size
                current_html = format_html(
                    "<p style='margin:0 0 8px;'><strong>Τρέχον αρχείο:</strong> {}×{} px</p>",
                    w,
                    h,
                )
            except (OSError, ValueError):
                pass

        return format_html(
            """
            <div class="logo-spec-box">
              {}
              <table style="border-collapse:collapse;font-size:13px;">
                <tr><td style="padding:4px 12px 4px 0;color:#666;">Προτεινόμενο upload</td>
                    <td><strong>{}×{} px</strong></td></tr>
                <tr><td style="padding:4px 12px 4px 0;color:#666;">Εμφάνιση στο PDF</td>
                    <td>έως {}×{} px</td></tr>
                <tr><td style="padding:4px 12px 4px 0;color:#666;">Ελάχιστο</td>
                    <td>{}×{} px</td></tr>
                <tr><td style="padding:4px 12px 4px 0;color:#666;">Μέγιστο upload</td>
                    <td>{}×{} px</td></tr>
                <tr><td style="padding:4px 12px 4px 0;color:#666;">Αναλογία</td>
                    <td>{} (οριζόντιο)</td></tr>
                <tr><td style="padding:4px 12px 4px 0;color:#666;">Μορφή</td>
                    <td>{}</td></tr>
              </table>
            </div>
            """,
            current_html,
            spec["recommended_width"],
            spec["recommended_height"],
            spec["pdf_width"],
            spec["pdf_height"],
            spec["min_width"],
            spec["min_height"],
            spec["max_width"],
            spec["max_height"],
            spec["aspect_ratio"],
            spec["formats"],
        )

    @admin.display(description="Προεπισκόπηση λογότυπου (PDF)")
    def logo_preview(self, obj):
        spec = get_logo_spec()
        if obj.logo:
            return format_html(
                '<p style="margin:0 0 6px;color:#666;font-size:12px;">'
                "Έτσι εμφανίζεται στο PDF (max {}×{} px):</p>"
                '<img src="{}" alt="logo" style="max-height:{}px; max-width:{}px; '
                'border:1px dashed #ccc; padding:4px; background:#f9fafb;" />',
                spec["pdf_width"],
                spec["pdf_height"],
                obj.logo.url,
                spec["pdf_height"],
                spec["pdf_width"],
            )
        return "—"


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    fk_name = "user"
    verbose_name_plural = "Ρόλος"
    fields = ("role", "language", "dark_mode", "must_change_password")
    extra = 0

    def has_add_permission(self, request, obj=None):
        # Το profile δημιουργείται από signal στο save του User — όχι δεύτερο inline insert.
        return False


class UserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]
    list_display = BaseUserAdmin.list_display + ("role_display",)

    @admin.display(description="Ρόλος")
    def role_display(self, obj):
        from .permissions import get_user_profile

        profile = get_user_profile(obj)
        if profile and profile.role_id:
            return profile.role.name
        return "—"


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role")
    list_filter = ("role",)
    search_fields = ("user__username", "user__first_name", "user__last_name")
    autocomplete_fields = ("user",)


@admin.register(AuthRole)
class AuthRoleAdmin(admin.ModelAdmin):
    change_form_template = "admin/auth/authrole/change_form.html"
    list_display = (
        "name",
        "code",
        "is_system",
        "is_assignable",
        "user_count",
        "sort_order",
    )
    list_filter = ("is_system", "is_assignable")
    search_fields = ("name", "code", "description")
    ordering = ("sort_order", "name")
    fields = ("name", "code", "description", "is_assignable", "sort_order", "is_system")

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj and obj.is_system:
            readonly.extend(["code", "is_system"])
        return readonly

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        role = self.get_object(request, object_id) if object_id else None
        extra_context["show_permissions"] = True
        extra_context["permission_groups"] = permission_groups_for_role(role)
        return super().changeform_view(request, object_id, form_url, extra_context)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        save_role_permissions(obj, request.POST)

    def has_module_permission(self, request):
        return request.user.is_active and (
            request.user.is_superuser or can_access_admin(request.user)
        )

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request):
        return self.has_module_permission(request)

    def has_change_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.is_system:
            return False
        return self.has_module_permission(request)

    @admin.display(description="Χρήστες")
    def user_count(self, obj):
        return obj.user_profiles.count()

    def delete_model(self, request, obj):
        if obj.user_profiles.exists():
            messages.error(request, f"Ο ρόλος «{obj.name}» έχει συνδεδεμένους χρήστες.")
            return
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        blocked = queryset.filter(is_system=True)
        if blocked.exists():
            messages.error(request, "Δεν διαγράφονται συστημικοί ρόλοι.")
            queryset = queryset.filter(is_system=False)
        for role in queryset:
            if role.user_profiles.exists():
                messages.error(
                    request,
                    f"Ο ρόλος «{role.name}» έχει συνδεδεμένους χρήστες και δεν διαγράφηκε.",
                )
                continue
            role.delete()
