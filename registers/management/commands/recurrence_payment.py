import datetime
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from registers.models import RecurringExpense, Expense


class Command(BaseCommand):
    help = 'Create monthly expenses from RecurringExpense'

    def add_arguments(self, parser):
        parser.add_argument(
            '--month',
            type=int,
            default=None,
            help='Month number (1-12) to process recurring expenses for (default: current month)'
        )

    def handle(self, *args, **kwargs):
        # Get the month to process
        month_to_process = kwargs.get('month')
        if month_to_process is None:
            month_to_process = now().date().month

        # Validate month range
        if month_to_process < 1 or month_to_process > 12:
            self.stdout.write(self.style.ERROR(
                'Month must be between 1 and 12'))
            return

        # Get today's date
        today = now().date().replace(day=1)
        current_year = today.year

        self.stdout.write(self.style.SUCCESS(
            f'Processing recurring expenses for month {month_to_process} ({datetime.date(current_year, month_to_process, 1).strftime("%B")})'))

        # Get all recurring expenses that need to be added for this month or previous months
        recurring_expenses = RecurringExpense.objects.all()
        print(
            f"Number of recurring expenses to process: {recurring_expenses.count()}")

        for recurring_expense in recurring_expenses:
          
            if not recurring_expense.generate_debit:
              continue
            
            # Set the day and month from the recurring expense's start_date, and use the current year
            print(
                f"Processing recurring expense: {recurring_expense.description}")

            try:
                expense_date = datetime.date(
                    current_year, month_to_process, recurring_expense.start_date.day)
            except ValueError as e:
                self.stdout.write(self.style.WARNING(
                    f"Invalid date for {recurring_expense.description}: {e}. Skipping."))
                continue

            print(f"Expense date set to: {expense_date}")

            # Check if an expense for this recurring expense already exists for this month
            last_expense = Expense.objects.filter(
                reccurring_expense=recurring_expense,
                date__year=current_year,
                date__month=month_to_process,
                date__day=expense_date.day
            ).first()

            if last_expense:
                self.stdout.write(
                    f"Expense already exists for {recurring_expense.description} on {expense_date}")

            else:
                # Create a new expense for the same day and month as the start_date of recurring_expense, but with the current year
                Expense.objects.create(
                    user=recurring_expense.user,
                    description=recurring_expense.description,
                    amount=recurring_expense.total_amount,
                    date=expense_date,  # Use the day and month from start_date, and the current year
                    category=recurring_expense.category,
                    payment_method=recurring_expense.payment_method,
                    reccurring_expense=recurring_expense
                )

                self.stdout.write(self.style.SUCCESS(
                    f"Created expense for {recurring_expense.description} on {expense_date}"))

        self.stdout.write(self.style.SUCCESS(
            'Monthly expenses have been created.'))
