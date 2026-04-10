# accounts/signals.py

from django.db.models.signals import post_save, pre_save
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

@receiver(pre_save, sender=User)
def update_user_profile_on_role_change(sender, instance, **kwargs):
    if not instance.pk:
        return

    try:
        old_instance = User.objects.get(pk=instance.pk)
    except User.DoesNotExist:
        return

    if old_instance.role != instance.role:
        old_profiles = [
            getattr(instance, 'student_profile', None),
            getattr(instance, 'reviewer_profile', None),
            getattr(instance, 'committee_head_profile', None),
            getattr(instance, 'auditor_profile', None),
        ]
        for profile in old_profiles:
            if profile:
                profile.delete()

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
    if getattr(instance, '_profile_saved', False):
        return

    instance._profile_saved = True

    if instance.role == UserRoles.STUDENT and hasattr(instance, 'student_profile'):
        instance.student_profile.save()
    elif instance.role == UserRoles.REVIEWER and hasattr(instance, 'reviewer_profile'):
        instance.reviewer_profile.save()
    elif instance.role == UserRoles.COMMITTEE_HEAD and hasattr(instance, 'committee_head_profile'):
        instance.committee_head_profile.save()
    elif instance.role == UserRoles.AUDITOR and hasattr(instance, 'auditor_profile'):
        instance.auditor_profile.save()

    del instance._profile_saved