import os

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from registers.csv import importer


class Command(BaseCommand):
    help = 'Import expenses and incomes from a CSV file (same format as the CSV import page)'

    def add_arguments(self, parser):
        parser.add_argument('csv_file_path', type=str, help='Path to the CSV file')
        parser.add_argument('--separator', type=str, default=',', help='CSV separator (default: ,)')
        parser.add_argument('--user', type=str, default=None, help='Username to import data for (default: first user)')
        parser.add_argument('--preview', action='store_true', help="Show preview only, don't import")

    def handle(self, *args, **options):
        path = options['csv_file_path']
        if not os.path.isabs(path):
            path = os.path.join(settings.BASE_DIR, path)
        if not os.path.exists(path):
            raise CommandError(f'File not found: {path}')
        user = (User.objects.filter(username=options['user']).first() if options['user']
                else User.objects.first())
        if user is None:
            raise CommandError(f"User not found: {options['user'] or '(no users in database)'}")

        df, problems = importer.read_csv(path, options['separator'])
        if df is None:
            raise CommandError('\n'.join(problems))
        for warning in problems:
            self.stdout.write(self.style.WARNING(f'Data warning: {warning}'))

        if options['preview']:
            self.stdout.write(df.head(importer.PREVIEW_ROWS).to_string())
            self.stdout.write(f'\nTotal rows: {len(df)}')
            return

        result = importer.import_rows(df, user)
        for error in result['errors']:
            self.stdout.write(self.style.ERROR(f'  - {error}'))
        stats = result['stats']
        self.stdout.write(self.style.SUCCESS(
            f"Imported {stats['imported']} of {stats['total_rows']} rows "
            f"({stats['imported_expenses']} expenses, {stats['imported_incomes']} incomes, {stats['errors']} errors)."
        ))
