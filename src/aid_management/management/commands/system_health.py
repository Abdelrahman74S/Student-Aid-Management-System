from django.core.management.base import BaseCommand
from accounts.models import User, Program, StudentProfile
from aid_management.models import SupportCycle, AidApplication, BudgetAllocation
from assets_reporting.models import DocumentType, CommitteeMeetingMinute
from django.utils import timezone
from decimal import Decimal

class Command(BaseCommand):
    help = 'Checks the health and status of the Student Aid Management System'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('--- System Health Report ---'))
        
        # 1. Accounts Stats
        users_count = User.objects.count()
        students_count = StudentProfile.objects.count()
        programs_count = Program.objects.count()
        
        self.stdout.write(f'Users: {users_count}')
        self.stdout.write(f'Students: {students_count}')
        self.stdout.write(f'Programs: {programs_count}')
        
        # 2. Support Cycle Stats
        active_cycles = SupportCycle.objects.filter(status='OPEN').count()
        total_budget = SupportCycle.objects.aggregate(total=models.Sum('total_budget'))['total'] or Decimal('0.00')
        reserved_budget = SupportCycle.objects.aggregate(total=models.Sum('reserved_budget'))['total'] or Decimal('0.00')
        
        self.stdout.write(f'Active Cycles: {active_cycles}')
        self.stdout.write(f'Total System Budget: {total_budget}')
        self.stdout.write(f'Total Reserved: {reserved_budget}')
        
        # 3. Application Stats
        apps_count = AidApplication.objects.count()
        approved_count = AidApplication.objects.filter(status='APPROVED').count()
        disbursed_count = AidApplication.objects.filter(status='DISBURSED').count()
        
        self.stdout.write(f'Total Applications: {apps_count}')
        self.stdout.write(f'Approved (Pending Disb): {approved_count}')
        self.stdout.write(f'Disbursed: {disbursed_count}')
        
        # 4. Critical Checks
        self.stdout.write('--- Critical Checks ---')
        
        # Check for unverified users
        unverified = User.objects.filter(is_verified=False, role__in=['R', 'C', 'D']).count()
        if unverified > 0:
            self.stdout.write(self.style.ERROR(f'CRITICAL: {unverified} staff members are not verified!'))
        else:
            self.stdout.write(self.style.SUCCESS('All staff members are verified.'))
            
        # Check for budget integrity
        for cycle in SupportCycle.objects.all():
            sum_alloc = BudgetAllocation.objects.filter(cycle=cycle, status__in=['PENDING', 'DISBURSED']).aggregate(total=models.Sum('amount_allocated'))['total'] or Decimal('0.00')
            if abs((cycle.reserved_budget + cycle.disbursed_budget) - sum_alloc) > Decimal('0.01'):
                self.stdout.write(self.style.ERROR(f'MISMATCH in Cycle ID {cycle.id}: Reserved+Disbursed ({cycle.reserved_budget + cycle.disbursed_budget}) != Sum of Allocations ({sum_alloc})'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Cycle ID {cycle.id} budget is consistent.'))

        # 5. Missing Data
        missing_docs = DocumentType.objects.count()
        if missing_docs == 0:
            self.stdout.write(self.style.ERROR('DATA ERROR: No DocumentTypes defined. Students won\'t be able to upload documents.'))

        self.stdout.write(self.style.SUCCESS('--- End of Report ---'))

from django.db import models
