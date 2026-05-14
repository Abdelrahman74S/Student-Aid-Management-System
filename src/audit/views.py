from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.generic import ListView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count
from django.utils.translation import gettext_lazy as _

# استيراد النماذج
from .models import (
    DataAuditLog,
    ProcessActionLog,
    AccessLog,
    BudgetAuditLog,
    SystemOverrideLog,
    FinancialIntegrityLog,
    ApplicationHistory,
)
from accounts.models import User, StudentProfile, Program, UserRoles
from accounts.mixins import AuditorRequiredMixin, RoleRequiredMixin
from .filters import DataAuditFilter, AccessLogFilter


# ==========================================
# ميكسن الصلاحيات المطور
# ==========================================
class AuditStaffRequiredMixin(RoleRequiredMixin):
    """يسمح للمراقبين والمديرين بالوصول لسجلات التدقيق"""

    allowed_roles = [UserRoles.AUDITOR, UserRoles.ADMIN]

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        # السماح للمراقب أو المدير العام أو أي Superuser
        if request.user.role in self.allowed_roles or request.user.is_superuser:
            return super(RoleRequiredMixin, self).dispatch(request, *args, **kwargs)

        messages.error(
            request, "عذراً، هذه السجلات حساسة ومتاحة فقط للمراقبين والإدارة العليا."
        )
        return redirect("accounts:dashboard")


# ==========================================
# 1. لوحة تحكم التدقيق (Dashboard)
# ==========================================
class AuditDashboardView(AuditStaffRequiredMixin, TemplateView):
    template_name = "audit/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # إحصائيات سريعة
        context["stats"] = {
            "total_logs": DataAuditLog.objects.count(),
            "security_alerts": AccessLog.objects.filter(event_type="FAILED").count(),
            "overrides_count": SystemOverrideLog.objects.count(),
            "unbalanced_cycles": FinancialIntegrityLog.objects.filter(
                is_balanced=False
            ).count(),
        }
        # حالة التوازن المالي لآخر دورة
        context["integrity_check"] = (
            FinancialIntegrityLog.objects.select_related("cycle")
            .order_by("-timestamp")
            .first()
        )

        # توزيع العمليات للرسم البياني
        context["actions_summary"] = DataAuditLog.objects.values("action").annotate(
            total=Count("action")
        )

        return context


# ==========================================
# 2. سجل تعديلات البيانات (Advanced Filter)
# ==========================================
class DataAuditListView(AuditStaffRequiredMixin, ListView):
    model = DataAuditLog
    template_name = "audit/data_audit_list.html"
    context_object_name = "data_logs"
    paginate_by = 25

    def get_queryset(self):
        # 1. الاستعلام الأساسي مع تحسين الأداء
        queryset = (
            DataAuditLog.objects.select_related("user").all().order_by("-timestamp")
        )

        # 2. تطبيق الفلترة المتقدمة (Django Filter Logic)
        self.filterset = DataAuditFilter(self.request.GET, queryset=queryset)

        # 3. دعم الترتيب الديناميكي (Dynamic Ordering)
        order_by = self.request.GET.get("sort")
        if order_by in ["timestamp", "-timestamp", "action", "-action"]:
            return self.filterset.qs.order_by(order_by)

        return self.filterset.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter"] = self.filterset
        query_params = self.request.GET.copy()
        if "page" in query_params:
            query_params.pop("page")
        context["query_params"] = query_params.urlencode()
        return context


# ==========================================
# 3. سجل الوصول والأمان (Access Logs)
# ==========================================
class AccessLogListView(AuditStaffRequiredMixin, ListView):
    model = AccessLog
    template_name = "audit/access_log_list.html"
    context_object_name = "access_logs"
    paginate_by = 50

    def get_queryset(self):
        queryset = AccessLog.objects.select_related("user").all().order_by("-timestamp")
        self.filterset = AccessLogFilter(self.request.GET, queryset=queryset)
        return self.filterset.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter"] = self.filterset
        return context


# ==========================================
# 4. سجل التجاوزات الاستثنائية (Overrides)
# ==========================================
class OverrideLogListView(AuditStaffRequiredMixin, ListView):
    model = SystemOverrideLog
    template_name = "audit/override_log_list.html"
    context_object_name = "overrides"
    paginate_by = 20

    def get_queryset(self):
        return (
            SystemOverrideLog.objects.select_related("admin_user", "application")
            .all()
            .order_by("-timestamp")
        )


# ==========================================
# 5. السجل الزمني للحالات (Timeline)
# ==========================================
class AuditTimelineView(AuditStaffRequiredMixin, ListView):
    model = ApplicationHistory
    template_name = "audit/timeline.html"
    context_object_name = "history_events"
    paginate_by = 50

    def get_queryset(self):
        queryset = (
            ApplicationHistory.objects.select_related("application", "changed_by")
            .all()
            .order_by("-timestamp")
        )

        # بحث برقم تسلسل الطلب
        serial = self.request.GET.get("serial")
        if serial:
            queryset = queryset.filter(application__serial_number__icontains=serial)

        return queryset


# ==========================================
# 6. سجل الميزانية (Budget Audit)
# ==========================================
class BudgetAuditListView(AuditStaffRequiredMixin, ListView):
    model = BudgetAuditLog
    template_name = "audit/budget_audit_list.html"
    context_object_name = "budget_logs"

    def get_queryset(self):
        queryset = (
            BudgetAuditLog.objects.select_related("cycle", "user")
            .all()
            .order_by("-timestamp")
        )

        # فلترة متقدمة للعمليات الضخمة فقط (أكبر من مبلغ معين)
        min_amount = self.request.GET.get("min_amount")
        if min_amount:
            queryset = queryset.filter(amount_after__gte=min_amount)

        return queryset


# ==========================================
# 7. القرارات الإدارية (Process Actions)
# ==========================================
class ProcessActionListView(AuditStaffRequiredMixin, ListView):
    model = ProcessActionLog
    template_name = "audit/process_action_list.html"
    context_object_name = "process_actions"

    def get_queryset(self):
        return (
            ProcessActionLog.objects.select_related("user").all().order_by("-timestamp")
        )
