from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import CommitteeReview, AidApplication, BudgetAllocation
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

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
            'student_name': instance.student.user.get_full_name(),
            'application_number': instance.serial_number,
            'status_display': instance.get_status_display(),
            'decision_notes': instance.committee_decision,
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
            'student_name': instance.application.student.user.get_full_name(),
            'amount': instance.amount_disbursed,
            'date': instance.disbursement_date
        }
        html_message = render_to_string('aid_management/emails/disbursement_notification.html', context)
        send_mail(
            subject, strip_tags(html_message), settings.DEFAULT_FROM_EMAIL,
            [instance.application.student.user.email], html_message=html_message, fail_silently=True,
        )