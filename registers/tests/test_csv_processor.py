"""Nubank CSV → standard import CSV (date, amount, payment_method, description). No database writes."""
import pandas as pd
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from registers.csv import processor

NUBANK_CSV = 'Data,Valor,Descrição\n02/11/2024,8.96,Uber - Trip\n03/11/2024,50.00,Pix\n'


class NubankTransformTest(TestCase):
    def test_dates_go_from_brazilian_to_iso(self):
        self.assertEqual(processor.to_iso_date('02/11/2024'), '2024-11-02')
        self.assertEqual(processor.to_iso_date('02/11/2024 14:30'), '2024-11-02')
        self.assertEqual(processor.to_iso_date('2024-11-02'), '2024-11-02')
        self.assertEqual(processor.to_iso_date(''), '')

    def test_description_splits_on_the_first_separator(self):
        self.assertEqual(processor.split_description('Uber - Trip - X'), ('Uber', 'Trip - X'))
        self.assertEqual(processor.split_description('Pix'), ('Pix', ''))
        self.assertEqual(processor.split_description(None), ('', ''))

    def test_nubank_columns_are_found_exactly_by_case_or_by_part(self):
        def detect(*columns):
            return processor.detect_columns(pd.DataFrame(columns=list(columns)))
        self.assertEqual(detect('Data', 'Valor', 'Descrição'),
                         {'date': 'Data', 'amount': 'Valor', 'description': 'Descrição'})
        self.assertEqual(detect('data', 'VALOR', 'descrição'),
                         {'date': 'data', 'amount': 'VALOR', 'description': 'descrição'})
        self.assertEqual(detect('Data da compra', 'Valor R$', 'Descricao'),
                         {'date': 'Data da compra', 'amount': 'Valor R$', 'description': 'Descricao'})
        self.assertIsNone(detect('a'))

    def test_unconvertible_dates_are_reported_by_row(self):
        df = pd.DataFrame({'Data': ['02/11/2024'] + ['xx'] * 12, 'Valor': [1] * 13, 'Descrição': ['A - b'] * 13})
        with translation.override('en'):
            processed, warnings = processor.process(df, processor.detect_columns(df))
        self.assertEqual(list(processed.columns), ['date', 'amount', 'payment_method', 'description'])
        self.assertEqual(warnings, ['Could not convert dates in 12 rows: 3, 4, 5, 6, 7, 8, 9, 10, 11, 12 ... and 2 more'])

    def test_missing_mapped_column_is_an_error(self):
        df = pd.DataFrame({'Data': ['02/11/2024'], 'Valor': [1]})
        processed, errors = processor.process(df, {'date': 'Data', 'amount': 'Valor', 'description': 'Nope'})
        self.assertIsNone(processed)
        self.assertEqual(len(errors), 1)


class NubankProcessorPagesTest(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_user(username='importer', password='x'))

    def test_process_preview_edit_and_download(self):
        response = self.client.post(reverse('csv_processor'), {
            'csv_text': NUBANK_CSV, 'separator': ',', 'auto_detect': 'on'})
        self.assertContains(response, 'Uber')
        self.assertContains(response, '2024-11-02')

        edited = [{'date': '2024-11-02', 'amount': 8.96, 'payment_method': 'Uber', 'description': 'Ride'}]
        update = self.client.post(reverse('csv_processor_update_data'), {'rows': edited}, content_type='application/json')
        self.assertTrue(update.json()['success'])
        csv_text = self.client.get(reverse('csv_processor_download')).content.decode()
        self.assertEqual(csv_text, 'date,amount,payment_method,description\n2024-11-02,8.96,Uber,Ride\n')

        not_an_object = self.client.post(reverse('csv_processor_update_data'), [1, 2], content_type='application/json')
        self.assertEqual(not_an_object.status_code, 400)
