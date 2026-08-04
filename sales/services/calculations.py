from decimal import Decimal

class InvoiceCalculator:

    @staticmethod
    def calculate(items, vat=0, discount=0):

        subtotal = Decimal("0")

        for item in items:
            subtotal += Decimal(str(item.qty or 0)) * Decimal(str(item.unit_price or 0))

        vat_amount = subtotal * Decimal(str(vat or 0)) / Decimal("100")

        total = subtotal + vat_amount - Decimal(str(discount or 0))

        return {
            "subtotal": subtotal,
            "vat": vat_amount,
            "discount": Decimal(str(discount or 0)),
            "total": total,
        }
