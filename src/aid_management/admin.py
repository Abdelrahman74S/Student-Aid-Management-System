from django.contrib import admin
from .models import SupportCycle, ScoringRule

@admin.register(SupportCycle)
class SupportCycleAdmin(admin.ModelAdmin):
    list_display = ('serial_number', 'name', 'status', 'total_budget', 'available_budget', 'is_locked')
    list_filter = ('status', 'academic_year', 'semester')
    search_fields = ('name', 'serial_number')
    
    readonly_fields = ('reserved_budget', 'disbursed_budget', 'serial_number')

@admin.register(ScoringRule)
class ScoringRuleAdmin(admin.ModelAdmin):
    list_display = ('criteria_type', 'points', 'weight', 'priority', 'is_active')
    list_editable = ('priority', 'is_active') 
    list_filter = ('cycle', 'criteria_type')