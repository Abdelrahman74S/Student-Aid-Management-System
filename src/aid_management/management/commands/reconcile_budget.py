import logging
from django.core.management.base import BaseCommand
from django.db.models import Sum
from aid_management.models import SupportCycle, BudgetAllocation

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Reconciles SupportCycle budget totals with actual allocations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run the command without saving changes'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        cycles = SupportCycle.objects.all()

        fixed_count = 0

        for cycle in cycles:
            allocations = BudgetAllocation.objects.filter(cycle=cycle)

            actual_reserved = allocations.filter(
                status='PENDING'
            ).aggregate(total=Sum('amount_allocated'))['total'] or 0

            actual_disbursed = allocations.filter(
                status='DISBURSED'
            ).aggregate(total=Sum('amount_disbursed'))['total'] or 0

            if (
                cycle.reserved_budget != actual_reserved or
                cycle.disbursed_budget != actual_disbursed
            ):
                fixed_count += 1

                msg = (
                    f"Cycle {cycle.serial_number} drift detected | "
                    f"Reserved: {cycle.reserved_budget} → {actual_reserved}, "
                    f"Disbursed: {cycle.disbursed_budget} → {actual_disbursed}"
                )

                logger.warning(msg)
                self.stdout.write(self.style.WARNING(msg))

                if not dry_run:
                    cycle.reserved_budget = actual_reserved
                    cycle.disbursed_budget = actual_disbursed
                    cycle.save(update_fields=[
                        'reserved_budget',
                        'disbursed_budget',
                        'updated_at'
                    ])

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"[DRY RUN] {fixed_count} cycles would be fixed"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Successfully fixed {fixed_count} cycles"
            ))