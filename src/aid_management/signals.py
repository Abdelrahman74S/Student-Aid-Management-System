from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from .models import CommitteeReview, AidApplication, BudgetAllocation
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.core.cache import cache

@receiver(pre_save, sender=AidApplication)
def capture_old_status(sender, instance, **kwargs):
    """حفظ الحالة القديمة قبل التعديل لمقارنتها بعد الحفظ."""
    if instance.pk:
        try:
            instance._old_status = AidApplication.objects.get(pk=instance.pk).status
        except AidApplication.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None

@receiver([post_save, post_delete], sender=AidApplication)
def clear_aid_management_cache(sender, instance, **kwargs):
    """Invalidate cache on aid application changes."""
    cache.delete_pattern("committee_head_dashboard_*")
    cache.delete_pattern("application_ranking_list_*")

@receiver(post_save, sender=AidApplication)
def send_status_notification(sender, instance, created, **kwargs):
    """إرسال إشعار داخلي عند تغير حالة الطلب."""
    if created:
        return
    old_status = getattr(instance, '_old_status', None)
    if old_status and old_status != instance.status:
        try:
            from notifications.services import notify_application_status_change
            notify_application_status_change(instance, old_status, instance.status)
        except Exception:
            import logging
            logging.getLogger(__name__).exception(
                f"فشل إرسال إشعار لتغير حالة الطلب {instance.id}"
            )

@receiver(post_save, sender=AidApplication)
def calculate_auto_score_on_submit(sender, instance, **kwargs):
    """حساب الدرجة التلقائية عند تقديم الطلب."""
    update_fields = kwargs.get('update_fields')
    # تجنب الحلقة اللانهائية: لا نحسب إذا كان التحديث على auto_score نفسه
    if update_fields and 'auto_score' in update_fields:
        return
    if instance.status == 'SUBMITTED' and instance.auto_score == 0:
        try:
            instance.calculate_auto_score()
        except Exception:
            import logging
            logging.getLogger(__name__).exception(
                f"فشل حساب الدرجة التلقائية للطلب {instance.id}"
            )

@receiver([post_save, post_delete], sender=CommitteeReview)
def clear_dashboard_reviews_cache(sender, instance, **kwargs):
    """Invalidate dashboard when reviews change."""
    cache.delete_pattern("committee_head_dashboard_*")

@receiver(post_save, sender=CommitteeReview)
def check_all_reviews_submitted(sender, instance, **kwargs):
    if instance.status != 'SUBMITTED':
        return

    application = instance.application
    total_reviews = application.reviews.count()
    submitted_reviews = application.reviews.filter(status='SUBMITTED').count()

    if total_reviews > 0 and total_reviews == submitted_reviews:
        if application.status not in ['SCORED', 'APPROVED', 'REJECTED', 'DISBURSED']:
            application.status = 'SCORED'
            application.decision_date = timezone.now()
            application.save(update_fields=['status', 'decision_date', 'updated_at'])

@receiver(post_save, sender=BudgetAllocation)
def update_cycle_budget_on_allocation(sender, instance, created, **kwargs):
    if created:
        cycle = instance.cycle
        cycle.reserved_budget += instance.amount_allocated
        cycle.save(update_fields=['reserved_budget', 'updated_at'])

@receiver(post_delete, sender=BudgetAllocation)
def restore_budget_on_delete(sender, instance, **kwargs):
    cycle = instance.cycle
    cycle.reserved_budget -= instance.amount_allocated
    cycle.save(update_fields=['reserved_budget', 'updated_at'])

@receiver(post_save, sender=BudgetAllocation)
def update_application_status_on_disburse(sender, instance, **kwargs):
    if instance.status == 'DISBURSED' and instance.application:
        application = instance.application
        if application.status != 'DISBURSED':
            application.status = 'DISBURSED'
            application.save(update_fields=['status', 'updated_at'])

@receiver(post_save, sender=AidApplication)
def send_status_update_email(sender, instance, created, **kwargs):
    trackable_statuses = ['SUBMITTED', 'APPROVED', 'REJECTED']
    if instance.status in trackable_statuses:
        subject = f"تحديث بخصوص طلب المساعدة رقم: {instance.serial_number}"
        template_name = f'aid_management/emails/status_{instance.status.lower()}.html'
        context = {
            'decision_notes': instance.committee_decision,
            'application': instance,
        }
        html_message = render_to_string(template_name, context)
        send_mail(
            subject, strip_tags(html_message), settings.DEFAULT_FROM_EMAIL,
            [instance.student.user.email], html_message=html_message, fail_silently=True,
        )

@receiver(post_save, sender=BudgetAllocation)
def send_disbursement_email(sender, instance, **kwargs):
    if instance.status == 'DISBURSED' and instance.application:
        subject = "تم صرف مبلغ الدعم المالي"
        context = {
            'date': instance.disbursement_date,
            'application': instance.application,
        }
        html_message = render_to_string('aid_management/emails/disbursement_notification.html', context)
        send_mail(
            subject, strip_tags(html_message), settings.DEFAULT_FROM_EMAIL,
            [instance.application.student.user.email], html_message=html_message, fail_silently=True,
        )

import uuid
from datetime import timedelta

@receiver(post_save, sender=AidApplication)
def create_voucher_and_report_on_approval(sender, instance, created, **kwargs):
    if instance.status == 'APPROVED' and hasattr(instance, 'budget_allocation') and instance.budget_allocation:
        from assets_reporting.models import DisbursementVoucher, OfficialReport
        from assets_reporting.utils import render_to_pdf
        
        voucher, voucher_created = DisbursementVoucher.objects.get_or_create(
            application=instance,
            defaults={
                'voucher_number': f"VCH-{instance.serial_number}-{uuid.uuid4().hex[:6].upper()}",
                'allocation': instance.budget_allocation,
                'amount': instance.budget_allocation.amount_allocated,
                'expiry_date': timezone.now().date() + timedelta(days=30),
                'status': 'PENDING'
            }
        )
        
        report, report_created = OfficialReport.objects.get_or_create(
            application=instance
        )
        
        if report_created or not report.pdf_version:
            context = {
                'report': report,
                'application': instance,
            }
            pdf_file = render_to_pdf('assets_reporting/committee/official_report.html', context)
            if pdf_file:
                file_name = f"official_report_{instance.serial_number}.pdf"
                report.pdf_version.save(file_name, pdf_file, save=True)