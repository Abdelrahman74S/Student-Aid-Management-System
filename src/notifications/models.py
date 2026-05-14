"""
نماذج التنبيهات والتظلمات
=========================
- Notification: إشعارات داخلية للمستخدمين
- Appeal: تظلم الطالب على قرار الرفض
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class Notification(models.Model):
    """إشعار داخلي يصل للمستخدم عبر الموقع."""

    class NotificationType(models.TextChoices):
        INFO = 'INFO', _('معلومة')
        SUCCESS = 'SUCCESS', _('نجاح')
        WARNING = 'WARNING', _('تحذير')
        ALERT = 'ALERT', _('تنبيه عاجل')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_("المستقبل"),
    )
    title = models.CharField(max_length=200, verbose_name=_("العنوان"))
    message = models.TextField(verbose_name=_("نص الإشعار"))
    notification_type = models.CharField(
        max_length=10,
        choices=NotificationType.choices,
        default=NotificationType.INFO,
        verbose_name=_("نوع الإشعار"),
    )

    # الربط الاختياري بكيان في النظام
    related_url = models.CharField(
        max_length=500,
        blank=True,
        default='',
        verbose_name=_("رابط مرتبط"),
    )

    is_read = models.BooleanField(default=False, verbose_name=_("مقروء"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاريخ الإنشاء"))
    read_at = models.DateTimeField(null=True, blank=True, verbose_name=_("تاريخ القراءة"))

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("إشعار")
        verbose_name_plural = _("الإشعارات")
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"[{self.get_notification_type_display()}] {self.title}"

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class Appeal(models.Model):
    """
    تظلم الطالب — يُقدَّم بعد رفض الطلب.
    يمر بحالات: PENDING → UNDER_REVIEW → ACCEPTED/REJECTED.
    """

    class Status(models.TextChoices):
        PENDING = 'PENDING', _('قيد الانتظار')
        UNDER_REVIEW = 'UNDER_REVIEW', _('تحت المراجعة')
        ACCEPTED = 'ACCEPTED', _('مقبول')
        REJECTED = 'REJECTED', _('مرفوض')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        'aid_management.AidApplication',
        on_delete=models.CASCADE,
        related_name='appeals',
        verbose_name=_("الطلب المرتبط"),
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='appeals',
        verbose_name=_("الطالب"),
    )
    reason = models.TextField(verbose_name=_("سبب التظلم"))
    supporting_documents = models.FileField(
        upload_to='appeals/%Y/%m/',
        blank=True,
        null=True,
        verbose_name=_("مستندات داعمة"),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("حالة التظلم"),
    )

    # الرد الإداري
    admin_response = models.TextField(
        blank=True,
        default='',
        verbose_name=_("رد اللجنة"),
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_appeals',
        verbose_name=_("المراجع"),
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاريخ التقديم"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("آخر تحديث"))

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("تظلم")
        verbose_name_plural = _("التظلمات")
        constraints = [
            models.UniqueConstraint(
                fields=['application', 'student'],
                condition=models.Q(status__in=['PENDING', 'UNDER_REVIEW']),
                name='unique_active_appeal_per_application',
            ),
        ]

    def __str__(self):
        return f"تظلم #{str(self.id)[:8]} — {self.student.full_name}"

    def clean(self):
        from django.core.exceptions import ValidationError
        # لا يُسمح بالتظلم إلا على طلب مرفوض
        if self.application.status != 'REJECTED':
            raise ValidationError(
                _("لا يمكن تقديم تظلم إلا على طلب مرفوض.")
            )
