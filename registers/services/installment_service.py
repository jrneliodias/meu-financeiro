from dateutil.relativedelta import relativedelta
from ..models import Expense, Installment


class InstallmentService:
    """ Service class to handle Installment creation """

    def create_installments(self, user, installment_data):
        """
        Handles the creation of an Installment plan and its related expenses.
        """
        total_amount = installment_data['amount']
        total_installments = installment_data['installments']

        installment = Installment(
            user=user,
            description=installment_data['description'],
            start_date=installment_data['date'],
            total_amount=total_amount,
            total_installments=total_installments,
            category=installment_data['category'],
            payment_method=installment_data['payment_method'],
        )

        # Save the Installment object before creating related expenses
        installment.save()

        installment_amount = total_amount / total_installments
        expenses = []

        for i in range(total_installments):
            due_date = installment_data['date'] + relativedelta(months=i)

            expense = Expense.objects.create(
                user=user,
                description=f"{installment_data['description']} - {i+1}/{total_installments}",
                amount=installment_amount,
                date=due_date,
                category=installment_data['category'],
                payment_method=installment_data['payment_method'],
                installment_plan=installment
            )
            expenses.append(expense)

        return installment, expenses
