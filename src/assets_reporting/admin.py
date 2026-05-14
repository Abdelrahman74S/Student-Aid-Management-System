from django.contrib import admin
from django.utils.html import format_html
from .models import (
    DocumentType, ApplicationDocument, OfficialReport, SocialResearchForm,
    CommitteeMeetingMinute, DisbursementVoucher, SystemTemplate
)

@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')

@admin.register(ApplicationDocument)
class ApplicationDocumentAdmin(admin.ModelAdmin):
    list_display = ('application', 'document_type', 'is_verified', 'uploaded_at', 'view_file_link')
    list_filter = ('is_verified', 'document_type', 'uploaded_at')
    search_fields = ('application__serial_number', 'application__student__user__full_name')
    actions = ['mark_as_verified']

    def view_file_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">View File</a>', obj.file.url)
        return "No File"
    view_file_link.short_description = "ملف المستند"

    @admin.action(description="اعتماد المستندات المختارة")
    def mark_as_verified(self, request, queryset):
        queryset.update(is_verified=True)

@admin.register(OfficialReport)
class OfficialReportAdmin(admin.ModelAdmin):
    list_display = ('application', 'generated_at', 'generated_by', 'view_pdf_link')
    search_fields = ('application__serial_number', 'report_id')
    readonly_fields = ('generated_at', 'report_id')

    def view_pdf_link(self, obj):
        if obj.pdf_version:
            return format_html('<a href="{}" target="_blank">PDF Report</a>', obj.pdf_version.url)
        return "Not Generated"
    view_pdf_link.short_description = "تقرير PDF"

@admin.register(SocialResearchForm)
class SocialResearchFormAdmin(admin.ModelAdmin):
    list_display = ('application', 'researcher_name', 'housing_type', 'last_updated')
    list_filter = ('housing_type', 'last_updated')
    search_fields = ('application__serial_number', 'researcher_name')

@admin.register(CommitteeMeetingMinute)
class CommitteeMeetingMinuteAdmin(admin.ModelAdmin):
    list_display = ('meeting_number', 'meeting_date', 'head_of_committee', 'created_at')
    list_filter = ('meeting_date', 'created_at')
    search_fields = ('meeting_number', 'head_of_committee__full_name')
    filter_horizontal = ('attendees', 'approved_applications')

@admin.register(DisbursementVoucher)
class DisbursementVoucherAdmin(admin.ModelAdmin):
    list_display = ('voucher_number', 'application', 'amount', 'status', 'expiry_date', 'is_printed')
    list_filter = ('status', 'is_printed', 'expiry_date')
    search_fields = ('voucher_number', 'application__serial_number')
    readonly_fields = ('verification_hash', 'qr_code')

@admin.register(SystemTemplate)
class SystemTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'role_required', 'created_at', 'download_link')
    list_filter = ('role_required', 'created_at')
    search_fields = ('name',)

    def download_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" download>Download</a>', obj.file.url)
        return "No File"
    download_link.short_description = "رابط التحميل"
