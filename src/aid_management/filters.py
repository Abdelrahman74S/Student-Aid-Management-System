import django_filters
from django.utils.translation import gettext_lazy as _
from .models import AidApplication, SupportCycle

class AidApplicationFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(
        choices=AidApplication.STATUS_CHOICES,
        label=_("حالة الطلب"),
        empty_label=_("كل الحالات")
    )
    cycle = django_filters.ModelChoiceFilter(
        queryset=SupportCycle.objects.all(),
        label=_("دورة الدعم"),
        empty_label=_("كل الدورات")
    )
    date_min = django_filters.DateFilter(
        field_name='submission_date',
        lookup_expr='gte',
        label=_("من تاريخ")
    )
    date_max = django_filters.DateFilter(
        field_name='submission_date',
        lookup_expr='lte',
        label=_("إلى تاريخ")
    )

    class Meta:
        model = AidApplication
        fields = ['status', 'cycle']
