from ..models import Income


class IncomeService:
    """ Income service"""

    def create_income(self, user, income_data):
        """_summary_

        Args:
            user (_type_): _description_
            income_data (_type_): _description_
        """
        income = Income(
            user=user,
            description=income_data['description'],
            amount=income_data['amount'],
            date=income_data['date'],
            category=income_data['category'],
        )
        income.save()
        return income
