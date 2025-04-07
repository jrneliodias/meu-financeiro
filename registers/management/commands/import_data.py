import pandas as pd
from django.core.management.base import BaseCommand
from registers.models import Expense, Category, PaymentMethod
from django.contrib.auth.models import User  # Importe o modelo User
import os
from django.conf import settings


class Command(BaseCommand):
    help = 'Importa dados de um arquivo CSV para o banco de dados'

    def handle(self, *args, **kwargs):
        csv_file_path = 'my_finance_pix.csv'
        csv_file_separator = ','

        base_dir = settings.BASE_DIR
        # Substitua pelo caminho para o seu arquivo CSV
        csv_file_path = os.path.join(base_dir, csv_file_path)

        # Usando pandas para ler o CSV
        df = pd.read_csv(csv_file_path, sep=csv_file_separator)

        # Verifique se o usuário existe ou crie um usuário padrão
        # Substitua por lógica para selecionar o usuário correto
        default_user = User.objects.first()

        # Percorre as linhas do DataFrame
        for index, row in df.iterrows():
            # Verificar ou criar a categoria
            category_name = row['category']
            category, created = Category.objects.get_or_create(
                name=category_name, type='expense')

            # Verificar ou criar o método de pagamento
            payment_method_name = row['payment_method']
            print(payment_method_name)
            payment_method = PaymentMethod.objects.get(
                name=payment_method_name)

            # Criar a despesa
            expense = Expense(
                user=default_user,
                description=row['description'],
                amount=row['amount'],
                date=row['date'],
                category=category,  # Chave estrangeira para Category
                payment_method=payment_method,  # Chave estrangeira para PaymentMethod
            )
            expense.save()
            self.stdout.write(self.style.SUCCESS(
                f'Dados importados com sucesso! {expense.description} - {expense.amount} - {expense.date} - {expense.category} - {expense.payment_method}'))

        self.stdout.write(self.style.SUCCESS('Dados importados com sucesso!'))
