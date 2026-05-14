from django.contrib import admin
from .models import (
    DataAuditLog, ProcessActionLog, AccessLog, 
    BudgetAuditLog, SystemOverrideLog, FinancialIntegrityLog, ApplicationHistory
)

@admin.register(DataAuditLog)
class DataAuditLogAdmin(admin.ModelAdmin):
    list_display = ('entity_type', 'action', 'user', 'timestamp')
    list_filter = ('action', 'entity_type', 'timestamp')
    search_fields = ('entity_id', 'user__full_name')
    readonly_fields = ('log_id', 'timestamp', 'old_values', 'new_values')

@admin.register(ProcessActionLog)
class ProcessActionLogAdmin(admin.ModelAdmin):
    list_display = ('action_name', 'user', 'cycle_name', 'timestamp')
    list_filter = ('action_name', 'timestamp')
    search_fields = ('action_name', 'notes', 'user__full_name')
    readonly_fields = ('timestamp',)

@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'event_type', 'ip_address', 'timestamp')
    list_filter = ('event_type', 'timestamp')
    search_fields = ('user__full_name', 'ip_address')
    readonly_fields = ('timestamp', 'user_agent')

@admin.register(BudgetAuditLog)
class BudgetAuditLogAdmin(admin.ModelAdmin):
    list_display = ('cycle', 'user', 'amount_before', 'amount_after', 'timestamp')
    list_filter = ('timestamp', 'cycle')
    search_fields = ('reason', 'user__full_name')
    readonly_fields = ('timestamp',)

@admin.register(SystemOverrideLog)
class SystemOverrideLogAdmin(admin.ModelAdmin):
    list_display = ('admin_user', 'application', 'override_type', 'timestamp')
    list_filter = ('override_type', 'timestamp')
    search_fields = ('reason', 'admin_user__full_name', 'application__serial_number')
    readonly_fields = ('timestamp', 'previous_state', 'new_state')

@admin.register(FinancialIntegrityLog)
class FinancialIntegrityLogAdmin(admin.ModelAdmin):
    list_display = ('cycle', 'total_budget', 'sum_of_allocations', 'discrepancy', 'is_balanced', 'timestamp')
    list_filter = ('is_balanced', 'timestamp', 'cycle')
    readonly_fields = ('timestamp',)

@admin.register(ApplicationHistory)
class ApplicationHistoryAdmin(admin.ModelAdmin):
    list_display = ('application', 'from_status', 'to_status', 'changed_by', 'timestamp')
    list_filter = ('from_status', 'to_status', 'timestamp')
    search_fields = ('application__serial_number', 'changed_by__full_name')
    readonly_fields = ('timestamp',)