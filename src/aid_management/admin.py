from django.contrib import admin
from django.db import transaction
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from .models import SupportCycle, ScoringRule, BudgetAllocation, AidApplication, CommitteeReview
from assets_reporting.models import ApplicationDocument

class ApplicationDocumentInline(admin.TabularInline):
    model = ApplicationDocument
    extra = 0
    readonly_fields = ('uploaded_at', 'view_file_link')
    fields = ('document_type', 'is_verified', 'uploaded_at', 'view_file_link')

    def view_file_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">فتح</a>', obj.file.url)
        return "-"
    view_file_link.short_description = _("الملف")

class ScoringRuleInline(admin.TabularInline):
    model = ScoringRule
    extra = 0
    fields = ('criteria_type', 'condition', 'points', 'weight', 'priority', 'is_active')

class CommitteeReviewInline(admin.StackedInline):
    model = CommitteeReview
    extra = 0
    readonly_fields = ('review_timestamp', 'total_score')
    fieldsets = (
        (None, {'fields': (('reviewer', 'status', 'is_submitted'), 'total_score', 'conflict_of_interest')}),
    )

class BudgetAllocationInline(admin.TabularInline):
    model = BudgetAllocation
    extra = 0
    readonly_fields = ('created_at',)
    fields = ('amount_allocated', 'amount_disbursed', 'status', 'created_at')

@admin.register(SupportCycle)
class SupportCycleAdmin(admin.ModelAdmin):
    list_display = ('serial_number', 'name', 'colored_status', 'budget_usage', 'academic_year', 'total_budget', 'is_locked')
    list_filter = ('status', 'academic_year', 'semester', 'is_locked')
    search_fields = ('name', 'serial_number', 'academic_year')
    readonly_fields = ('serial_number', 'reserved_budget', 'disbursed_budget', 'created_by')
    inlines = [ScoringRuleInline]

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def colored_status(self, obj):
        colors = {
            'OPEN': 'green',
            'REVIEW': 'blue',
            'CLOSED': 'red',
            'ARCHIVED': 'gray',
        }
        return format_html(
            '<b style="color: {};">{}</b>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    def budget_usage(self, obj):
        if obj.total_budget > 0:
            usage = ((obj.reserved_budget + obj.disbursed_budget) / obj.total_budget) * 100
            color = 'green' if usage < 80 else 'orange' if usage < 100 else 'red'
            return format_html(
                '<div style="width:100px; background:#eee; height:10px; border-radius:5px;">'
                '<div style="width:{}px; background:{}; height:10px; border-radius:5px;"></div>'
                '</div> <small>{}%</small>',
                min(usage, 100), color, round(usage, 1)
            )
        return "0%"
    budget_usage.short_description = _("استهلاك الميزانية")

    fieldsets = (
        (_('المعلومات الأساسية'), {
            'fields': ('name', 'serial_number', ('academic_year', 'semester'), ('status', 'is_locked'))
        }),
        (_('الميزانية'), {
            'fields': (('total_budget', 'budget_usage'), ('reserved_budget', 'disbursed_budget'))
        }),
        (_('التواريخ الهامة'), {
            'fields': (('application_start_date', 'application_end_date'), ('review_start_date', 'review_end_date'))
        }),
        (_('البيانات الوصفية'), {
            'fields': ('created_by',),
            'classes': ('collapse',)
        }),
    )

@admin.register(ScoringRule)
class ScoringRuleAdmin(admin.ModelAdmin):
    list_display = ('criteria_type', 'cycle', 'points', 'weight', 'priority', 'is_active')
    list_editable = ('priority', 'is_active')
    list_filter = ('cycle', 'criteria_type', 'is_active')
    search_fields = ('description',)

@admin.register(AidApplication)
class AidApplicationAdmin(admin.ModelAdmin):
    list_display = ('serial_number', 'student_name', 'program_name', 'cycle', 'get_total_score', 'colored_status', 'is_locked')
    list_filter = ('status', 'cycle', 'student__program', 'is_locked', 'submission_date')
    search_fields = ('serial_number', 'student__user__full_name', 'student__student_id', 'student__user__national_id')
    readonly_fields = ('serial_number', 'submission_date', 'decision_date', 'ip_address', 'user_agent', 'get_total_score')
    inlines = [ApplicationDocumentInline, CommitteeReviewInline, BudgetAllocationInline]
    actions = ['lock_applications', 'unlock_applications']

    fieldsets = (
        (_('بيانات الطالب والطلب'), {
            'fields': (('student', 'cycle'), ('serial_number', 'submission_date'))
        }),
        (_('القرار المالي'), {
            'fields': (('status', 'is_locked'), ('get_total_score', 'decision_date'), 'decision_notes')
        }),
        (_('بيانات تقنية'), {
            'fields': (('ip_address', 'user_agent'),),
            'classes': ('collapse',)
        }),
    )

    def student_name(self, obj):
        return obj.student.user.full_name
    student_name.short_description = _("اسم الطالب")

    def colored_status(self, obj):
        colors = {
            'DRAFT': 'gray',
            'SUBMITTED': 'orange',
            'UNDER_REVIEW': 'blue',
            'SCORED': 'purple',
            'APPROVED': 'green',
            'REJECTED': 'red',
            'DISBURSED': 'darkgreen',
        }
        return format_html(
            '<b style="color: {};">{}</b>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    def program_name(self, obj):
        return obj.student.program.name if obj.student.program else "-"
    program_name.short_description = _("القسم")

    def get_total_score(self, obj):
        reviews = obj.reviews.filter(is_submitted=True)
        if reviews.exists():
            avg = reviews.aggregate(Avg('total_score'))['total_score__avg']
            return round(avg, 2)
        return "-"
    get_total_score.short_description = _("متوسط الدرجة")

    @admin.action(description=_("قفل الطلبات المختارة"))
    def lock_applications(self, request, queryset):
        queryset.update(is_locked=True)

    @admin.action(description=_("إلغاء قفل الطلبات المختارة"))
    def unlock_applications(self, request, queryset):
        queryset.update(is_locked=False)

@admin.register(CommitteeReview)
class CommitteeReviewAdmin(admin.ModelAdmin):
    list_display = ('application', 'reviewer', 'status', 'total_score', 'is_submitted', 'review_timestamp')
    list_filter = ('status', 'is_submitted', 'review_timestamp')
    search_fields = ('application__serial_number', 'reviewer__full_name')
    readonly_fields = ('review_timestamp', 'total_score')

@admin.register(BudgetAllocation)
class BudgetAllocationAdmin(admin.ModelAdmin):
    list_display = ('application', 'cycle', 'amount_allocated', 'amount_disbursed', 'status', 'disbursement_date')
    list_filter = ('status', 'disbursement_date', 'cycle')
    search_fields = ('application__serial_number', 'notes')
    readonly_fields = ('created_at', 'updated_at')