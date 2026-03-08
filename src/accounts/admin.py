from django.contrib import admin
from .models import (
    User,
    Program,
    StudentProfile,
    ReviewerProfile,
    CommitteeHeadProfile,
    AuditorProfile
)


# -----------------------------
# User Admin
# -----------------------------
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "full_name", "role", "is_verified", "is_active", "date_joined")
    list_filter = ("role", "is_verified", "is_active", "is_staff")
    search_fields = ("email", "full_name", "national_id")
    ordering = ("-date_joined",)
    readonly_fields = ("date_joined", "last_login")


# -----------------------------
# Program Admin
# -----------------------------
@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active", "created_at")
    search_fields = ("name", "code")
    list_filter = ("is_active",)
    ordering = ("name",)


# -----------------------------
# Student Profile
# -----------------------------
@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "student_id",
        "program",
        "level",
        "gpa",
        "disability_status",
        "HasPreviousSupport",
    )

    search_fields = (
        "user__email",
        "user__full_name",
        "student_id",
    )

    list_filter = (
        "program",
        "level",
        "disability_status",
        "HasPreviousSupport",
    )

    list_select_related = ("user", "program")

    ordering = ("-gpa",)


# -----------------------------
# Reviewer Profile
# -----------------------------
@admin.register(ReviewerProfile)
class ReviewerProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "academic_rank",
        "specialization",
        "created_at",
    )

    search_fields = (
        "user__email",
        "user__full_name",
        "specialization",
    )

    list_filter = (
        "academic_rank",
        "specialization",
    )

    list_select_related = ("user",)

    filter_horizontal = ("assigned_programs",)


# -----------------------------
# Committee Head Profile
# -----------------------------
@admin.register(CommitteeHeadProfile)
class CommitteeHeadProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "committee_name",
        "authority_level",
        "is_active_head",
        "created_at",
    )

    search_fields = (
        "user__email",
        "user__full_name",
        "committee_name",
    )

    list_filter = (
        "is_active_head",
        "authority_level",
    )

    list_select_related = ("user",)

    filter_horizontal = ("managed_programs",)


# -----------------------------
# Auditor Profile
# -----------------------------
@admin.register(AuditorProfile)
class AuditorProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "created_at",
    )

    search_fields = (
        "user__email",
        "user__full_name",
    )

    list_select_related = ("user",)

    filter_horizontal = ("assigned_programs",)