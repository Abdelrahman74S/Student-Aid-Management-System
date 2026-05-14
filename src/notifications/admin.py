from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from .models import Notification, Appeal


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'recipient', 'notification_type_badge', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'recipient__full_name')
    readonly_fields = ('created_at', 'read_at')

    def notification_type_badge(self, obj):
        colors = {
            'INFO': 'blue',
            'SUCCESS': 'green',
            'WARNING': 'orange',
            'ALERT': 'red',
        }
        color = colors.get(obj.notification_type, 'gray')
        return format_html(
            '<b style="color: {};">{}</b>',
            color, obj.get_notification_type_display()
        )
    notification_type_badge.short_description = _("النوع")


@admin.register(Appeal)
class AppealAdmin(admin.ModelAdmin):
    list_display = ('student', 'application', 'colored_status', 'reviewed_by', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('student__full_name', 'application__serial_number', 'reason')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (_('بيانات التظلم'), {
            'fields': ('application', 'student', 'reason', 'supporting_documents', 'status')
        }),
        (_('رد اللجنة'), {
            'fields': ('admin_response', 'reviewed_by')
        }),
        (_('التواريخ'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def colored_status(self, obj):
        colors = {
            'PENDING': 'orange',
            'UNDER_REVIEW': 'blue',
            'ACCEPTED': 'green',
            'REJECTED': 'red',
        }
        return format_html(
            '<b style="color: {};">{}</b>',
            colors.get(obj.status, 'gray'),
            obj.get_status_display()
        )
    colored_status.short_description = _("الحالة")
