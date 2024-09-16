import datetime
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from registers.models import RecurringExpense, Expense


class Command(BaseCommand):
    help = 'Create monthly expenses from RecurringExpense'

    def handle(self, *args, **kwargs):
        # Get today's date
        today = now().date().replace(day=1)

        # Get all recurring expenses that need to be added for this month or previous months
        recurring_expenses = RecurringExpense.objects.filter(
            start_date__gte=today)

        for rexpense in recurring_expenses:
            # Set the day and month from the recurring expense's start_date, and use the current year
            expense_date = today.replace(
                month=rexpense.start_date.month+1, day=rexpense.start_date.day)

            # Check if an expense for this recurring expense already exists for this month
            last_expense = Expense.objects.filter(
                reccurring_expense=rexpense,
                date__year=today.year,
                date__month=expense_date.month,
                date__day=expense_date.day
            ).first()

            if not last_expense:
                # Create a new expense for the same day and month as the start_date of rexpense, but with the current year
                new_expense = Expense.objects.create(
                    user=rexpense.user,
                    description=rexpense.description,
                    amount=rexpense.total_amount,
                    date=expense_date,  # Use the day and month from start_date, and the current year
                    category=rexpense.category,
                    payment_method=rexpense.payment_method,
                    reccurring_expense=rexpense
                )

                self.stdout.write(self.style.SUCCESS(
                    f"Created expense for {rexpense.description} on {expense_date}"))

        self.stdout.write(self.style.SUCCESS(
            'Monthly expenses have been created.'))
