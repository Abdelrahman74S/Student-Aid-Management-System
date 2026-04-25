from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import (
    DataAuditLog, ProcessActionLog, AccessLog, 
    BudgetAuditLog, SystemOverrideLog, FinancialIntegrityLog, ApplicationHistory
)

class ReadOnlyAuditAdmin(admin.ModelAdmin):
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False

@admin.register(DataAuditLog)
class DataAuditLogAdmin(ReadOnlyAuditAdmin):
    list_display = ('timestamp', 'user', 'entity_type', 'action', 'entity_id')
    list_filter = ('action', 'entity_type', 'timestamp')
    search_fields = ('entity_id', 'user__username', 'new_values')
    readonly_fields = ('log_id', 'user', 'entity_type', 'entity_id', 'action', 'old_values', 'new_values', 'timestamp')

@admin.register(ProcessActionLog)
class ProcessActionLogAdmin(ReadOnlyAuditAdmin):
    list_display = ('timestamp', 'action_name', 'user', 'cycle_name', 'ip_address')
    list_filter = ('action_name', 'timestamp')
    search_fields = ('action_name', 'notes', 'user__username')

@admin.register(AccessLog)
class AccessLogAdmin(ReadOnlyAuditAdmin):
    list_display = ('timestamp', 'user', 'event_type', 'ip_address')
    list_filter = ('event_type', 'timestamp')
    search_fields = ('user__username', 'ip_address', 'user_agent')

@admin.register(BudgetAuditLog)
class BudgetAuditLogAdmin(ReadOnlyAuditAdmin):
    list_display = ('timestamp', 'cycle', 'user', 'amount_before', 'amount_after')
    list_filter = ('cycle', 'timestamp')
    readonly_fields = ('cycle', 'user', 'amount_before', 'amount_after', 'reason', 'timestamp')

@admin.register(SystemOverrideLog)
class SystemOverrideLogAdmin(ReadOnlyAuditAdmin):
    list_display = ('timestamp', 'admin_user', 'application', 'override_type')
    list_filter = ('override_type', 'timestamp')
    search_fields = ('reason', 'admin_user__username', 'application__serial_number')

@admin.register(FinancialIntegrityLog)
class FinancialIntegrityLogAdmin(ReadOnlyAuditAdmin):
    list_display = ('timestamp', 'cycle', 'is_balanced', 'discrepancy')
    list_filter = ('is_balanced', 'check_type')
    
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('-is_balanced', '-timestamp')

@admin.register(ApplicationHistory)
class ApplicationHistoryAdmin(ReadOnlyAuditAdmin):
    list_display = ('application', 'from_status', 'to_status', 'changed_by', 'timestamp')
    list_filter = ('from_status', 'to_status', 'timestamp')
    search_fields = ('application__serial_number', 'changed_by__username', 'notes')