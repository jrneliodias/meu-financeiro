from django.core.management.base import BaseCommand, CommandError
from django.utils.timezone import localdate

from registers.models import RecurringExpense


class Command(BaseCommand):
    help = "Create this year's monthly expenses from every user's active recurring expenses"

    def add_arguments(self, parser):
        parser.add_argument('--month', type=int, default=None,
                            help='Month number (1-12) to process recurring expenses for (default: current month)')

    def handle(self, *args, **options):
        today = localdate()
        month = options['month'] or today.month
        if not 1 <= month <= 12:
            raise CommandError('Month must be between 1 and 12')
        for recurring_expense in RecurringExpense.objects.due_in(today.year, month):
            expense, created = recurring_expense.generate_for_month(today.year, month)
            status = 'Created' if created else 'Already exists'
            self.stdout.write(f"{status}: {recurring_expense.description} on {expense.date}")
        self.stdout.write(self.style.SUCCESS('Monthly expenses have been created.'))
