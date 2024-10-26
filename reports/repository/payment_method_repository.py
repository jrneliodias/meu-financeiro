from registers.models import PaymentMethod
from django.forms.models import model_to_dict


class PaymentMethodRepository:
    def get_start_billing_days_payment_methods():
        payment_methods_db = PaymentMethod.objects.all()
        data = []

        if payment_methods_db:
            for payment_method in payment_methods_db:
                method_dict = model_to_dict(payment_method)
                data.append(method_dict)
        return data
