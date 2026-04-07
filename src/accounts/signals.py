from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import (
    User, UserRoles, StudentProfile, ReviewerProfile, 
    CommitteeHeadProfile, AuditorProfile
)

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if instance.role == UserRoles.STUDENT:
            StudentProfile.objects.create(
                user=instance,
                student_id=instance.national_id
            )
            
        elif instance.role == UserRoles.REVIEWER:
            ReviewerProfile.objects.create(user=instance)
            
        elif instance.role == UserRoles.COMMITTEE_HEAD:
            CommitteeHeadProfile.objects.create(user=instance)
            
        elif instance.role == UserRoles.AUDITOR:
            AuditorProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if instance.role == UserRoles.STUDENT and hasattr(instance, 'student_profile'):
        instance.student_profile.save()
    elif instance.role == UserRoles.REVIEWER and hasattr(instance, 'reviewer_profile'):
        instance.reviewer_profile.save()
    elif instance.role == UserRoles.COMMITTEE_HEAD and hasattr(instance, 'committee_head_profile'):
        instance.committee_head_profile.save()
    elif instance.role == UserRoles.AUDITOR and hasattr(instance, 'auditor_profile'):
        instance.auditor_profile.save()