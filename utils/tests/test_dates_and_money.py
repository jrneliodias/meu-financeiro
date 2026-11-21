from datetime import date
from decimal import Decimal

from django.template import Context, Template
from django.test import SimpleTestCase

from utils.dates import parse_month_year
from utils.money import format_brl
from utils.tests.clock import today_is


class MoneyTest(SimpleTestCase):
    def test_brl_format(self):
        # like Intl's pt-BR currency format: sign first, and a no-break space so the value never wraps
        self.assertEqual(format_brl(Decimal('1234567.891')), 'R$\xa01.234.567,89')
        self.assertEqual(format_brl(Decimal('-42161.82')), '-R$\xa042.161,82')
        self.assertEqual(format_brl(0), 'R$\xa00,00')

    def test_brl_filter_is_blank_for_non_numbers(self):
        template = Template('{% load formatting %}{{ x|format_brl }}')
        self.assertEqual(template.render(Context({})), '')
        self.assertEqual(template.render(Context({'x': 'abc'})), '')
        self.assertEqual(template.render(Context({'x': Decimal('12.5')})), 'R$\xa012,50')


class MonthYearTest(SimpleTestCase):
    def test_month_year_defaults_to_today_and_returns_year_first(self):
        with today_is(date(2026, 11, 20)):
            self.assertEqual(parse_month_year({}), (2026, 11))
        self.assertEqual(parse_month_year({'month': '3', 'year': '2025'}), (2025, 3))

    def test_month_year_rejects_missing_required_and_out_of_range(self):
        for params, required in [({'year': '2026'}, True), ({'month': '13', 'year': '2026'}, False),
                                 ({'month': '1', 'year': '1999'}, False), ({'month': '1', 'year': '2101'}, False),
                                 ({'month': 'x'}, False)]:
            with self.subTest(params=params):
                with self.assertRaises(ValueError):
                    parse_month_year(params, required=required)
