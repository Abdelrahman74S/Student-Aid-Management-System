import django_filters
from .models import DataAuditLog, AccessLog, ApplicationHistory
from django.utils.translation import gettext_lazy as _

class DataAuditFilter(django_filters.FilterSet):
    timestamp = django_filters.DateFromToRangeFilter(
        label=_("الفترة الزمنية"),
        widget=django_filters.widgets.RangeWidget(attrs={'type': 'date', 'class': 'form-control'})
    )
    user_email = django_filters.CharFilter(field_name='user__email', lookup_expr='icontains', label=_("بريد المستخدم"))
    entity = django_filters.CharFilter(field_name='entity_type', lookup_expr='icontains', label=_("الجدول/الموديل"))
    
    class Meta:
        model = DataAuditLog
        fields = ['action', 'entity', 'user_email', 'timestamp']

class AccessLogFilter(django_filters.FilterSet):
    timestamp = django_filters.DateFromToRangeFilter(label=_("فترة الدخول"))
    
    class Meta:
        model = AccessLog
        fields = {
            'event_type': ['exact'],
            'ip_address': ['icontains'],
            'user__email': ['icontains'],
        }