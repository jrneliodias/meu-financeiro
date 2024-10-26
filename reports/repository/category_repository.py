from registers.models import Category
from django.db.models import Sum
from django.db.models.functions import TruncMonth, TruncYear


class CategoryRepository:

    def get_categories(self):
        """Returns a dictionary where onths as keys and the total income for that month as values."""
        return Category.objects.all()
