from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Count
from .models import CommitteeReview, AidApplication, BudgetAllocation
from django.utils import timezone


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
def update_application_status_on_disburse(sender, instance, **kwargs):
    if instance.status == 'DISBURSED' and instance.application:
        application = instance.application
        if application.status != 'DISBURSED':
            application.status = 'DISBURSED'
            application.save(update_fields=['status', 'updated_at'])