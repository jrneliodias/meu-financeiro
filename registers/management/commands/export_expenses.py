import csv
from django.core.management.base import BaseCommand
from django.http import HttpResponse
from registers.models import Expense


class Command(BaseCommand):
    help = 'Export expenses to a CSV file with related data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            help='The file path where the CSV should be saved',
            default='expenses.csv'
        )

    def handle(self, *args, **options):
        output_path = options['output']

        # Criar o arquivo CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)

            # Cabeçalhos do CSV
            writer.writerow(['ID', 'User', 'Description', 'Amount', 'Date', 'Category', 'Payment Method',
                             'Installment Plan', 'Recurring Expense', 'Created At', 'Updated At'])

            # Obter todas as despesas e suas informações relacionadas
            expenses = Expense.objects.select_related(
                'user', 'category', 'payment_method', 'installment_plan', 'reccurring_expense'
            )

            # Adicionar cada despesa ao CSV
            for expense in expenses:
                writer.writerow([
                    expense.id,
                    expense.user.username,
                    expense.description,
                    expense.amount,
                    expense.date,
                    expense.category.name if expense.category else 'N/A',
                    expense.payment_method.name if expense.payment_method else 'N/A',
                    expense.installment_plan.description if expense.installment_plan else 'N/A',
                    expense.reccurring_expense.description if expense.reccurring_expense else 'N/A',
                    expense.created_at,
                    expense.updated_at
                ])

        self.stdout.write(self.style.SUCCESS(
            f'Expenses successfully exported to {output_path}'))
