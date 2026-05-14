from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from .models import (
    User, Program, StudentProfile, ReviewerProfile, 
    CommitteeHeadProfile, AuditorProfile
)

class StudentProfileInline(admin.StackedInline):
    model = StudentProfile
    can_delete = False
    verbose_name_plural = _('بروفايل الطالب')
    fk_name = 'user'

class ReviewerProfileInline(admin.StackedInline):
    model = ReviewerProfile
    can_delete = False
    verbose_name_plural = _('بروفايل المراجع')
    fk_name = 'user'

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'full_name', 'colored_role', 'is_verified', 'is_staff', 'date_joined')
    list_filter = ('role', 'is_verified', 'is_staff', 'is_active', 'date_joined')
    search_fields = ('email', 'full_name', 'national_id')
    ordering = ('-date_joined',)
    
    def colored_role(self, obj):
        colors = {
            'S': '#0ea5e9', # Student - Blue
            'R': '#8b5cf6', # Reviewer - Purple
            'C': '#f59e0b', # Head - Orange
            'D': '#10b981', # Auditor - Green
            'A': '#ef4444', # Admin - Red
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 11px;">{}</span>',
            colors.get(obj.role, '#6b7280'),
            obj.get_role_display()
        )
    colored_role.short_description = _("الدور")
    inlines = [] # dynamically set
    
    actions = ['verify_users', 'unverify_users']

    @admin.action(description=_("اعتماد المستخدمين المختارين"))
    def verify_users(self, request, queryset):
        queryset.update(is_verified=True)

    @admin.action(description=_("إلغاء اعتماد المستخدمين المختارين"))
    def unverify_users(self, request, queryset):
        queryset.update(is_verified=False)

    def get_inlines(self, request, obj=None):
        if obj:
            if obj.role == 'S':
                return [StudentProfileInline]
            elif obj.role == 'R':
                return [ReviewerProfileInline]
        return []

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('المعلومات الشخصية'), {'fields': ('full_name', 'national_id', 'image')}),
        (_('الدور والصلاحيات'), {'fields': ('role', 'is_verified', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('التواريخ'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'national_id', 'role', 'password'),
        }),
    )

@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')
    ordering = ('name',)

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'student_id', 'program', 'level', 'gpa', 'academic_standing')
    list_filter = ('program', 'level', 'disability_status', 'HasPreviousSupport')
    search_fields = ('user__full_name', 'student_id', 'user__email')
    raw_id_fields = ('user',)

@admin.register(ReviewerProfile)
class ReviewerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'academic_rank', 'specialization')
    list_filter = ('academic_rank', 'specialization')
    search_fields = ('user__full_name', 'specialization')
    filter_horizontal = ('assigned_programs',)
    raw_id_fields = ('user',)

@admin.register(CommitteeHeadProfile)
class CommitteeHeadProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'committee_name', 'authority_level', 'is_active_head')
    list_filter = ('is_active_head', 'authority_level')
    search_fields = ('user__full_name', 'committee_name')
    filter_horizontal = ('managed_programs',)
    raw_id_fields = ('user',)

@admin.register(AuditorProfile)
class AuditorProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at')
    search_fields = ('user__full_name', 'user__email')
    filter_horizontal = ('assigned_programs',)
    raw_id_fields = ('user',)