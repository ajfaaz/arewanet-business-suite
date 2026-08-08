from sales.payments.models import Payment


class PaymentSelector:

    @staticmethod
    def list(organization):
        return Payment.objects.filter(
            organization=organization
        ).select_related("invoice", "customer", "organization")
