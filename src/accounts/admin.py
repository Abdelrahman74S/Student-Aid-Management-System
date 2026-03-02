from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import (
    User, Program, StudentProfile, 
    ReviewerProfile, CommitteeHeadProfile
)

class StudentProfileInline(admin.StackedInline):
    model = StudentProfile
    can_delete = False
    verbose_name_plural = _('بيانات ملف الطالب')
    fk_name = 'user'

class ReviewerProfileInline(admin.StackedInline):
    model = ReviewerProfile
    can_delete = False
    verbose_name_plural = _('بيانات ملف المُراجع')


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    
    list_display = ('email', 'full_name', 'national_id', 'role', 'is_verified', 'is_staff')
    list_filter = ('role', 'is_verified', 'is_staff', 'is_superuser')
    search_fields = ('email', 'full_name', 'national_id')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (_('بيانات الحساب'), {'fields': ('email', 'password')}),
        (_('المعلومات الشخصية'), {'fields': ('full_name', 'national_id', 'image')}),
        (_('الصلاحيات والأدوار'), {'fields': ('role', 'is_verified', 'is_active', 'is_staff', 'is_superuser')}),
        (_('التواريخ الهامة'), {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'national_id', 'role', 'password'),
        }),
    )

    inlines = [StudentProfileInline, ReviewerProfileInline]


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):

    list_display = ('student_id', 'get_user_name', 'program', 'level', 'gpa', 'academic_standing')
    list_filter = ('program', 'level', 'disability_status')
    search_fields = ('student_id', 'user__full_name', 'user__national_id')
    readonly_fields = ('created_at', 'updated_at')

    def get_user_name(self, obj):
        return obj.user.full_name
    get_user_name.short_description = _('اسم الطالب')


@admin.register(ReviewerProfile)
class ReviewerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'academic_rank', 'specialization')
    list_filter = ('academic_rank', 'assigned_programs')
    filter_horizontal = ('assigned_programs',) 

@admin.register(CommitteeHeadProfile)
class CommitteeHeadProfileAdmin(admin.ModelAdmin):
    list_display = ('committee_name', 'user', 'authority_level', 'is_active_head')
    list_filter = ('authority_level', 'is_active_head')