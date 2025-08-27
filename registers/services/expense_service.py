from ..models import Expense


class ExpenseService:
    """ Expense service"""

    def create_single_expense(self, user, expense_data):
        """_summary_

        Args:
            user (_type_): _description_
            expense_data (_type_): _description_
        """
        expense = Expense(
            user=user,
            description=expense_data['description'],
            amount=expense_data['amount'],
            date=expense_data['date'],
            category=expense_data['category'],
            payment_method=expense_data['payment_method'],
            installment_plan=None,
        )
        expense.save()
        return expense
