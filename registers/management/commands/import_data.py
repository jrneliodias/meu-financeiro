import pandas as pd
from django.core.management.base import BaseCommand
from registers.models import Expense, Category, PaymentMethod
from django.contrib.auth.models import User
import os
from django.conf import settings


class Command(BaseCommand):
    help = 'Importa dados de um arquivo CSV para o banco de dados'

    def add_arguments(self, parser):
        parser.add_argument('csv_file_path', type=str,
                            help='Caminho para o arquivo CSV')
        parser.add_argument('--separator', type=str, default=',',
                            help='Separador do arquivo CSV (padrão: ,)')

    def handle(self, *args, **kwargs):
        csv_file_path = kwargs['csv_file_path']
        csv_file_separator = kwargs['separator']

        # Verifica se o caminho é absoluto ou relativo
        if not os.path.isabs(csv_file_path):
            base_dir = settings.BASE_DIR
            csv_file_path = os.path.join(base_dir, csv_file_path)

        # Verifica se o arquivo existe
        if not os.path.exists(csv_file_path):
            self.stdout.write(self.style.ERROR(
                f'Arquivo não encontrado: {csv_file_path}'))
            return

        # Usando pandas para ler o CSV
        try:
            df = pd.read_csv(csv_file_path, sep=csv_file_separator)
            self.stdout.write(self.style.SUCCESS(
                f'Arquivo CSV lido com sucesso: {csv_file_path}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f'Erro ao ler o arquivo CSV: {e}'))
            return

        # Verifique se o usuário existe ou crie um usuário padrão
        # Substitua por lógica para selecionar o usuário correto
        default_user = User.objects.first()

        # Contador para relatório final
        items_imported = 0

        # Percorre as linhas do DataFrame
        for index, row in df.iterrows():
            try:
                # Verificar ou criar a categoria
                category_name = row['category']
                category, created = Category.objects.get_or_create(
                    name=category_name, type='expense')

                # Verificar ou criar o método de pagamento
                payment_method_name = row['payment_method']
                payment_method, created = PaymentMethod.objects.get_or_create(
                    name=payment_method_name,
                    defaults={'start_billing_day': 1}
                )

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
                items_imported += 1

                if items_imported % 10 == 0:
                    self.stdout.write(
                        f'Importados {items_imported} registros...')

            except Exception as e:
                self.stdout.write(self.style.WARNING(
                    f'Erro ao importar linha {index}: {e}'))

        self.stdout.write(self.style.SUCCESS(
            f'Importação concluída! {items_imported} registros importados com sucesso.'))
