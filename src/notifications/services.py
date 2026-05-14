"""
خدمات التنبيهات — دوال مساعدة لإرسال الإشعارات
"""

from django.urls import reverse
from .models import Notification


def notify_user(recipient, title, message, notification_type='INFO', related_url=''):
    """إنشاء إشعار جديد للمستخدم."""
    return Notification.objects.create(
        recipient=recipient,
        title=title,
        message=message,
        notification_type=notification_type,
        related_url=related_url,
    )


def notify_application_status_change(application, old_status, new_status):
    """إشعار الطالب عند تغير حالة طلبه."""
    status_messages = {
        'UNDER_REVIEW': {
            'title': 'طلبك قيد المراجعة',
            'message': f'تم استلام طلبك رقم {application.serial_number} وهو الآن قيد المراجعة من اللجنة.',
            'type': 'INFO',
        },
        'SCORED': {
            'title': 'تم تقييم طلبك',
            'message': f'اكتمل تقييم طلبك رقم {application.serial_number}. في انتظار القرار النهائي.',
            'type': 'INFO',
        },
        'APPROVED': {
            'title': '🎉 تمت الموافقة على طلبك!',
            'message': f'مبارك! تمت الموافقة على طلب المساعدة رقم {application.serial_number}.',
            'type': 'SUCCESS',
        },
        'REJECTED': {
            'title': 'لم تتم الموافقة على طلبك',
            'message': f'نأسف لإبلاغك أن طلب المساعدة رقم {application.serial_number} لم تتم الموافقة عليه. يمكنك تقديم تظلم.',
            'type': 'WARNING',
        },
        'DISBURSED': {
            'title': '💰 تم صرف المساعدة',
            'message': f'تم صرف المساعدة المالية لطلبك رقم {application.serial_number}.',
            'type': 'SUCCESS',
        },
    }

    msg = status_messages.get(new_status)
    if msg:
        try:
            related_url = reverse(
                'aid_management:application_detail',
                kwargs={'pk': str(application.id)}
            )
        except Exception:
            related_url = ''

        notify_user(
            recipient=application.student.user,
            title=msg['title'],
            message=msg['message'],
            notification_type=msg['type'],
            related_url=related_url,
        )


def notify_appeal_status_change(appeal):
    """إشعار الطالب عند تغير حالة تظلمه."""
    if appeal.status == 'UNDER_REVIEW':
        notify_user(
            recipient=appeal.student,
            title='تظلمك قيد المراجعة',
            message=f'يتم مراجعة تظلمك على الطلب {appeal.application.serial_number} من قبل اللجنة.',
            notification_type='INFO',
        )
    elif appeal.status == 'ACCEPTED':
        notify_user(
            recipient=appeal.student,
            title='✅ تم قبول تظلمك',
            message=f'تم قبول تظلمك وسيتم إعادة النظر في طلبك رقم {appeal.application.serial_number}.',
            notification_type='SUCCESS',
        )
    elif appeal.status == 'REJECTED':
        notify_user(
            recipient=appeal.student,
            title='تم رفض التظلم',
            message=f'بعد المراجعة، تم رفض تظلمك على الطلب {appeal.application.serial_number}. السبب: {appeal.admin_response}',
            notification_type='WARNING',
        )
