from django.contrib import admin
from .models import SupportCycle, ScoringRule , BudgetAllocation, AidApplication, CommitteeReview

from django.contrib import admin
from django.db import transaction
from django.contrib import messages


@admin.register(ScoringRule)
class ScoringRuleAdmin(admin.ModelAdmin):
    list_display = ('criteria_type', 'points', 'weight', 'priority', 'is_active')
    list_editable = ('priority', 'is_active') 
    list_filter = ('cycle', 'criteria_type')
    


@admin.action(description="Allocate budget (Fixed Amount)")
def allocate_budget(modeladmin, request, queryset):
    amount = 0  
    success_count = 0

    for cycle_obj in queryset:
        try:
            with transaction.atomic():
                cycle = SupportCycle.objects.select_for_update().get(id=cycle_obj.id)

                if cycle.available_budget < amount:
                    messages.warning(
                        request,
                        f"Cycle {cycle.serial_number}: insufficient budget"
                    )
                    continue

                BudgetAllocation.objects.create(
                    cycle=cycle,
                    amount_allocated=amount,
                    status='PENDING'
                )

                cycle.reserved_budget += amount
                cycle.available_budget -= amount
                cycle.save(update_fields=[
                    'reserved_budget',
                    'available_budget'
                ])

                success_count += 1

        except Exception as e:
            messages.error(request, f"Error in cycle {cycle_obj.id}: {str(e)}")


    messages.success(
        request,
        f"Successfully allocated budget for {success_count} cycle(s)"
    )

@admin.register(SupportCycle)
class SupportCycleAdmin(admin.ModelAdmin):
    list_display = ('serial_number', 'name', 'status', 'total_budget', 'available_budget', 'is_locked')
    list_filter = ('status', 'academic_year', 'semester')
    search_fields = ('name', 'serial_number')
    
    readonly_fields = ('reserved_budget', 'disbursed_budget', 'serial_number')
    actions = [allocate_budget]