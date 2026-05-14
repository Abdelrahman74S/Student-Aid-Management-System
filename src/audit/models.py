import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from aid_management.models import AidApplication

# ==============================
# 1. سجل تغيير البيانات (DataAuditLog)
# ==============================
class DataAuditLog(models.Model):
    """يسجل أي عملية إضافة أو تعديل أو حذف للبيانات في قاعدة البيانات"""
    log_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name=_("المستخدم القائم بالإجراء"))
    entity_type = models.CharField(max_length=50, verbose_name=_("نوع الجدول")) # مثال: AidApplication
    entity_id = models.CharField(max_length=255, verbose_name=_("معرف السجل"))
    action = models.CharField(
        max_length=10, 
        choices=[
            ('CREATE', _('إضافة')), 
            ('UPDATE', _('تعديل')), 
            ('DELETE', _('حذف'))
        ],
        verbose_name=_("الإجراء")
    )
    
    old_values = models.JSONField(null=True, blank=True, verbose_name=_("البيانات قبل"))
    new_values = models.JSONField(null=True, blank=True, verbose_name=_("البيانات بعد"))
    
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_("وقت التعديل"))

    class Meta:
        verbose_name = _("سجل بيانات")
        verbose_name_plural = _("سجلات البيانات")

# ==============================
# 2. سجل القرارات الإدارية (ProcessActionLog)
# ==============================
class ProcessActionLog(models.Model):
    """يسجل الانتقالات الكبرى في السيستم (فتح دورة، إغلاق مراجعة، اعتماد ميزانية)"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action_name = models.CharField(max_length=100, verbose_name=_("الإجراء الإداري")) # مثال: "إغلاق دورة الدعم"
    cycle_name = models.CharField(max_length=255, null=True, blank=True)
    notes = models.TextField(verbose_name=_("مبررات القرار"))
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("سجل إجراء إداري")
        verbose_name_plural = _("سجل الإجراءات الإدارية")

# ==============================
# 3. سجل الوصول والأمان (AccessLog)
# ==============================
class AccessLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    event_type = models.CharField(max_length=20, choices=[('LOGIN', 'دخول'), ('LOGOUT', 'خروج'), ('FAILED', 'فشل دخول')])
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(verbose_name=_("بيانات المتصفح"))
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("سجل وصول")
        verbose_name_plural = _("سجلات الوصول")


class BudgetAuditLog(models.Model):
    cycle = models.ForeignKey('aid_management.SupportCycle', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    amount_before = models.DecimalField(max_digits=12, decimal_places=2)
    amount_after = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.CharField(max_length=255, verbose_name=_("سبب التغيير"))
    
    timestamp = models.DateTimeField(auto_now_add=True)

class SystemOverrideLog(models.Model):
    admin_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    application = models.ForeignKey('aid_management.AidApplication', on_delete=models.CASCADE)
    
    override_type = models.CharField(max_length=50, verbose_name=_("نوع التجاوز"))
    reason = models.TextField(verbose_name=_("السبب الإداري للتجاوز")) 
    
    previous_state = models.JSONField(verbose_name=_("الحالة السابقة"))
    new_state = models.JSONField(verbose_name=_("الحالة الجديدة"))
    
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("سجل تجاوز نظام")
        verbose_name_plural = _("سجلات التجاوزات الاستثنائية")

class FinancialIntegrityLog(models.Model):
    cycle = models.ForeignKey('aid_management.SupportCycle', on_delete=models.CASCADE)
    
    total_budget = models.DecimalField(max_digits=12, decimal_places=2)
    sum_of_allocations = models.DecimalField(max_digits=12, decimal_places=2)
    discrepancy = models.DecimalField(max_digits=12, decimal_places=2, default=0) 
    
    is_balanced = models.BooleanField(default=True)
    check_type = models.CharField(max_length=50, default="AUTOMATED_RECONCILIATION")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("سجل مطابقة مالية")
        verbose_name_plural = _("سجلات المطابقة المالية")

class ApplicationHistory(models.Model):
    application = models.ForeignKey(
        'aid_management.AidApplication', 
        on_delete=models.CASCADE, 
        related_name='history',
        verbose_name=_("الطلب")
    )
    from_status = models.CharField(
        max_length=20, 
        choices=AidApplication.STATUS_CHOICES, 
        verbose_name=_("من حالة")
    )
    to_status = models.CharField(
        max_length=20, 
        choices=AidApplication.STATUS_CHOICES, 
        verbose_name=_("إلى حالة")
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name=_("بواسطة")
    )
    notes = models.TextField(blank=True, verbose_name=_("ملاحظات التغيير"))
    
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_("وقت التغيير"))

    class Meta:
        verbose_name = _("تاريخ حالة الطلب")
        verbose_name_plural = _("سجلات تاريخ الحالات")
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.application.serial_number}: {self.from_status} -> {self.to_status}"