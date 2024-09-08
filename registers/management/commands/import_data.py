import pandas as pd
from django.core.management.base import BaseCommand
from registers.models import Expense, Category, PaymentMethod
from django.contrib.auth.models import User  # Importe o modelo User
import os


class Command(BaseCommand):
    help = 'Importa dados de um arquivo CSV para o banco de dados'

    def handle(self, *args, **kwargs):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # Substitua pelo caminho para o seu arquivo CSV
        csv_file_path = os.path.join(base_dir, 'my_finance.csv')

        # Usando pandas para ler o CSV
        df = pd.read_csv(csv_file_path, sep=';')

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
            payment_method, created = PaymentMethod.objects.get_or_create(
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

        self.stdout.write(self.style.SUCCESS('Dados importados com sucesso!'))
